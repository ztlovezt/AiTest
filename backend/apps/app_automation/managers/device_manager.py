# -*- coding: utf-8 -*-
import logging
import platform
import re
import subprocess

logger = logging.getLogger(__name__)


class DeviceManager:
    """Android ADB device manager."""

    def __init__(self, adb_path='adb'):
        self.adb_path = adb_path
        self._adb_verified = False
        self.subprocess_kwargs = {}
        if platform.system() == 'Windows':
            self.subprocess_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW

    def _verify_adb(self):
        """Ensure adb is available before running device commands."""
        try:
            result = subprocess.run(
                [self.adb_path, 'version'],
                capture_output=True,
                text=True,
                timeout=5,
                **self.subprocess_kwargs,
            )
            if result.returncode != 0:
                logger.warning(f'ADB verification failed: {result.stderr}')
                return False
            logger.info(f'ADB verification succeeded: {result.stdout.strip()}')
            self._adb_verified = True
            return True
        except FileNotFoundError as exc:
            logger.error(f'ADB command not found: {self.adb_path}')
            raise Exception(f'ADB command not found: {self.adb_path}. Please check the configured adb path.') from exc
        except subprocess.TimeoutExpired as exc:
            logger.error('ADB verification timed out')
            raise Exception('ADB verification timed out. Please check whether adb is working normally.') from exc
        except Exception as exc:
            logger.error(f'ADB verification failed: {exc}')
            raise

    def _run_adb(self, args, timeout=15, check=False):
        if not self._adb_verified:
            self._verify_adb()
        result = subprocess.run(
            [self.adb_path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            **self.subprocess_kwargs,
        )
        if check and result.returncode != 0:
            error_message = (result.stderr or result.stdout or '').strip()
            raise Exception(error_message or 'ADB command failed')
        return result

    def _run_device_command(self, device_id, args, timeout=15, check=False):
        return self._run_adb(['-s', device_id, *args], timeout=timeout, check=check)

    def _run_shell(self, device_id, shell_args, timeout=15, check=False):
        return self._run_device_command(device_id, ['shell', *shell_args], timeout=timeout, check=check)

    def run_shell_args(self, device_id: str, shell_args: list[str], timeout: int = 15, check: bool = False) -> str:
        """Run a shell command with argument tokens instead of `sh -c`."""
        result = self._run_shell(device_id, shell_args, timeout=timeout, check=check)
        return (result.stdout or result.stderr or '').strip()

    def run_shell_command(self, device_id: str, command: str, timeout: int = 15, check: bool = False) -> str:
        """Run a shell command string through `sh -c` on the device."""
        result = self._run_shell(device_id, ['sh', '-c', command], timeout=timeout, check=check)
        return (result.stdout or result.stderr or '').strip()

    def read_file(self, device_id: str, file_path: str, timeout: int = 5) -> str:
        """Read a file from the device filesystem."""
        try:
            return self.run_shell_args(device_id, ['cat', file_path], timeout=timeout, check=True)
        except subprocess.TimeoutExpired:
            logger.warning(f'Reading file timed out via direct shell: {file_path}')
            if file_path.startswith('/proc/'):
                return ''
            logger.warning(f'Falling back to sh -c for file read: {file_path}')
            return self.run_shell_command(device_id, f'cat {file_path}', timeout=timeout, check=True)

    def dumpsys(self, device_id: str, *args: str, timeout: int = 20) -> str:
        """Run `dumpsys` on the device."""
        result = self._run_shell(device_id, ['dumpsys', *args], timeout=timeout)
        return (result.stdout or result.stderr or '').strip()

    def list_devices(self):
        """Return device list from `adb devices -l`."""
        try:
            logger.info(f'Running adb command: {self.adb_path} devices -l')
            result = self._run_adb(['devices', '-l'], timeout=10)
            if result.returncode != 0:
                logger.error(f'ADB command failed: {result.stderr}')
                raise Exception(f'ADB command failed: {result.stderr}')

            logger.info(f'ADB output: {result.stdout}')
            devices = []
            lines = result.stdout.strip().split('\n')[1:]

            for line in lines:
                line = line.strip()
                if not line or line.startswith('*'):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    continue

                device_id = parts[0]
                status = 'online' if parts[1] == 'device' else 'offline'
                device_info = {
                    'device_id': device_id,
                    'status': status,
                    'name': None,
                    'android_version': None,
                    'ip_address': None,
                    'port': 5555,
                }

                if ':' in device_id:
                    ip_port = device_id.split(':')
                    device_info['ip_address'] = ip_port[0]
                    device_info['port'] = int(ip_port[1]) if len(ip_port) > 1 else 5555

                if status == 'online':
                    try:
                        device_info.update(self.get_device_info(device_id))
                    except Exception:
                        pass

                devices.append(device_info)

            logger.info(f'Found {len(devices)} devices')
            return devices
        except subprocess.TimeoutExpired as exc:
            logger.error('ADB command timed out')
            raise Exception('ADB command timed out') from exc
        except Exception as exc:
            logger.error(f'Failed to get device list: {exc}')
            raise Exception(f'Failed to get device list: {exc}') from exc

    def get_device_info(self, device_id):
        """Get basic device information."""
        info = {}
        try:
            result = self._run_shell(device_id, ['getprop', 'ro.product.model'], timeout=5)
            if result.returncode == 0:
                info['name'] = result.stdout.strip()

            result = self._run_shell(device_id, ['getprop', 'ro.build.version.release'], timeout=5)
            if result.returncode == 0:
                info['android_version'] = result.stdout.strip()
        except Exception as exc:
            logger.warning(f'Failed to get device info for {device_id}: {exc}')
        return info

    def get_device_profile(self, device_id: str) -> dict:
        """Return a basic static device profile from system properties."""
        keys = [
            'ro.product.brand',
            'ro.product.manufacturer',
            'ro.product.model',
            'ro.product.device',
            'ro.build.version.release',
            'ro.build.version.sdk',
            'ro.product.cpu.abilist',
        ]
        profile = {}
        for key in keys:
            result = self._run_shell(device_id, ['getprop', key], timeout=5)
            profile[key] = result.stdout.strip() if result.returncode == 0 else ''
        return profile

    def get_resolution(self, device_id: str) -> str:
        output = self.run_shell_args(device_id, ['wm', 'size'], timeout=5)
        match = re.search(r'Physical size:\s*(\d+x\d+)', output)
        return match.group(1) if match else ''

    def get_density(self, device_id: str) -> str:
        output = self.run_shell_args(device_id, ['wm', 'density'], timeout=5)
        match = re.search(r'Physical density:\s*(\d+)', output)
        return match.group(1) if match else ''

    def get_installed_packages(self, device_id: str) -> list[str]:
        """Return installed third-party package names on the device."""
        result = self._run_shell(device_id, ['pm', 'list', 'packages', '-3'], timeout=20)
        if result.returncode != 0:
            raise Exception((result.stderr or result.stdout or '').strip() or 'Failed to get packages')
        packages = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith('package:'):
                packages.append(line.replace('package:', '', 1).strip())
        return sorted(packages)

    def get_app_pid(self, device_id: str, package_name: str) -> str:
        """Return app pid if the package is running."""
        if not package_name:
            return ''
        result = self._run_shell(device_id, ['pidof', package_name], timeout=5)
        if result.returncode != 0:
            return ''
        return result.stdout.strip().split()[0] if result.stdout.strip() else ''

    def get_logcat(self, device_id: str, lines: int = 200, log_format: str = 'threadtime') -> str:
        """Dump recent device logcat lines."""
        result = self._run_device_command(
            device_id,
            ['logcat', '-d', '-v', log_format, '-t', str(lines)],
            timeout=20,
        )
        return (result.stdout or result.stderr or '').strip()

    def clear_logcat(self, device_id: str) -> None:
        """Clear device logcat buffer."""
        self._run_device_command(device_id, ['logcat', '-c'], timeout=10, check=True)

    def connect_device(self, ip_address, port=5555):
        """Connect a remote adb device."""
        try:
            device_address = f'{ip_address}:{port}'
            logger.info(f'Connecting device: {device_address}')
            result = self._run_adb(['connect', device_address], timeout=30)

            if result.returncode != 0:
                logger.error(f'Failed to connect device: {result.stderr}')
                raise Exception(f'Failed to connect device: {result.stderr}')

            output = result.stdout.strip()
            logger.info(f'Connect result: {output}')
            if 'connected' not in output.lower() and 'already connected' not in output.lower():
                logger.error(f'Failed to connect device: {output}')
                raise Exception(f'Failed to connect device: {output}')

            device_info = {
                'device_id': device_address,
                'status': 'online',
                'ip_address': ip_address,
                'port': port,
                'name': None,
                'android_version': None,
            }
            try:
                device_info.update(self.get_device_info(device_address))
            except Exception as exc:
                logger.warning(f'Failed to get remote device info: {exc}')
            logger.info(f'Device connected successfully: {device_info}')
            return device_info
        except subprocess.TimeoutExpired as exc:
            logger.error('Device connect timed out')
            raise Exception('Device connect timed out. Please check network connectivity.') from exc
        except Exception as exc:
            logger.error(f'Failed to connect device: {exc}')
            raise Exception(f'Failed to connect device: {exc}') from exc

    def disconnect_device(self, device_id: str) -> bool:
        """Disconnect a remote adb device."""
        try:
            logger.info(f'Disconnecting device: {device_id}')
            result = self._run_adb(['disconnect', device_id], timeout=10)
            success = result.returncode == 0
            if success:
                logger.info(f'Device disconnected: {device_id}')
            else:
                logger.error(f'Failed to disconnect device: {result.stderr}')
            return success
        except Exception as exc:
            logger.error(f'Failed to disconnect device: {exc}')
            return False

    def install_apk(self, device_id: str, apk_path: str, replace: bool = True) -> str:
        """Install an APK on the target device."""
        if not apk_path:
            raise Exception('APK path is required')
        command = ['install']
        if replace:
            command.append('-r')
        command.append(apk_path)
        result = self._run_device_command(device_id, command, timeout=180, check=True)
        return (result.stdout or result.stderr or '').strip()

    def launch_app(self, device_id: str, package_name: str, activity: str = '') -> str:
        """Launch an app on the target device."""
        if not package_name:
            raise Exception('Package name is required')
        if activity:
            component = f'{package_name}/{activity}'
            result = self._run_shell(device_id, ['am', 'start', '-n', component], timeout=30, check=True)
        else:
            result = self._run_shell(
                device_id,
                ['monkey', '-p', package_name, '-c', 'android.intent.category.LAUNCHER', '1'],
                timeout=30,
                check=True,
            )
        return (result.stdout or result.stderr or '').strip()

    def stop_app(self, device_id: str, package_name: str) -> str:
        """Force stop an app."""
        if not package_name:
            raise Exception('Package name is required')
        result = self._run_shell(device_id, ['am', 'force-stop', package_name], timeout=30, check=True)
        return (result.stdout or result.stderr or '').strip()

    def clear_app_data(self, device_id: str, package_name: str) -> str:
        """Clear app data."""
        if not package_name:
            raise Exception('Package name is required')
        result = self._run_shell(device_id, ['pm', 'clear', package_name], timeout=30, check=True)
        return (result.stdout or result.stderr or '').strip()

    def uninstall_app(self, device_id: str, package_name: str) -> str:
        """Uninstall an app."""
        if not package_name:
            raise Exception('Package name is required')
        result = self._run_device_command(device_id, ['uninstall', package_name], timeout=60, check=True)
        return (result.stdout or result.stderr or '').strip()

    def get_current_app(self, device_id: str) -> dict:
        """Return the foreground app package and activity."""
        result = self._run_shell(device_id, ['dumpsys', 'activity', 'activities'], timeout=20)
        output = (result.stdout or '') + '\n' + (result.stderr or '')
        patterns = [
            r'topResumedActivity:.*?\s([A-Za-z0-9_.]+)/([A-Za-z0-9_.$]+)',
            r'mResumedActivity:.*?\s([A-Za-z0-9_.]+)/([A-Za-z0-9_.$]+)',
            r'ResumedActivity:.*?\s([A-Za-z0-9_.]+)/([A-Za-z0-9_.$]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return {
                    'package_name': match.group(1),
                    'activity': match.group(2),
                }
        return {
            'package_name': '',
            'activity': '',
        }
