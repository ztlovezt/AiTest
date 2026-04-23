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

from django.db import connection, OperationalError, ProgrammingError


def get_knowledge_base_config():
    """
    获取知识库配置
    
    Returns:
        dict: 配置信息，包含 configured, has_embedding, has_tika, has_refiner 等状态
    """
    config_status = {
        'configured': False,
        'has_embedding': False,
        'has_tika': False,
        'has_refiner': False,
        'config': None,
        'message': ''
    }
    
    try:
        if connection.introspection.table_names():
            from apps.knowledge_base.models import KnowledgeBaseConfig
            db_config = KnowledgeBaseConfig.objects.filter(is_active=True).first()
            
            if db_config:
                config_status['config'] = db_config
                config_status['has_embedding'] = bool(db_config.embedding_api_key)
                config_status['has_tika'] = bool(db_config.tika_server_url)
                config_status['has_refiner'] = bool(db_config.refiner_api_key)
                config_status['configured'] = (
                    config_status['has_embedding'] or 
                    config_status['has_tika'] or 
                    config_status['has_refiner']
                )
                
                if not config_status['configured']:
                    config_status['message'] = '知识库配置未设置，请在设置中心配置知识库相关参数'
            else:
                config_status['message'] = '未找到激活的知识库配置，请在设置中心配置知识库相关参数'
        else:
            config_status['message'] = '数据库表尚未创建，请先执行数据库迁移'
            
    except (OperationalError, ProgrammingError, Exception) as e:
        config_status['message'] = f'获取配置失败: {str(e)}'
        logger.warning(f"获取知识库配置失败: {e}")
    
    return config_status


def check_knowledge_base_config(require_embedding=False, require_tika=False, require_refiner=False):
    """
    检查知识库配置是否满足要求
    
    Args:
        require_embedding: 是否需要 Embedding 配置
        require_tika: 是否需要 Tika 配置
        require_refiner: 是否需要 Refiner 配置
        
    Returns:
        tuple: (is_valid, error_message)
    """
    config_status = get_knowledge_base_config()
    
    if not config_status['configured']:
        return False, config_status['message'] or '知识库配置未设置，请在设置中心配置知识库相关参数'
    
    if require_embedding and not config_status['has_embedding']:
        return False, 'Embedding API 未配置，请在设置中心配置 Embedding 相关参数'
    
    if require_tika and not config_status['has_tika']:
        return False, 'Tika Server URL 未配置，请在设置中心配置 Tika 相关参数'
    
    if require_refiner and not config_status['has_refiner']:
        return False, 'Refiner API 未配置，请在设置中心配置 Refiner 相关参数'
    
    return True, ''


class TikaParser:
    """Tika Server 文档解析服务"""

    def __init__(self):
        self._config_loaded = False
        self.tika_server_url = None

    def _ensure_config(self):
        """延迟加载配置"""
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
        """调用 Tika Server 提取纯文本"""
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
    """文档解析器 - 统一使用 Tika Server 解析各种文档"""

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
        self._embedding_initialized = False

    def _ensure_embedding(self):
        """确保 embedding 已初始化（延迟加载）"""
        if self._embedding_initialized:
            return
        self._init_embedding()
        self._embedding_initialized = True

    def _init_chroma(self):
        """初始化 ChromaDB 客户端"""
        if self.chroma_client is not None:
            return
            
        try:
            import chromadb
            from chromadb.config import Settings

            chroma_path = settings.PATHS_CHROMA_DB
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
        """初始化嵌入模型，从数据库读取配置"""
        if self.embedding_function is not None:
            return
            
        try:
            from chromadb.utils import embedding_functions

            api_key = None
            base_url = None
            embedding_model = None

            try:
                if connection.introspection.table_names():
                    from apps.knowledge_base.models import KnowledgeBaseConfig
                    db_config = KnowledgeBaseConfig.objects.filter(is_active=True).first()
                    if db_config and db_config.embedding_api_key:
                        api_key = db_config.embedding_api_key
                        base_url = db_config.embedding_base_url
                        embedding_model = db_config.embedding_model or "text-embedding-v3"
                        logger.debug(f"从数据库加载 Embedding 配置成功")
            except (OperationalError, ProgrammingError, Exception) as e:
                logger.warning(f"数据库查询 embedding 配置失败: {e}")

            if not api_key:
                logger.warning("未配置 Embedding API Key，请在设置中心配置知识库相关参数，向量检索功能将不可用")
                self.embedding_function = None
                return

            if not embedding_model:
                embedding_model = "text-embedding-v3"
                logger.info(f"使用默认 Embedding 模型: {embedding_model}")

            self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name=embedding_model,
                api_base=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            logger.info(f"Embedding 模型初始化成功: {embedding_model}")

        except ImportError as e:
            logger.error(f"嵌入函数初始化失败: {e}")
            self.embedding_function = None
        except Exception as e:
            logger.error(f"嵌入模型初始化失败: {e}")
            self.embedding_function = None

    def get_or_create_collection(self, collection_name: str):
        """获取或创建向量集合"""
        self._init_chroma()
        self._ensure_embedding()
        
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
        self._init_chroma()
        
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
        use_vision_direct: bool = False
    ) -> Dict[str, Any]:
        """
        处理单个文档：解析文本、分块、向量化

        Args:
            document: KnowledgeDocument 实例
            chunk_size: 分块大小
            chunk_overlap: 分块重叠
            enable_vectorization: 是否进行向量化
            use_vision: 是否使用视觉模型解析图片（本地解析模式）
            use_vision_direct: 是否直接使用视觉模型解析整个文档（推荐，完全跳过本地解析）

        Returns:
            处理结果
        """
        result = {
            'success': False,
            'text_length': 0,
            'chunk_count': 0,
            'vectorized': False,
            'error': None,
            'parse_method': 'tika_direct'
        }

        try:
            if use_vision_direct:
                is_valid, error_msg = check_knowledge_base_config(require_tika=True)
                if not is_valid:
                    result['error'] = error_msg
                    from .models import KnowledgeDocument
                    KnowledgeDocument.objects.filter(pk=document.pk).update(
                        vector_status='failed',
                        vector_error=error_msg
                    )
                    return result

            if enable_vectorization:
                is_valid, error_msg = check_knowledge_base_config(require_embedding=True)
                if not is_valid:
                    result['error'] = error_msg
                    from .models import KnowledgeDocument
                    KnowledgeDocument.objects.filter(pk=document.pk).update(
                        vector_status='failed',
                        vector_error=error_msg
                    )
                    return result

            # 1. 提取文本
            if document.file and os.path.exists(document.file.path):
                logger.info(f"使用 Tika Server 解析文档: {document.title}")
                text = tika_parser.extract_text(
                    document.file.path
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
            combined_score = max(0.0, min(1.0, combined_score))
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
