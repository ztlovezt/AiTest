"""
知识库文档解析和向量化服务
"""
import os
import re
import uuid
import base64
import threading
from typing import List, Dict, Any, Optional
from django.conf import settings

try:
    from backend.log_config import get_logger
    logger = get_logger(__name__)
except Exception:
    import logging
    logger = logging.getLogger(__name__)

# 使用统一的配置加载器
try:
    from backend.config_loader import config_loader
except ImportError:
    config_loader = None
    logger.warning("无法导入 config_loader，将使用环境变量")


class GLMVisionParser:
    """智谱 GLM 视觉模型文档解析器 - 用于解析文档中的图片或直接解析整个文档"""

    def __init__(self):
        self.api_key = None
        self.base_url = None
        self.model = None
        self._load_config()

    def _load_config(self):
        """加载智谱 GLM 配置，优先从数据库读取，其次尝试 config.yaml"""
        # 1. 尝试从数据库加载配置
        from apps.knowledge_base.models import KnowledgeBaseConfig
        db_config = KnowledgeBaseConfig.objects.filter(is_active=True).first()
        
        if db_config and db_config.zhipu_api_key:
            self.api_key = db_config.zhipu_api_key
            self.base_url = db_config.zhipu_base_url or 'https://open.bigmodel.cn/api/paas/v4'
            self.model = db_config.zhipu_vision_model or 'glm-4v-flash'
            return

        # 2. 如果数据库未配置，退退回 config.yaml 或 环境变量
        if config_loader:
            llm_config = config_loader.get_llm_config()
            self.api_key = llm_config.get('ZHIPU_API_KEY')
            self.base_url = llm_config.get('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
            self.model = llm_config.get('ZHIPU_VISION_MODEL', 'glm-4v-flash')

        # 3. 备选：从环境变量读取
        if not self.api_key:
            self.api_key = os.environ.get('ZHIPU_API_KEY')
        if not self.base_url:
            self.base_url = os.environ.get('ZHIPU_BASE_URL', 'https://open.bigmodel.cn/api/paas/v4')
        if not self.model:
            self.model = os.environ.get('ZHIPU_VISION_MODEL', 'glm-4v-flash')

    def is_configured(self) -> bool:
        """检查是否已配置智谱 API"""
        return bool(self.api_key)

    def upload_file(self, file_path: str) -> Optional[str]:
        """
        上传文件到智谱服务器（使用文件解析API）

        Args:
            file_path: 文件路径

        Returns:
            任务ID (task_id)，失败返回 None
        """
        if not self.is_configured():
            logger.warning("智谱 GLM API 未配置，跳过文件上传")
            return None

        try:
            import httpx

            # 智谱文件解析API
            url = f"{self.base_url}/files/parser/create"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            # 获取文件名和类型
            filename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower().replace('.', '')

            # 文件类型映射
            file_type_map = {
                'docx': 'DOCX', 'doc': 'DOC',
                'xlsx': 'XLSX', 'xls': 'XLS',
                'pptx': 'PPTX', 'ppt': 'PPT',
                'pdf': 'PDF',
                'txt': 'TXT', 'md': 'MD', 'csv': 'CSV',
                'png': 'PNG', 'jpg': 'JPG', 'jpeg': 'JPEG',
            }
            file_type = file_type_map.get(ext, ext.upper())

            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f)
                }
                data = {
                    'file_type': file_type,
                    'tool_type': 'lite'  # 使用 lite 类型，免费且速度快
                }

                with httpx.Client(timeout=120) as client:
                    response = client.post(url, headers=headers, files=files, data=data)
                    response.raise_for_status()
                    result = response.json()

            task_id = result.get('task_id')
            logger.info(f"文件解析任务创建成功: {filename}, task_id: {task_id}")
            return task_id

        except Exception as e:
            logger.error(f"文件上传/创建解析任务失败: {e}")
            return None

    def parse_document_directly(self, file_path: str, prompt: str = None) -> str:
        """
        直接使用智谱文件解析API解析整个文档

        Args:
            file_path: 文档路径（PDF、Word、图片等）
            prompt: 自定义提示词（此API不需要）

        Returns:
            文档内容
        """
        if not self.is_configured():
            logger.warning("智谱 GLM API 未配置，跳过文档解析")
            return ""

        try:
            import httpx
            import time

            # 1. 创建解析任务
            task_id = self.upload_file(file_path)
            if not task_id:
                logger.error("创建解析任务失败")
                return ""

            logger.info(f"开始轮询解析结果: {os.path.basename(file_path)}")

            # 2. 轮询获取解析结果
            result_url = f"{self.base_url}/files/parser/result/{task_id}/text"
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            max_retry = 60  # 最多轮询60次
            interval = 3  # 每次间隔3秒

            with httpx.Client(timeout=30) as client:
                for i in range(max_retry):
                    response = client.get(result_url, headers=headers)
                    response.raise_for_status()
                    result = response.json()

                    status = result.get('status', '')
                    logger.info(f"解析任务状态: {status}, 尝试 {i + 1}/{max_retry}")

                    if status == 'succeeded':
                        content = result.get('content', '')
                        parsing_url = result.get('parsing_result_url', '')

                        # 如果有下载链接，获取更完整的内容
                        if parsing_url and not content:
                            try:
                                dl_response = client.get(parsing_url, timeout=60)
                                if dl_response.status_code == 200:
                                    content = dl_response.text
                            except Exception as e:
                                logger.warning(f"下载解析结果失败: {e}")

                        logger.info(f"智谱文件解析成功，内容长度: {len(content)} 字符")
                        logger.info(f"解析内容预览: {content[:500]}...")
                        return content

                    elif status == 'failed':
                        error_msg = result.get('message', '未知错误')
                        logger.error(f"解析任务失败: {error_msg}")
                        return ""

                    elif status == 'processing':
                        time.sleep(interval)
                    else:
                        time.sleep(interval)

            logger.error("解析任务超时")
            return ""

        except Exception as e:
            logger.error(f"智谱文件解析失败: {e}")
            return ""

    def parse_document_with_images(self, file_path: str, document_type: str, prompt: str = None) -> str:
        """
        对于图片型PDF或多图片文档，将每页转为图片后逐一解析

        Args:
            file_path: 文档路径
            document_type: 文档类型
            prompt: 自定义提示词

        Returns:
            文档内容
        """
        if not self.is_configured():
            logger.warning("智谱 GLM API 未配置，跳过文档解析")
            return ""

        try:
            if document_type == 'pdf':
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                all_content = []

                # 默认提示词
                if not prompt:
                    prompt = """请详细解析这个文档页面的所有内容，包括：
1. 所有文字内容
2. 图片、图表的内容描述
3. 表格数据
请完整提取页面中的所有信息。"""

                for page_num in range(len(doc)):
                    page = doc[page_num]

                    # 将页面渲染为图片
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")

                    # 调用视觉模型解析
                    page_content = self.parse_image_from_bytes(
                        img_data,
                        mime_type='image/png',
                        prompt=prompt
                    )

                    if page_content:
                        all_content.append(f"=== 第 {page_num + 1} 页 ===\n{page_content}")
                        logger.info(f"PDF 第 {page_num + 1} 页解析完成")

                doc.close()
                return "\n\n".join(all_content)

            else:
                # 其他类型直接上传解析
                return self.parse_document_directly(file_path, prompt)

        except ImportError:
            logger.warning("PyMuPDF 未安装，尝试直接上传解析")
            return self.parse_document_directly(file_path, prompt)
        except Exception as e:
            logger.error(f"文档解析失败: {e}")
            return ""

    def parse_image(self, image_path: str, prompt: str = None) -> str:
        """
        使用 GLM 视觉模型解析图片

        Args:
            image_path: 图片路径
            prompt: 自定义提示词

        Returns:
            图片内容描述
        """
        if not self.is_configured():
            logger.warning("智谱 GLM API 未配置，跳过图片解析")
            return ""

        try:
            import httpx

            # 读取图片并转为 base64
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # 获取图片格式
            ext = os.path.splitext(image_path)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')

            # base64 编码
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{image_base64}"

            # 默认提示词
            if not prompt:
                prompt = "请详细描述这张图片的内容，包括文字、图表、流程图等所有可见信息。如果是表格，请按表格格式输出。"

            # 调用智谱 GLM 视觉 API
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }

            with httpx.Client(timeout=60) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

            # 打印完整的 API 响应
            logger.info(f"GLM 视觉模型 API 响应: {result}")

            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            logger.info(f"GLM 视觉模型解析图片成功，内容长度: {len(content)} 字符")
            logger.info(f"解析内容: {content[:500]}...")  # 打印前500字符
            return content

        except Exception as e:
            logger.error(f"GLM 视觉模型解析图片失败: {e}")
            return ""

    def parse_image_from_bytes(self, image_data: bytes, mime_type: str = 'image/png', prompt: str = None) -> str:
        """
        使用 GLM 视觉模型解析图片字节数据

        Args:
            image_data: 图片字节数据
            mime_type: 图片 MIME 类型
            prompt: 自定义提示词

        Returns:
            图片内容描述
        """
        if not self.is_configured():
            logger.warning("智谱 GLM API 未配置，跳过图片解析")
            return ""

        try:
            import httpx

            # base64 编码
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:{mime_type};base64,{image_base64}"

            # 默认提示词
            if not prompt:
                prompt = "请详细描述这张图片的内容，包括文字、图表、流程图等所有可见信息。如果是表格，请按表格格式输出。"

            # 调用智谱 GLM 视觉 API
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }

            with httpx.Client(timeout=60) as client:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            return content

        except Exception as e:
            logger.error(f"GLM 视觉模型解析图片失败: {e}")
            return ""


# 全局 GLM 视觉解析器实例
glm_vision_parser = GLMVisionParser()


class DocumentParser:
    """文档解析器 - 支持PDF、Word、TXT、MD格式"""

    @staticmethod
    def extract_text_from_pdf(file_path: str, use_vision: bool = True) -> str:
        """
        从PDF文件提取文本和图片（使用 GLM 视觉模型解析图片)

        Args:
            file_path: PDF文件路径
            use_vision: 是否使用 GLM 视觉模型解析图片
        """
        text_content = []
        images_text = []

        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)

            for page_num in range(len(doc)):
                page = doc[page_num]

                # 提取文本
                page_text = page.get_text()
                if page_text:
                    text_content.append(page_text)
                    text_content.append("\n")

                # 提取图片并使用 GLM 视觉模型解析
                if use_vision and glm_vision_parser.is_configured():
                    images = page.get_images(full=True)
                    for img_index in range(len(images)):
                        xref = images[img_index]
                        try:
                            base_image = doc.extract_image(xref)
                            if base_image:
                                # 保存临时图片
                                temp_dir = os.path.join(settings.BASE_DIR, 'expand', 'temp_images')
                                os.makedirs(temp_dir, exist_ok=True)
                                ext = base_image.get("ext", "png")
                                temp_image_path = os.path.join(temp_dir, f"page_{page_num}_img_{img_index}.{ext}")
                                with open(temp_image_path, 'wb') as f:
                                    f.write(base_image["image"])

                                # 使用 GLM 视觉模型解析图片
                                image_text = glm_vision_parser.parse_image(temp_image_path)
                                if image_text:
                                    images_text.append(f"\n[图片{page_num + 1}-{img_index + 1}]: {image_text}")
                                    logger.info(f"PDF 第 {page_num + 1} 页，第 {img_index + 1} 张图片解析完成")

                                # 删除临时图片
                                try:
                                    os.remove(temp_image_path)
                                except:
                                    pass
                        except Exception as img_error:
                            logger.error(f"PDF 第 {page_num + 1} 页图片 {img_index + 1} 提取/解析失败: {img_error}")

                else:
                    logger.info("GLM 视觉模型未配置，跳过图片解析")

            doc.close()

            # 合并文本和图片描述
            full_text = "".join(text_content)
            if images_text:
                full_text += "\n\n[图片内容]:\n" + "\n".join(images_text)

            return full_text.strip()
        except ImportError:
            logger.warning("PyMuPDF未安装，尝试使用pdfplumber")
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text.strip()
            except ImportError:
                logger.error("pdfplumber也未安装，无法解析PDF")
                return ""
        except Exception as e:
            logger.error(f"PDF解析失败: {e}")
            return ""

    @staticmethod
    def extract_text_from_docx(file_path: str, use_vision: bool = True) -> str:
        """从Word文件提取文本和图片（使用 GLM 视觉模型解析图片)"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = []
            images_text = []

            # 提取段落文本
            for para in doc.paragraphs:
                if para.text.strip():
                    text.append(para.text)

            # 提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text.append(" | ".join(row_text))

            # 提取图片并使用 GLM 视觉模型解析
            if use_vision and glm_vision_parser.is_configured():
                for rel in doc.part.rels.values():
                    if "image" in rel.reltype:
                        try:
                            image = rel.image
                            # 保存临时图片
                            temp_dir = os.path.join(settings.BASE_DIR, 'expand', 'temp_images')
                            os.makedirs(temp_dir, exist_ok=True)
                            ext = image.ext if hasattr(image, 'ext') else 'png'
                            temp_image_path = os.path.join(temp_dir, f"docx_img_{len(images_text)}.{ext}")
                            with open(temp_image_path, 'wb') as f:
                                f.write(image.blob)

                            # 使用 GLM 视觉模型解析图片
                            image_text = glm_vision_parser.parse_image(temp_image_path)
                            if image_text:
                                images_text.append(f"\n[图片{len(images_text) + 1}]: {image_text}")
                                logger.info(f"Word 文档第 {len(images_text)} 张图片解析完成")

                            # 删除临时图片
                            try:
                                os.remove(temp_image_path)
                            except:
                                pass
                        except Exception as img_error:
                            logger.error(f"Word 文档图片提取/解析失败: {img_error}")

            # 合并文本和图片描述
            full_text = "\n".join(text)
            if images_text:
                full_text += "\n\n[图片内容]:\n" + "\n".join(images_text)

            return full_text.strip()
        except ImportError:
            logger.error("python-docx未安装，无法解析Word文档")
            return ""
        except Exception as e:
            logger.error(f"Word解析失败: {e}")
            return ""

    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """从TXT文件提取文本"""
        try:
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read().strip()
                except UnicodeDecodeError:
                    continue
            return ""
        except Exception as e:
            logger.error(f"TXT解析失败: {e}")
            return ""

    @staticmethod
    def extract_text_from_md(file_path: str) -> str:
        """从Markdown文件提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            # 简单的Markdown清理，保留文本内容
            # 移除代码块标记但保留内容
            content = re.sub(r'```[\w]*\n?', '', content)
            content = re.sub(r'`([^`]+)`', r'\1', content)
            # 移除链接但保留文本
            content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)
            # 移除图片
            content = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', content)
            # 移除标题标记
            content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
            # 移除粗体/斜体标记
            content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
            content = re.sub(r'\*([^*]+)\*', r'\1', content)
            content = re.sub(r'__([^_]+)__', r'\1', content)
            content = re.sub(r'_([^_]+)_', r'\1', content)
            return content.strip()
        except Exception as e:
            logger.error(f"Markdown解析失败: {e}")
            return ""

    @classmethod
    def extract_text_with_glm(cls, file_path: str, document_type: str) -> str:
        """
        直接使用智谱GLM大模型解析整个文档（推荐方式）

        Args:
            file_path: 文档路径
            document_type: 文档类型

        Returns:
            解析后的文本内容
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return ""

        if not glm_vision_parser.is_configured():
            logger.warning("智谱 GLM API 未配置，回退到本地解析")
            return cls.extract_text(file_path, document_type, use_vision=False)

        logger.info(f"使用智谱GLM大模型直接解析文档: {os.path.basename(file_path)}")

        # 直接调用智谱GLM解析整个文档
        return glm_vision_parser.parse_document_directly(file_path)

    @classmethod
    def extract_text(cls, file_path: str, document_type: str, use_vision: bool = True, use_glm_direct: bool = False) -> str:
        """
        根据文档类型提取文本

        Args:
            file_path: 文档路径
            document_type: 文档类型
            use_vision: 是否使用 GLM 视觉模型解析图片（本地解析模式）
            use_glm_direct: 是否直接使用智谱GLM大模型解析整个文档（推荐）

        Returns:
            提取的文本内容
        """
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return ""

        # 如果选择直接使用智谱GLM解析，则调用新方法
        if use_glm_direct and glm_vision_parser.is_configured():
            return cls.extract_text_with_glm(file_path, document_type)

        # 原有的本地解析逻辑
        if document_type == 'pdf':
            return cls.extract_text_from_pdf(file_path, use_vision=use_vision)
        elif document_type in ['docx', 'doc']:
            return cls.extract_text_from_docx(file_path, use_vision=use_vision)
        elif document_type == 'txt':
            return cls.extract_text_from_txt(file_path)
        elif document_type == 'md':
            return cls.extract_text_from_md(file_path)
        else:
            logger.error(f"不支持的文档类型: {document_type}")
            return ""


class TextChunker:
    """文本分块器"""

    @staticmethod
    def split_text(
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        将文本分割成多个块

        Args:
            text: 要分割的文本
            chunk_size: 每个块的最大字符数
            chunk_overlap: 相邻块之间的重叠字符数
            separators: 分隔符优先级列表

        Returns:
            分块列表，每个块包含 text, start_index, end_index
        """
        if not text or not text.strip():
            return []

        if separators is None:
            # 中文优先按段落、句号分割
            separators = ["\n\n", "\n", "。", "！", "？", "；", ".", "!", "?", ";", " ", ""]

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # 确定当前块的结束位置
            end = start + chunk_size

            if end >= text_length:
                # 最后一块
                chunk_text = text[start:].strip()
                if chunk_text:
                    chunks.append({
                        'text': chunk_text,
                        'start_index': start,
                        'end_index': text_length
                    })
                break

            # 尝试在chunk_size附近找到最佳分隔点
            best_end = end
            for separator in separators:
                # 在 end 附近向后查找分隔符
                idx = text.find(separator, end - chunk_overlap, end + chunk_overlap)
                if idx != -1:
                    best_end = idx + len(separator)
                    break

            # 如果找不到合适的分隔点，强制在 chunk_size 处分割
            if best_end > end + chunk_overlap:
                best_end = end

            chunk_text = text[start:best_end].strip()
            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'start_index': start,
                    'end_index': best_end
                })

            # 下一块的起始位置（考虑重叠）
            start = best_end - chunk_overlap
            if start < 0:
                start = 0
            # 避免无限循环
            if start <= chunks[-1]['start_index']:
                start = best_end

        return chunks


class VectorStoreService:
    """向量存储服务 - 使用 ChromaDB"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.chroma_client = None
        self.embedding_function = None
        self._init_chroma()
        self._init_embedding()

    def _init_chroma(self):
        """初始化 ChromaDB 客户端"""
        try:
            import chromadb
            from chromadb.config import Settings

            # ChromaDB 数据存储路径
            chroma_path = os.path.join(settings.BASE_DIR, 'expand', 'chroma_db')
            os.makedirs(chroma_path, exist_ok=True)

            self.chroma_client = chromadb.PersistentClient(
                path=chroma_path,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            logger.info(f"ChromaDB 初始化成功，存储路径: {chroma_path}")
        except ImportError:
            logger.error("chromadb 未安装，请运行: pip install chromadb")
            self.chroma_client = None
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            self.chroma_client = None

    def _init_embedding(self):
        """初始化嵌入模型"""
        try:
            from chromadb.utils import embedding_functions

            api_key = None
            base_url = None
            embedding_model = None

            # 1. 优先尝试从数据库读取配置
            from apps.knowledge_base.models import KnowledgeBaseConfig
            db_config = KnowledgeBaseConfig.objects.filter(is_active=True).first()
            if db_config and db_config.embedding_api_key:
                api_key = db_config.embedding_api_key
                base_url = db_config.embedding_base_url
                embedding_model = db_config.embedding_model or "text-embedding-v3"
            
            # 2. 如果数据库未配置，回退到 config.yaml
            if not api_key and config_loader:
                llm_config = config_loader.get_llm_config()
                api_key = llm_config.get('QWEN_API_KEY') or llm_config.get('DASHSCOPE_API_KEY')
                base_url = llm_config.get('QWEN_BASE_URL') or llm_config.get('DASHSCOPE_BASE_URL')
                embedding_model = llm_config.get('EMBEDDING_MODEL')

            # 3. 备选：从 settings 或环境变量读取
            if not api_key:
                api_key = getattr(settings, 'QWEN_API_KEY', None) or \
                          getattr(settings, 'DASHSCOPE_API_KEY', None) or \
                          os.environ.get('QWEN_API_KEY') or \
                          os.environ.get('DASHSCOPE_API_KEY')

            if not base_url:
                base_url = getattr(settings, 'QWEN_BASE_URL', None) or \
                           os.environ.get('QWEN_BASE_URL')

            # 检查必要配置
            if not api_key:
                error_msg = "未配置 Embedding API Key，请在知识库配置或 config.yaml 中进行配置"
                logger.error(error_msg)
                raise ValueError(error_msg)

            if not embedding_model:
                embedding_model = "text-embedding-v3"
                logger.warning(f"未配置 EMBEDDING_MODEL，使用默认模型: {embedding_model}")

            # 使用 OpenAI 兼容的 embedding 函数
            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name=embedding_model,
                api_base=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            logger.info(f"Embedding 模型初始化成功: {embedding_model}")

        except ImportError as e:
            logger.error(f"嵌入函数初始化失败: {e}")
            self.embedding_function = None
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"嵌入模型初始化失败: {e}")
            self.embedding_function = None

    def get_or_create_collection(self, collection_name: str):
        """获取或创建向量集合"""
        if not self.chroma_client:
            logger.error("ChromaDB 客户端未初始化")
            return None

        try:
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            return collection
        except Exception as e:
            logger.error(f"创建/获取集合失败: {e}")
            return None

    def delete_collection(self, collection_name: str) -> bool:
        """删除向量集合"""
        if not self.chroma_client:
            return False

        try:
            self.chroma_client.delete_collection(collection_name)
            logger.info(f"集合 {collection_name} 已删除")
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False

    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict] = None,
        ids: List[str] = None,
        batch_size: int = 10
    ) -> bool:
        """
        向集合添加文档（分批处理，每批最多 batch_size 个）

        Args:
            collection_name: 集合名称
            documents: 文档文本列表
            metadatas: 元数据列表
            ids: 文档ID列表
            batch_size: 每批处理的最大文档数（阿里云 API 限制为 10）

        Returns:
            是否成功
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False

        try:
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]

            total_docs = len(documents)
            success_count = 0

            # 分批处理，每批最多 batch_size 个文档
            for i in range(0, total_docs, batch_size):
                batch_end = min(i + batch_size, total_docs)
                batch_docs = documents[i:batch_end]
                batch_ids = ids[i:batch_end]
                batch_metadatas = metadatas[i:batch_end] if metadatas else None

                try:
                    collection.add(
                        documents=batch_docs,
                        metadatas=batch_metadatas,
                        ids=batch_ids
                    )
                    success_count += len(batch_docs)
                    logger.info(f"批次 {i // batch_size + 1}: 成功添加 {len(batch_docs)} 个文档")
                except Exception as batch_error:
                    logger.error(f"批次 {i // batch_size + 1} 添加失败: {batch_error}")
                    # 继续处理下一批，不中断整个流程

            if success_count == total_docs:
                logger.info(f"成功添加 {success_count} 个文档到集合 {collection_name}")
                return True
            elif success_count > 0:
                logger.warning(f"部分成功: {success_count}/{total_docs} 个文档添加到集合 {collection_name}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def query(
        self,
        collection_name: str,
        query_texts: List[str],
        n_results: int = 5,
        where: Dict = None
    ) -> Dict:
        """
        查询相似文档

        Args:
            collection_name: 集合名称
            query_texts: 查询文本列表
            n_results: 返回结果数量
            where: 元数据过滤条件

        Returns:
            查询结果
        """
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return {'ids': [], 'documents': [], 'metadatas': [], 'distances': []}

        try:
            results = collection.query(
                query_texts=query_texts,
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {'ids': [], 'documents': [], 'metadatas': [], 'distances': []}

    def delete_documents(self, collection_name: str, ids: List[str]) -> bool:
        """删除指定文档"""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return False

        try:
            collection.delete(ids=ids)
            logger.info(f"成功从集合 {collection_name} 删除 {len(ids)} 个文档")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def get_collection_count(self, collection_name: str) -> int:
        """获取集合中的文档数量"""
        collection = self.get_or_create_collection(collection_name)
        if not collection:
            return 0

        try:
            return collection.count()
        except Exception as e:
            logger.error(f"获取集合数量失败: {e}")
            return 0


class KnowledgeBaseService:
    """知识库服务 - 整合文档解析、分块和向量化"""

    def __init__(self):
        self.parser = DocumentParser()
        self.chunker = TextChunker()
        self.vector_store = VectorStoreService()

    def process_document(
        self,
        document,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        enable_vectorization: bool = True,
        use_vision: bool = True,
        use_glm_direct: bool = False
    ) -> Dict[str, Any]:
        """
        处理单个文档：解析文本、分块、向量化

        Args:
            document: KnowledgeDocument 实例
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            enable_vectorization: 是否进行向量化
            use_vision: 是否使用 GLM 视觉模型解析图片（本地解析模式）
            use_glm_direct: 是否直接使用智谱GLM大模型解析整个文档（推荐，完全跳过本地解析）

        Returns:
            处理结果
        """
        result = {
            'success': False,
            'text_length': 0,
            'chunk_count': 0,
            'vectorized': False,
            'error': None,
            'parse_method': 'glm_direct' if use_glm_direct else 'local'
        }

        try:
            # 1. 提取文本
            if document.file and os.path.exists(document.file.path):
                if use_glm_direct:
                    # 直接使用智谱GLM大模型解析整个文档
                    logger.info(f"使用智谱GLM大模型直接解析文档: {document.title}")
                    text = DocumentParser.extract_text_with_glm(
                        document.file.path,
                        document.document_type
                    )
                else:
                    # 本地解析 + GLM视觉模型解析图片
                    text = self.parser.extract_text(
                        document.file.path,
                        document.document_type,
                        use_vision=use_vision
                    )
            else:
                text = document.content or ""

            result['text_length'] = len(text)

            # 保存提取的文本
            if text:
                from .models import KnowledgeDocument
                KnowledgeDocument.objects.filter(pk=document.pk).update(content=text)

            # 2. 分块
            chunks = self.chunker.split_text(
                text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            result['chunk_count'] = len(chunks)

            # 更新分块数量
            from .models import KnowledgeDocument
            KnowledgeDocument.objects.filter(pk=document.pk).update(
                chunk_count=len(chunks),
                vector_status='processing'
            )

            # 3. 向量化
            if enable_vectorization and chunks:
                collection_name = document.knowledge_base.collection_name
                if collection_name:
                    documents = [chunk['text'] for chunk in chunks]
                    metadatas = [{
                        'document_id': document.id,
                        'knowledge_base_id': document.knowledge_base_id,
                        'start_index': chunk['start_index'],
                        'end_index': chunk['end_index'],
                        'title': document.title,
                    } for chunk in chunks]
                    ids = [f"{document.id}_{i}" for i in range(len(chunks))]

                    success = self.vector_store.add_documents(
                        collection_name=collection_name,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )

                    if success:
                        KnowledgeDocument.objects.filter(pk=document.pk).update(
                            vector_status='completed'
                        )
                        result['vectorized'] = True
                    else:
                        KnowledgeDocument.objects.filter(pk=document.pk).update(
                            vector_status='failed',
                            vector_error='向量化存储失败'
                        )
                        result['error'] = '向量化存储失败'
                else:
                    result['error'] = '知识库未配置向量集合'
            else:
                KnowledgeDocument.objects.filter(pk=document.pk).update(
                    vector_status='completed' if not enable_vectorization else 'failed'
                )
                result['vectorized'] = not enable_vectorization

            result['success'] = True

        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            result['error'] = str(e)
            from .models import KnowledgeDocument
            KnowledgeDocument.objects.filter(pk=document.pk).update(
                vector_status='failed',
                vector_error=str(e)
            )

        return result

    def create_knowledge_base_collection(self, knowledge_base) -> str:
        """
        为知识库创建向量集合

        Args:
            knowledge_base: KnowledgeBase 实例

        Returns:
            集合名称
        """
        collection_name = f"kb_{knowledge_base.id}_{uuid.uuid4().hex[:8]}"

        collection = self.vector_store.get_or_create_collection(collection_name)
        if collection:
            # 保存集合名称到知识库
            from .models import KnowledgeBase
            KnowledgeBase.objects.filter(pk=knowledge_base.pk).update(
                collection_name=collection_name
            )
            return collection_name
        return ""

    def search_similar(
        self,
        knowledge_base,
        query: str,
        n_results: int = 5
    ) -> List[Dict]:
        """
        在知识库中搜索相似内容（纯语义检索）

        Args:
            knowledge_base: KnowledgeBase 实例
            query: 查询文本
            n_results: 返回结果数量

        Returns:
            相似文档列表
        """
        if not knowledge_base.collection_name:
            return []

        results = self.vector_store.query(
            collection_name=knowledge_base.collection_name,
            query_texts=[query],
            n_results=n_results
        )

        # 格式化结果
        formatted_results = []
        if results and results.get('ids'):
            for i, doc_id in enumerate(results['ids'][0]):
                formatted_results.append({
                    'id': doc_id,
                    'text': results['documents'][0][i] if results.get('documents') else '',
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                    'distance': results['distances'][0][i] if results.get('distances') else 0
                })

        return formatted_results

    def hybrid_search(
        self,
        knowledge_base,
        query: str,
        n_results: int = 5,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        keyword_limit: int = 20
    ) -> List[Dict]:
        """
        混合检索：结合关键词检索和语义检索

        Args:
            knowledge_base: KnowledgeBase 实例
            query: 查询文本
            n_results: 最终返回结果数量
            keyword_weight: 关键词检索权重 (0-1)
            semantic_weight: 语义检索权重 (0-1)
            keyword_limit: 关键词检索返回数量上限

        Returns:
            混合检索结果列表，按综合得分排序
        """
        from .models import KnowledgeDocument

        # 1. 语义检索
        semantic_results = []
        if knowledge_base.collection_name and knowledge_base.enable_vectorization:
            semantic_results = self.search_similar(
                knowledge_base=knowledge_base,
                query=query,
                n_results=n_results * 2  # 获取更多结果用于合并
            )

        # 2. 关键词检索（数据库全文搜索）
        keyword_results = []
        keywords = query.strip().split()
        if keywords:
            # 构建关键词查询
            from django.db.models import Q
            q_objects = Q()
            for keyword in keywords:
                q_objects |= Q(title__icontains=keyword)
                q_objects |= Q(content__icontains=keyword)
                q_objects |= Q(description__icontains=keyword)
                q_objects |= Q(tags__icontains=keyword)

            # 同时查询已发布和预览状态的文档
            docs = KnowledgeDocument.objects.filter(
                knowledge_base=knowledge_base,
                status__in=['published', 'draft']
            ).filter(q_objects)[:keyword_limit]

            logger.info(f"关键词检索找到 {docs.count()} 个文档")

            for doc in docs:
                # 计算关键词匹配得分（简单的词频统计）
                content_lower = (doc.title + ' ' + (doc.content or '') + ' ' + (doc.description or '')).lower()
                match_count = sum(1 for kw in keywords if kw.lower() in content_lower)
                keyword_score = min(match_count / max(len(keywords), 1), 1.0)

                # 获取完整内容
                full_content = doc.content or ''
                logger.info(f"文档 '{doc.title}' 内容长度: {len(full_content)} 字符")

                keyword_results.append({
                    'document_id': doc.id,
                    'document_title': doc.title,
                    'text': full_content,  # 返回完整内容
                    'full_content': full_content,
                    'file_url': doc.file.url if doc.file else None,
                    'keyword_score': keyword_score,
                    'source': 'keyword'
                })

        # 3. 合并结果
        result_map = {}  # 使用 document_id 作为 key

        # 添加语义检索结果
        for result in semantic_results:
            metadata = result.get('metadata', {})
            doc_id = metadata.get('document_id')
            if doc_id:
                if doc_id not in result_map:
                    result_map[doc_id] = {
                        'document_id': doc_id,
                        'document_title': metadata.get('title', ''),
                        'text': result.get('text', ''),
                        'semantic_score': 1 - result.get('distance', 0),  # 距离转相似度
                        'keyword_score': 0,
                        'source': 'semantic',
                        'chunk_id': result.get('id'),
                        'file_url': None,
                        'full_content': None
                    }
                else:
                    # 如果已存在，更新语义得分（取最高）
                    existing_score = result_map[doc_id].get('semantic_score', 0)
                    new_score = 1 - result.get('distance', 0)
                    if new_score > existing_score:
                        result_map[doc_id]['semantic_score'] = new_score
                        result_map[doc_id]['text'] = result.get('text', '')

        # 添加关键词检索结果
        for result in keyword_results:
            doc_id = result['document_id']
            if doc_id in result_map:
                # 合并：更新关键词得分和补充信息
                result_map[doc_id]['keyword_score'] = result['keyword_score']
                result_map[doc_id]['source'] = 'hybrid'
                result_map[doc_id]['file_url'] = result['file_url']
                result_map[doc_id]['full_content'] = result['full_content']
            else:
                result_map[doc_id] = {
                    'document_id': doc_id,
                    'document_title': result['document_title'],
                    'text': result['text'],
                    'semantic_score': 0,
                    'keyword_score': result['keyword_score'],
                    'source': 'keyword',
                    'chunk_id': None,
                    'file_url': result['file_url'],
                    'full_content': result['full_content']
                }

        # 4. 计算综合得分并排序
        final_results = []
        for doc_id, result in result_map.items():
            combined_score = (
                result['semantic_score'] * semantic_weight +
                result['keyword_score'] * keyword_weight
            )
            result['combined_score'] = combined_score
            final_results.append(result)

        # 按综合得分降序排序
        final_results.sort(key=lambda x: x['combined_score'], reverse=True)

        # 5. 补充文档的 file_url 信息
        doc_ids = [r['document_id'] for r in final_results if r['document_id']]
        if doc_ids:
            docs_with_files = KnowledgeDocument.objects.filter(id__in=doc_ids)
            doc_file_map = {d.id: (d.file.url if d.file else None, d.content) for d in docs_with_files}
            for result in final_results:
                doc_id = result.get('document_id')
                if doc_id and doc_id in doc_file_map:
                    if not result.get('file_url'):
                        result['file_url'] = doc_file_map[doc_id][0]
                    if not result.get('full_content'):
                        result['full_content'] = doc_file_map[doc_id][1]

        return final_results[:n_results]

    def delete_knowledge_base_vectors(self, knowledge_base) -> bool:
        """删除知识库的所有向量数据"""
        if knowledge_base.collection_name:
            return self.vector_store.delete_collection(knowledge_base.collection_name)
        return True


# 单例服务实例
knowledge_base_service = KnowledgeBaseService()
