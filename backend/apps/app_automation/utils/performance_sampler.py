# -*- coding: utf-8 -*-
"""Lightweight ADB-based performance sampling utilities for the APP workbench."""
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from apps.app_automation.managers.device_manager import DeviceManager


class DevicePerformanceSampler:
    """Sample device/app performance metrics with in-memory delta caches."""

    BATTERY_STATUS_MAP = {
        1: "unknown",
        2: "charging",
        3: "discharging",
        4: "not_charging",
        5: "full",
    }

    BATTERY_HEALTH_MAP = {
        1: "unknown",
        2: "good",
        3: "overheat",
        4: "dead",
        5: "over_voltage",
        6: "unspecified_failure",
        7: "cold",
    }

    _instance = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self._cache_lock = threading.Lock()
        self._device_cpu_cache: Dict[str, Dict[str, float]] = {}
        self._device_network_cache: Dict[str, Dict[str, float]] = {}
        self._app_cpu_cache: Dict[Tuple[str, str], Dict[str, float]] = {}
        self._app_frame_cache: Dict[Tuple[str, str], Dict[str, float]] = {}
        self._device_profile_cache: Dict[str, Dict[str, Any]] = {}
        self._cpu_core_cache: Dict[str, int] = {}

    @classmethod
    def instance(cls) -> "DevicePerformanceSampler":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def reset(self, device_id: Optional[str] = None, package_name: Optional[str] = None) -> None:
        """Reset cached counters for one device/package or all samples."""
        with self._cache_lock:
            if not device_id:
                self._device_cpu_cache.clear()
                self._device_network_cache.clear()
                self._app_cpu_cache.clear()
                self._app_frame_cache.clear()
                return

            self._device_cpu_cache.pop(device_id, None)
            self._device_network_cache.pop(device_id, None)
            if package_name:
                self._app_cpu_cache.pop((device_id, package_name), None)
                self._app_frame_cache.pop((device_id, package_name), None)
            else:
                self._app_cpu_cache = {
                    key: value for key, value in self._app_cpu_cache.items() if key[0] != device_id
                }
                self._app_frame_cache = {
                    key: value for key, value in self._app_frame_cache.items() if key[0] != device_id
                }

    def get_device_snapshot(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        profile = self._safe_collect(
            lambda: self._get_device_profile(manager, device_id),
            {
                "brand": "",
                "manufacturer": "",
                "model": "",
                "device": "",
                "android_version": "",
                "sdk": "",
                "abi": "",
                "resolution": "",
                "density": "",
            },
            "device profile",
            device_id,
        )
        cpu_cores = self._safe_collect(lambda: self._get_cpu_cores(manager, device_id), 0, "cpu cores", device_id)
        total_cpu = self._safe_collect(lambda: self._get_total_cpu_usage(manager, device_id), 0.0, "total cpu", device_id)
        memory = self._safe_collect(
            lambda: self._get_total_memory_usage(manager, device_id),
            {"total_mb": 0.0, "used_mb": 0.0, "free_mb": 0.0, "available_mb": 0.0, "usage_percent": 0.0},
            "memory",
            device_id,
        )
        network = self._safe_collect(
            lambda: self._get_network_usage(manager, device_id),
            {"download_kbps": 0.0, "upload_kbps": 0.0, "rx_total_mb": 0.0, "tx_total_mb": 0.0},
            "network",
            device_id,
        )
        battery = self._safe_collect(
            lambda: self._get_battery_info(manager, device_id),
            {"level": None, "status": "", "health": "", "temperature_c": None, "voltage_mv": None, "powered": False},
            "battery",
            device_id,
        )
        storage = self._safe_collect(
            lambda: self._get_storage_info(manager, device_id),
            {"total_gb": 0.0, "used_gb": 0.0, "available_gb": 0.0, "usage_percent": 0.0},
            "storage",
            device_id,
        )
        thermal = self._safe_collect(
            lambda: self._get_thermal_status(manager, device_id),
            {"status": "", "level": None},
            "thermal",
            device_id,
        )
        current_app = self._safe_collect(
            lambda: manager.get_current_app(device_id),
            {"package_name": "", "activity": ""},
            "current app",
            device_id,
        )

        return {
            "timestamp": int(time.time() * 1000),
            "profile": profile,
            "cpu": {
                "usage_percent": total_cpu,
                "cores": cpu_cores,
            },
            "memory": memory,
            "network": network,
            "battery": battery,
            "storage": storage,
            "thermal": thermal,
            "current_app": current_app,
        }

    def get_app_snapshot(
        self,
        manager: DeviceManager,
        device_id: str,
        package_name: str,
    ) -> Dict[str, Any]:
        current_app = self._safe_collect(
            lambda: manager.get_current_app(device_id),
            {"package_name": "", "activity": ""},
            "current app",
            device_id,
        )
        package_name = package_name or current_app.get("package_name", "")
        pid = self._safe_collect(
            lambda: manager.get_app_pid(device_id, package_name),
            "",
            "app pid",
            device_id,
        ) if package_name else ""
        running = bool(pid)

        cpu_percent = self._safe_collect(
            lambda: self._get_app_cpu_usage(manager, device_id, package_name, pid),
            0.0,
            "app cpu",
            device_id,
        ) if running else 0.0
        memory = self._safe_collect(
            lambda: self._get_app_memory_usage(manager, device_id, package_name),
            {
                "pss_mb": 0.0,
                "rss_mb": 0.0,
                "private_dirty_mb": 0.0,
            },
            "app memory",
            device_id,
        ) if package_name else {
            "pss_mb": 0.0,
            "rss_mb": 0.0,
            "private_dirty_mb": 0.0,
        }
        process = self._safe_collect(
            lambda: self._get_process_details(manager, device_id, pid),
            {
                "threads": 0,
                "open_fds": 0,
                "vm_size_mb": 0.0,
                "rss_mb": 0.0,
            },
            "app process",
            device_id,
        ) if running else {
            "threads": 0,
            "open_fds": 0,
            "vm_size_mb": 0.0,
            "rss_mb": 0.0,
        }
        frame_stats = self._safe_collect(
            lambda: self._get_gfxinfo_stats(manager, device_id, package_name),
            {
                "total_frames": 0,
                "janky_frames": 0,
                "jank_percent": 0.0,
                "fps": 0.0,
                "frame_time_ms": {
                    "p50": 0,
                    "p90": 0,
                    "p95": 0,
                    "p99": 0,
                },
            },
            "app frame stats",
            device_id,
        ) if package_name else {
            "total_frames": 0,
            "janky_frames": 0,
            "jank_percent": 0.0,
            "fps": 0.0,
            "frame_time_ms": {
                "p50": 0,
                "p90": 0,
                "p95": 0,
                "p99": 0,
            },
        }

        return {
            "timestamp": int(time.time() * 1000),
            "package_name": package_name,
            "pid": pid,
            "running": running,
            "foreground": bool(package_name and current_app.get("package_name") == package_name),
            "activity": current_app.get("activity", "") if current_app.get("package_name") == package_name else "",
            "cpu": {
                "usage_percent": cpu_percent,
                "normalized_by_cores": True,
            },
            "memory": memory,
            "process": process,
            "frame_stats": frame_stats,
        }

    def _safe_collect(self, collector, default, metric_name: str, device_id: str):
        try:
            return collector()
        except Exception as exc:
            logger.warning(f'Performance sampler fallback for {metric_name} on {device_id}: {exc}')
            return default

    def get_logcat(
        self,
        manager: DeviceManager,
        device_id: str,
        lines: int = 200,
        scope: str = "device",
        package_name: str = "",
        level: str = "",
        keyword: str = "",
    ) -> Dict[str, Any]:
        pid = manager.get_app_pid(device_id, package_name) if scope == "app" and package_name else ""
        raw_output = manager.get_logcat(device_id, lines=max(lines * 3, lines), log_format="threadtime")
        parsed_lines = []
        severity_order = {"V": 0, "D": 1, "I": 2, "W": 3, "E": 4, "F": 5}
        min_level = severity_order.get(level.upper(), 0) if level else 0
        keyword_lower = keyword.lower().strip()

        for raw_line in raw_output.splitlines():
            item = self._parse_logcat_line(raw_line)
            if not item:
                continue
            if severity_order.get(item["priority"], 0) < min_level:
                continue
            if scope == "app" and package_name:
                if pid:
                    if item["pid"] != pid:
                        continue
                elif package_name not in item["message"] and package_name not in item["tag"]:
                    continue
            if keyword_lower and keyword_lower not in item["raw"].lower():
                continue
            parsed_lines.append(item)

        if len(parsed_lines) > lines:
            parsed_lines = parsed_lines[-lines:]

        return {
            "timestamp": int(time.time() * 1000),
            "scope": scope,
            "package_name": package_name,
            "pid": pid,
            "lines": parsed_lines,
        }

    def _get_device_profile(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        cached = self._device_profile_cache.get(device_id)
        if cached:
            return cached

        props = manager.get_device_profile(device_id)
        profile = {
            "brand": props.get("ro.product.brand", ""),
            "manufacturer": props.get("ro.product.manufacturer", ""),
            "model": props.get("ro.product.model", ""),
            "device": props.get("ro.product.device", ""),
            "android_version": props.get("ro.build.version.release", ""),
            "sdk": props.get("ro.build.version.sdk", ""),
            "abi": props.get("ro.product.cpu.abilist", ""),
            "resolution": manager.get_resolution(device_id),
            "density": manager.get_density(device_id),
        }
        self._device_profile_cache[device_id] = profile
        return profile

    def _get_cpu_cores(self, manager: DeviceManager, device_id: str) -> int:
        if device_id in self._cpu_core_cache:
            return self._cpu_core_cache[device_id]

        output = manager.read_file(device_id, "/proc/cpuinfo")
        cpu_cores = len(re.findall(r"^processor\s*:", output, flags=re.MULTILINE))
        if cpu_cores <= 0:
            cpu_cores = 4
        self._cpu_core_cache[device_id] = cpu_cores
        return cpu_cores

    def _get_total_cpu_usage(self, manager: DeviceManager, device_id: str) -> float:
        output = manager.read_file(device_id, "/proc/stat")
        for line in output.splitlines():
            if not line.startswith("cpu "):
                continue
            parts = line.split()
            if len(parts) < 8:
                break
            values = [int(item) for item in parts[1:8]]
            total = sum(values)
            idle_total = values[3] + values[4]
            now = time.time()
            with self._cache_lock:
                previous = self._device_cpu_cache.get(device_id)
                self._device_cpu_cache[device_id] = {
                    "total": total,
                    "idle": idle_total,
                    "ts": now,
                }
            if not previous:
                return 0.0
            total_diff = total - previous["total"]
            idle_diff = idle_total - previous["idle"]
            if total_diff <= 0:
                return 0.0
            usage = 100.0 * (total_diff - idle_diff) / total_diff
            return round(max(0.0, min(100.0, usage)), 1)
        return 0.0

    def _get_total_memory_usage(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        output = manager.read_file(device_id, "/proc/meminfo")
        mem_info: Dict[str, int] = {}
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            parts = value.strip().split()
            if not parts:
                continue
            try:
                mem_info[key.strip()] = int(parts[0])
            except ValueError:
                continue

        total_kb = mem_info.get("MemTotal", 0)
        available_kb = mem_info.get("MemAvailable", 0)
        free_kb = mem_info.get("MemFree", 0)
        used_kb = total_kb - available_kb if available_kb else max(
            total_kb - free_kb - mem_info.get("Buffers", 0) - mem_info.get("Cached", 0),
            0,
        )
        usage_percent = (used_kb / total_kb * 100.0) if total_kb else 0.0

        return {
            "total_mb": round(total_kb / 1024, 1),
            "used_mb": round(used_kb / 1024, 1),
            "free_mb": round(free_kb / 1024, 1),
            "available_mb": round(available_kb / 1024, 1),
            "usage_percent": round(max(0.0, min(100.0, usage_percent)), 1),
        }

    def _get_network_usage(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        output = manager.read_file(device_id, "/proc/net/dev")
        rx_bytes = 0
        tx_bytes = 0
        for line in output.splitlines():
            if ":" not in line:
                continue
            interface, data = line.split(":", 1)
            interface = interface.strip()
            if interface == "lo":
                continue
            values = data.split()
            if len(values) < 9:
                continue
            try:
                rx_bytes += int(values[0])
                tx_bytes += int(values[8])
            except ValueError:
                continue

        now = time.time()
        with self._cache_lock:
            previous = self._device_network_cache.get(device_id)
            self._device_network_cache[device_id] = {
                "rx": rx_bytes,
                "tx": tx_bytes,
                "ts": now,
            }

        down_kbps = 0.0
        up_kbps = 0.0
        if previous:
            elapsed = max(now - previous["ts"], 0.001)
            down_kbps = max((rx_bytes - previous["rx"]) / 1024.0 / elapsed, 0.0)
            up_kbps = max((tx_bytes - previous["tx"]) / 1024.0 / elapsed, 0.0)

        return {
            "download_kbps": round(down_kbps, 1),
            "upload_kbps": round(up_kbps, 1),
            "rx_total_mb": round(rx_bytes / 1024.0 / 1024.0, 1),
            "tx_total_mb": round(tx_bytes / 1024.0 / 1024.0, 1),
        }

    def _get_battery_info(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        output = manager.dumpsys(device_id, "battery")
        data: Dict[str, Any] = {
            "level": None,
            "status": "",
            "health": "",
            "temperature_c": None,
            "voltage_mv": None,
            "powered": False,
        }
        for line in output.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key == "level":
                data["level"] = self._safe_int(value)
            elif key == "status":
                status_value = self._safe_int(value)
                data["status"] = self.BATTERY_STATUS_MAP.get(status_value, value)
            elif key == "health":
                health_value = self._safe_int(value)
                data["health"] = self.BATTERY_HEALTH_MAP.get(health_value, value)
            elif key == "temperature":
                temp = self._safe_int(value)
                data["temperature_c"] = round(temp / 10.0, 1) if temp is not None else None
            elif key == "voltage":
                data["voltage_mv"] = self._safe_int(value)
            elif key == "powered":
                data["powered"] = value.lower() == "true"
        return data

    def _get_storage_info(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        output = manager.run_shell_args(device_id, ["df", "/data"], timeout=8)
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if len(lines) < 2:
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "usage_percent": 0.0,
            }

        parts = re.split(r"\s+", lines[-1])
        if len(parts) < 5:
            return {
                "total_gb": 0.0,
                "used_gb": 0.0,
                "available_gb": 0.0,
                "usage_percent": 0.0,
            }

        total_kb = self._safe_int(parts[1]) or 0
        used_kb = self._safe_int(parts[2]) or 0
        available_kb = self._safe_int(parts[3]) or 0
        usage_percent = float((parts[4] or "0").replace("%", "") or 0)
        return {
            "total_gb": round(total_kb / 1024.0 / 1024.0, 1),
            "used_gb": round(used_kb / 1024.0 / 1024.0, 1),
            "available_gb": round(available_kb / 1024.0 / 1024.0, 1),
            "usage_percent": round(usage_percent, 1),
        }

    def _get_thermal_status(self, manager: DeviceManager, device_id: str) -> Dict[str, Any]:
        command_output = manager.run_shell_args(
            device_id,
            ["cmd", "thermalservice", "get-current-thermal-status"],
            timeout=8,
        ).strip()
        if not command_output:
            return {"status": "", "level": None}

        level = self._safe_int(re.search(r"(\d+)", command_output).group(1) if re.search(r"(\d+)", command_output) else "")
        status_map = {
            0: "none",
            1: "light",
            2: "moderate",
            3: "severe",
            4: "critical",
            5: "emergency",
            6: "shutdown",
        }
        return {
            "status": status_map.get(level, command_output),
            "level": level,
        }

    def _get_app_cpu_usage(
        self,
        manager: DeviceManager,
        device_id: str,
        package_name: str,
        pid: str,
    ) -> float:
        output = manager.read_file(device_id, f"/proc/{pid}/stat")
        parts = output.split()
        if len(parts) < 15:
            return 0.0

        process_cpu_time = self._safe_int(parts[13]) or 0
        process_cpu_time += self._safe_int(parts[14]) or 0
        cache_key = (device_id, package_name)
        now = time.time()

        with self._cache_lock:
            previous = self._app_cpu_cache.get(cache_key)
            self._app_cpu_cache[cache_key] = {"cpu": process_cpu_time, "ts": now}

        if not previous:
            return 0.0

        elapsed = now - previous["ts"]
        cpu_diff = process_cpu_time - previous["cpu"]
        if elapsed <= 0 or cpu_diff < 0:
            return 0.0

        cpu_cores = self._get_cpu_cores(manager, device_id)
        usage = (cpu_diff / 100.0) / elapsed * 100.0 / max(cpu_cores, 1)
        return round(max(0.0, usage), 1)

    def _get_app_memory_usage(
        self,
        manager: DeviceManager,
        device_id: str,
        package_name: str,
    ) -> Dict[str, Any]:
        output = manager.dumpsys(device_id, "meminfo", package_name)
        pss_kb = self._extract_named_value(output, "TOTAL PSS")
        rss_kb = self._extract_named_value(output, "TOTAL RSS")
        private_dirty_kb = self._extract_named_value(output, "TOTAL PRIVATE DIRTY")

        if not pss_kb:
            total_match = re.search(r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)", output)
            if total_match:
                pss_kb = self._safe_int(total_match.group(1)) or 0
                private_dirty_kb = self._safe_int(total_match.group(3)) or 0

        return {
            "pss_mb": round(pss_kb / 1024.0, 1),
            "rss_mb": round(rss_kb / 1024.0, 1),
            "private_dirty_mb": round(private_dirty_kb / 1024.0, 1),
        }

    def _get_process_details(self, manager: DeviceManager, device_id: str, pid: str) -> Dict[str, Any]:
        output = manager.read_file(device_id, f"/proc/{pid}/status")
        threads = 0
        vm_size_kb = 0
        rss_kb = 0

        for line in output.splitlines():
            if line.startswith("Threads:"):
                threads = self._safe_int(line.split(":", 1)[1].strip()) or 0
            elif line.startswith("VmSize:"):
                vm_size_kb = self._safe_int(line.split(":", 1)[1].strip().split()[0]) or 0
            elif line.startswith("VmRSS:"):
                rss_kb = self._safe_int(line.split(":", 1)[1].strip().split()[0]) or 0

        try:
            fd_output = manager.run_shell_args(
                device_id,
                ["ls", f"/proc/{pid}/fd"],
                timeout=5,
                check=False,
            ).strip()
            open_fds = len([line for line in fd_output.splitlines() if line.strip()]) if fd_output else 0
        except Exception:
            open_fds = 0

        return {
            "threads": threads,
            "open_fds": open_fds,
            "vm_size_mb": round(vm_size_kb / 1024.0, 1),
            "rss_mb": round(rss_kb / 1024.0, 1),
        }

    def _get_gfxinfo_stats(
        self,
        manager: DeviceManager,
        device_id: str,
        package_name: str,
    ) -> Dict[str, Any]:
        output = manager.dumpsys(device_id, "gfxinfo", package_name)
        total_frames = self._extract_named_value(output, "Total frames rendered")
        janky_frames = self._extract_named_value(output, "Janky frames")
        jank_percent_match = re.search(r"Janky frames:\s+\d+\s+\(([\d.]+)%\)", output)
        p50 = self._extract_percentile(output, "50th percentile")
        p90 = self._extract_percentile(output, "90th percentile")
        p95 = self._extract_percentile(output, "95th percentile")
        p99 = self._extract_percentile(output, "99th percentile")

        cache_key = (device_id, package_name)
        now = time.time()
        with self._cache_lock:
            previous = self._app_frame_cache.get(cache_key)
            self._app_frame_cache[cache_key] = {
                "frames": total_frames,
                "janky": janky_frames,
                "ts": now,
            }

        fps = 0.0
        if previous:
            frame_diff = total_frames - previous["frames"]
            elapsed = now - previous["ts"]
            if frame_diff > 0 and elapsed > 0:
                fps = round(frame_diff / elapsed, 1)

        return {
            "total_frames": total_frames,
            "janky_frames": janky_frames,
            "jank_percent": round(float(jank_percent_match.group(1)), 1) if jank_percent_match else 0.0,
            "fps": fps,
            "frame_time_ms": {
                "p50": p50,
                "p90": p90,
                "p95": p95,
                "p99": p99,
            },
        }

    def _extract_named_value(self, output: str, name: str) -> int:
        patterns = [
            rf"{re.escape(name)}:\s+(\d+(?:,\d+)*)",
            rf"{re.escape(name)}\s+(\d+(?:,\d+)*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, output, flags=re.IGNORECASE)
            if match:
                return self._safe_int(match.group(1).replace(",", "")) or 0
        return 0

    def _extract_percentile(self, output: str, name: str) -> int:
        match = re.search(rf"{re.escape(name)}:\s+(\d+)ms", output, flags=re.IGNORECASE)
        return self._safe_int(match.group(1)) or 0 if match else 0

    def _parse_logcat_line(self, line: str) -> Optional[Dict[str, str]]:
        match = re.match(
            r"^(?P<time>\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d+)\s+"
            r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<priority>[VDIWEF])\s+"
            r"(?P<tag>.*?):\s(?P<message>.*)$",
            line,
        )
        if not match:
            return None
        item = match.groupdict()
        item["raw"] = line
        return item

    def _safe_int(self, value: Any) -> Optional[int]:
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None


performance_sampler = DevicePerformanceSampler.instance()
