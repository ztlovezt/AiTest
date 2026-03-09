"""文件存储增强工具"""
import os
from pathlib import Path
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import hashlib
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class EnhancedFileStorage:
    """增强的文件存储"""
    
    def __init__(self, storage=None):
        self.storage = storage or default_storage
    
    def save_with_hash(self, name, content):
        """保存文件并返回哈希值"""
        saved_path = self.storage.save(name, content)
        file_hash = self._calculate_file_hash(saved_path)
        return saved_path, file_hash
    
    def _calculate_file_hash(self, file_path):
        """计算文件哈希值"""
        try:
            with self.storage.open(file_path, 'rb') as f:
                file_hash = hashlib.sha256()
                for chunk in iter(lambda: f.read(4096), b''):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            logger.error(f'计算文件哈希失败: {e}')
            return None
    
    def get_file_size(self, file_path):
        """获取文件大小"""
        try:
            return self.storage.size(file_path)
        except Exception:
            return 0
    
    def get_file_url(self, file_path):
        """获取文件 URL"""
        return self.storage.url(file_path)
    
    def file_exists(self, file_path):
        """检查文件是否存在"""
        return self.storage.exists(file_path)
    
    def delete_file(self, file_path):
        """删除文件"""
        try:
            if self.storage.exists(file_path):
                self.storage.delete(file_path)
                return True
        except Exception as e:
            logger.error(f'删除文件失败: {e}')
        return False
    
    def list_files(self, directory):
        """列出目录下的文件"""
        try:
            directories, files = self.storage.listdir(directory)
            return files
        except Exception:
            return []
    
    def ensure_directory(self, directory):
        """确保目录存在"""
        try:
            if not self.storage.exists(directory):
                self.storage.save(f'{directory}/.gitkeep', ContentFile(b''))
                return True
        except Exception as e:
            logger.error(f'创建目录失败: {e}')
        return False


class MediaFileManager:
    """媒体文件管理器"""
    
    def __init__(self):
        self.media_root = Path(settings.MEDIA_ROOT)
        self.media_url = settings.MEDIA_URL
    
    def get_user_upload_path(self, user_id, filename):
        """获取用户上传路径"""
        return f'uploads/user_{user_id}/{filename}'
    
    def get_project_upload_path(self, project_id, filename):
        """获取项目上传路径"""
        return f'uploads/project_{project_id}/{filename}'
    
    def get_report_path(self, report_type, report_id, filename):
        """获取报告路径"""
        return f'reports/{report_type}/{report_id}/{filename}'
    
    def get_screenshot_path(self, test_type, test_id, filename):
        """获取截图路径"""
        if test_type == 'ui':
            return f'ui_automation/screenshots/{test_id}/{filename}'
        elif test_type == 'app':
            return f'app_automation/screenshots/{test_id}/{filename}'
        return f'screenshots/{test_type}/{test_id}/{filename}'
    
    def get_allure_path(self, allure_type, filename):
        """获取 Allure 路径"""
        allure_paths = {
            'static': settings.ALLURE_STATIC_DIR,
            'reports': settings.ALLURE_REPORTS_DIR,
            'results': settings.ALLURE_RESULTS_DIR,
            'ai_recording': settings.ALLURE_AI_RECORDING,
            'api_testing': settings.ALLURE_API_TESTING,
            'app_automation': settings.ALLURE_APP_AUTOMATION,
        }
        base_path = allure_paths.get(allure_type, 'allure')
        return f'{base_path}/{filename}'
    
    def cleanup_old_files(self, days=30):
        """清理旧文件"""
        from datetime import timedelta
        
        cutoff = timezone.now() - timedelta(days=days)
        deleted_count = 0
        
        for root, dirs, files in os.walk(self.media_root):
            for file in files:
                file_path = Path(root) / file
                try:
                    mtime = file_path.stat().st_mtime
                    if mtime < cutoff.timestamp():
                        file_path.unlink()
                        deleted_count += 1
                except Exception as e:
                    logger.error(f'清理文件失败 {file_path}: {e}')
        
        return deleted_count
    
    def validate_file_size(self, file_size):
        """验证文件大小"""
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
        return file_size <= max_size
    
    def validate_file_extension(self, filename):
        """验证文件扩展名"""
        allowed_extensions = getattr(settings, 'ALLOWED_FILE_EXTENSIONS', [
            '.jpg', '.jpeg', '.png', '.gif', '.pdf', 
            '.doc', '.docx', '.txt', '.xls', '.xlsx'
        ])
        file_ext = Path(filename).suffix.lower()
        return file_ext in allowed_extensions


enhanced_storage = EnhancedFileStorage()
media_manager = MediaFileManager()
