import sys
import re

file_path = '/Users/chenjigang/Desktop/testhub_platform/backend/apps/knowledge_base/services.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace VisionParser and DocumentParser
start_marker = "    if require_refiner and not config_status['has_refiner']:\n        return False, 'Refiner API 未配置，请在设置中心配置 Refiner 相关参数'\n    \n    return True, ''\n\n\nclass VisionParser:"
end_marker = "class TextChunker:"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_code = """    if require_refiner and not config_status['has_refiner']:
        return False, 'Refiner API 未配置，请在设置中心配置 Refiner 相关参数'
    
    return True, ''


class TikaParser:
    \"\"\"Tika Server 文档解析服务\"\"\"

    def __init__(self):
        self._config_loaded = False
        self.tika_server_url = None

    def _ensure_config(self):
        \"\"\"延迟加载配置\"\"\"
        if self._config_loaded:
            return
        
        try:
            if connection.introspection.table_names():
                from apps.knowledge_base.models import KnowledgeBaseConfig
                db_config = KnowledgeBaseConfig.objects.filter(is_active=True).first()
                if db_config and db_config.tika_server_url:
                    self.tika_server_url = db_config.tika_server_url
                    logger.debug(f"从数据库加载 Tika 配置成功: {self.tika_server_url}")
                else:
                    from django.conf import settings
                    self.tika_server_url = getattr(settings, 'DOC_PARSER_URL', 'http://localhost:9987')
        except (OperationalError, ProgrammingError, Exception) as e:
            logger.warning(f"数据库查询配置失败: {e}")
            from django.conf import settings
            self.tika_server_url = getattr(settings, 'DOC_PARSER_URL', 'http://localhost:9987')
            
        self._config_loaded = True

    def extract_text(self, file_path: str) -> str:
        \"\"\"调用 Tika Server 提取纯文本\"\"\"
        self._ensure_config()
        if not self.tika_server_url:
            logger.error("Tika Server URL 未配置")
            return ""

        try:
            import httpx
            
            with open(file_path, 'rb') as f:
                # 使用 PUT 请求 Tika 的 /tika 端点，Header Accept 为 text/plain
                headers = {
                    'Accept': 'text/plain'
                }
                # 设置一个较长的超时时间（180秒）处理大文件
                with httpx.Client(timeout=180.0) as client:
                    response = client.put(
                        f"{self.tika_server_url.rstrip('/')}/tika",
                        content=f,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response.text.strip()
        except Exception as e:
            logger.error(f"Tika Server 解析文件失败 {file_path}: {e}")
            return ""

tika_parser = TikaParser()

# 为了兼容现有代码中可能使用到的变量名
vision_parser = tika_parser
glm_vision_parser = tika_parser


class DocumentParser:
    \"\"\"文档解析器 - 统一使用 Tika Server 解析各种文档\"\"\"

    @staticmethod
    def extract_text_from_pdf(file_path: str, use_vision: bool = False) -> str:
        return tika_parser.extract_text(file_path)

    @staticmethod
    def extract_text_from_docx(file_path: str, use_vision: bool = False) -> str:
        return tika_parser.extract_text(file_path)

    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        return tika_parser.extract_text(file_path)

    @staticmethod
    def extract_text_from_md(file_path: str) -> str:
        return tika_parser.extract_text(file_path)

    @classmethod
    def extract_text(cls, file_path: str, document_type: str, use_vision: bool = False, use_vision_direct: bool = False) -> str:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return ""

        logger.info(f"使用 Tika 解析文档: {os.path.basename(file_path)}")
        return tika_parser.extract_text(file_path)

    @classmethod
    def extract_text_with_vision(cls, file_path: str, document_type: str) -> str:
        return cls.extract_text(file_path, document_type)


"""
    
    new_content = content[:start_idx] + new_code + content[end_idx:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Replace success.")
else:
    print("Markers not found.")
