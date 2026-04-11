# -*- coding: utf-8 -*-
"""
PP-OCRv5 离线模型适配器 (PaddleOCR 3.x 版本)
"""
import os
import tempfile

os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['FLAGS_cinn_new_group_scheduler'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_check_cuda_version'] = '0'
os.environ['FLAGS_skip_allocator_mem_check'] = '1'

from typing import List, Optional, Union, Any, Dict

from PIL import Image
import numpy as np

from django.conf import settings
from backend.log_config import get_logger
from .base import BaseOCRAdapter, OCRResult, OCRTextItem, OCRLanguage, OCRConfig, OCREngineType

logger = get_logger(__name__)

PPOCR_AVAILABLE = False

try:
    from paddleocr import PaddleOCR
    PPOCR_AVAILABLE = True
except ImportError:
    logger.warning("PaddleOCR not installed. PP-OCRv5 will not be available.")


def get_ocr_config() -> Dict[str, Any]:
    """从 config.yaml 获取 OCR 配置（系统级配置）"""
    config = getattr(settings, 'OCR_CONFIG', {})
    return {
        'model_type': config.get('model_type', 'mobile'),
        'timeout': config.get('timeout', 300),
        'max_concurrent_tasks': config.get('max_concurrent_tasks', 3),
        'warmup_enabled': config.get('warmup_enabled', True),
    }


def get_database_ocr_config(ocr_config_id: Optional[int] = None) -> Dict[str, Any]:
    """从数据库获取 OCR 配置（用户配置）"""
    try:
        from apps.ocr_service.models import OCRConfig as OCRConfigModel
        
        if ocr_config_id:
            config = OCRConfigModel.objects.filter(id=ocr_config_id, is_active=True).first()
        else:
            config = OCRConfigModel.get_default_config()
        
        if config:
            return {
                'use_gpu': config.use_gpu,
                'language': config.language,
                'min_confidence': config.min_confidence,
                'extra_config': config.extra_config or {},
            }
    except Exception as e:
        logger.warning(f"Failed to get OCR config from database: {e}")
    
    return {
        'use_gpu': False,
        'language': 'chi_sim+eng',
        'min_confidence': 0.3,
        'extra_config': {},
    }


def check_gpu_available() -> bool:
    """检查 GPU 是否可用"""
    try:
        import paddle
        if paddle.is_compiled_with_cuda():
            gpu_count = paddle.device.cuda.device_count()
            return gpu_count > 0
        return False
    except Exception:
        return False


class PPOCRAdapter(BaseOCRAdapter):
    """PP-OCRv5 离线模型适配器 (PaddleOCR 3.x)"""
    
    _ppocr_instance = None
    _ppocr_instance_gpu = None
    _config = None
    _gpu_available = None
    
    def __init__(self, config: Optional[OCRConfig] = None, ocr_config_id: Optional[int] = None):
        super().__init__(config)
        
        if not PPOCR_AVAILABLE:
            raise ImportError(
                "PaddleOCR not installed. Please install: pip install paddlepaddle paddleocr"
            )
        
        self._config = get_ocr_config()
        self._db_config = get_database_ocr_config(ocr_config_id)
        
        if self.__class__._gpu_available is None:
            self.__class__._gpu_available = check_gpu_available()
    
    @property
    def engine_type(self) -> OCREngineType:
        return OCREngineType.PPOCR
    
    def initialize(self) -> bool:
        """
        初始化 PP-OCRv5 引擎
        
        Returns:
            是否初始化成功
        """
        if not PPOCR_AVAILABLE:
            logger.warning("PaddleOCR not installed. Please install: pip install paddlepaddle paddleocr")
            self._initialized = False
            return False
        
        try:
            lang = self._get_ppocr_lang()
            use_gpu = self._db_config.get('use_gpu', False)
            
            if use_gpu and not self._gpu_available:
                logger.warning("GPU acceleration requested but GPU is not available, falling back to CPU")
                use_gpu = False
            
            self.get_ppocr_instance(lang=lang, use_gpu=use_gpu)
            logger.info(f"PP-OCRv5 initialized successfully (use_gpu={use_gpu})")
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize PP-OCRv5: {e}")
            self._initialized = False
            return False
    
    def is_available(self) -> bool:
        """检查 PP-OCRv5 是否可用"""
        return PPOCR_AVAILABLE
    
    @classmethod
    def check_installation(cls) -> Dict[str, Any]:
        """检查 PP-OCR 安装状态"""
        result = {
            'installed': PPOCR_AVAILABLE,
            'version': None,
            'gpu_support': False,
            'message': ''
        }
        
        if PPOCR_AVAILABLE:
            try:
                import paddle
                result['version'] = paddle.__version__
                result['gpu_support'] = check_gpu_available()
                result['message'] = f"PaddlePaddle {result['version']} 已安装"
            except Exception as e:
                result['message'] = f"检测失败: {str(e)}"
        else:
            result['message'] = "PaddlePaddle 未安装，请运行: pip install paddlepaddle paddleocr"
        
        return result
    
    @classmethod
    def get_ppocr_instance(
        cls,
        lang: str = 'ch',
        use_gpu: bool = False,
        gpu_id: int = 0
    ) -> Any:
        """
        获取 PaddleOCR 实例（单例模式）
        
        Args:
            lang: 语言 ('ch', 'en', 'korean', 'japan' 等)
            use_gpu: 是否使用 GPU
            gpu_id: GPU 设备ID
            
        Returns:
            PaddleOCR 实例
        """
        config = get_ocr_config()
        model_type = config.get('model_type', 'mobile')
        device = f'gpu:{gpu_id}' if use_gpu else 'cpu'
        
        if use_gpu:
            if not cls._gpu_available:
                logger.warning("GPU not available, falling back to CPU instance")
                use_gpu = False
                device = 'cpu'
            else:
                if cls._ppocr_instance_gpu is None:
                    logger.info(f"Initializing PaddleOCR 3.x GPU (lang={lang}, model={model_type}, device={device})...")
                    logger.info("First time use will download model, please wait...")
                    
                    try:
                        init_params = {
                            'use_textline_orientation': True,
                            'lang': lang,
                            'device': device,
                            'enable_mkldnn': False,
                        }
                        
                        if model_type == 'mobile':
                            init_params['ocr_version'] = 'PP-OCRv5'
                        
                        cls._ppocr_instance_gpu = PaddleOCR(**init_params)
                        logger.info(f"PaddleOCR 3.x GPU initialized successfully (model={model_type})")
                    except Exception as e:
                        logger.error(f"PaddleOCR GPU init failed: {e}, falling back to CPU")
                        cls._gpu_available = False
                        use_gpu = False
                        device = 'cpu'
                else:
                    return cls._ppocr_instance_gpu
        
        if not use_gpu:
            if cls._ppocr_instance is None:
                logger.info(f"Initializing PaddleOCR 3.x CPU (lang={lang}, model={model_type})...")
                logger.info("First time use will download model, please wait...")
                
                try:
                    init_params = {
                        'use_textline_orientation': True,
                        'lang': lang,
                        'device': 'cpu',
                        'enable_mkldnn': False,
                    }
                    
                    if model_type == 'mobile':
                        init_params['ocr_version'] = 'PP-OCRv5'
                    
                    cls._ppocr_instance = PaddleOCR(**init_params)
                    logger.info(f"PaddleOCR 3.x CPU initialized successfully (model={model_type})")
                except Exception as e:
                    logger.error(f"PaddleOCR CPU init failed: {e}")
                    raise
            return cls._ppocr_instance
    
    @classmethod
    def reset_instance(cls):
        """重置 OCR 实例（用于配置变更时）"""
        cls._ppocr_instance = None
        cls._ppocr_instance_gpu = None
        cls._gpu_available = None
    
    def _get_ppocr_lang(self, language: Optional[OCRLanguage] = None) -> str:
        """获取 PaddleOCR 语言代码"""
        lang = language or self.config.language
        
        lang_map = {
            OCRLanguage.CHINESE: 'ch',
            OCRLanguage.ENGLISH: 'en',
            OCRLanguage.CHINESE_ENGLISH: 'ch',
            OCRLanguage.JAPANESE: 'japan',
            OCRLanguage.KOREAN: 'korean',
        }
        
        return lang_map.get(lang, 'ch')
    
    def recognize(
        self,
        image: Union[Image.Image, np.ndarray, str],
        language: Optional[OCRLanguage] = None,
        **kwargs
    ) -> OCRResult:
        """
        使用 PP-OCRv5 识别图像中的文字
        
        Args:
            image: PIL Image、numpy array 或图像路径
            language: 识别语言
            **kwargs: 额外参数
                
        Returns:
            OCRResult 识别结果
        """
        import time
        start_time = time.time()
        
        try:
            lang = self._get_ppocr_lang(language)
            use_gpu = self._db_config.get('use_gpu', False)
            
            if use_gpu and not self._gpu_available:
                logger.warning("GPU requested but not available, using CPU instead")
                use_gpu = False
            
            ocr = self.get_ppocr_instance(lang=lang, use_gpu=use_gpu)
            
            if isinstance(image, str) and os.path.exists(image):
                img = self.load_image(image)
                original_size = img.size
                img, scale = self.resize_for_ocr(img)
                if scale != 1.0:
                    logger.info(f"Image resized: {original_size} -> {img.size} (scale={scale:.2f})")
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                img.save(tmp_path)
                image_path = tmp_path
                need_cleanup = True
            else:
                img = self.load_image(image)
                original_size = img.size
                img, scale = self.resize_for_ocr(img)
                if scale != 1.0:
                    logger.info(f"Image resized: {original_size} -> {img.size} (scale={scale:.2f})")
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                img.save(tmp_path)
                image_path = tmp_path
                need_cleanup = True
            
            try:
                results = ocr.predict([image_path])
                
                texts = []
                if results:
                    for item in results:
                        if isinstance(item, dict) and 'rec_texts' in item and item['rec_texts']:
                            for text in item['rec_texts']:
                                texts.append(OCRTextItem(
                                    text=text,
                                    confidence=1.0,
                                    bbox=(0, 0, 0, 0)
                                ))
                
                elapsed = time.time() - start_time
                logger.info(f"PP-OCRv5 recognized {len(texts)} text items in {elapsed:.2f}s (gpu={use_gpu})")
                
                return OCRResult(
                    texts=texts,
                    success=True,
                    engine=self.engine_type
                )
                
            finally:
                if need_cleanup and os.path.exists(image_path):
                    os.remove(image_path)
            
        except Exception as e:
            logger.error(f"PP-OCRv5 recognition failed: {e}")
            return OCRResult(
                texts=[],
                success=False,
                engine=self.engine_type,
                error_message=str(e)
            )
    
    def recognize_batch(
        self,
        images: List[Union[Image.Image, np.ndarray, str]],
        language: Optional[OCRLanguage] = None,
        **kwargs
    ) -> List[OCRResult]:
        """
        批量识别图像中的文字
        
        Args:
            images: 图像列表（PIL Image、numpy array 或图像路径）
            language: 识别语言
            **kwargs: 额外参数
                
        Returns:
            OCRResult 列表
        """
        import time
        start_time = time.time()
        
        lang = self._get_ppocr_lang(language)
        use_gpu = self._db_config.get('use_gpu', False)
        
        if use_gpu and not self._gpu_available:
            logger.warning("GPU requested but not available, using CPU instead")
            use_gpu = False
        
        ocr = self.get_ppocr_instance(lang=lang, use_gpu=use_gpu)
        
        image_paths = []
        cleanup_paths = []
        
        try:
            for img in images:
                if isinstance(img, str) and os.path.exists(img):
                    loaded_img = self.load_image(img)
                    loaded_img, scale = self.resize_for_ocr(loaded_img)
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp_path = tmp.name
                    loaded_img.save(tmp_path)
                    image_paths.append(tmp_path)
                    cleanup_paths.append(tmp_path)
                else:
                    loaded_img = self.load_image(img)
                    loaded_img, scale = self.resize_for_ocr(loaded_img)
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                        tmp_path = tmp.name
                    loaded_img.save(tmp_path)
                    image_paths.append(tmp_path)
                    cleanup_paths.append(tmp_path)
            
            results = ocr.predict(image_paths)
            
            all_results = []
            if results:
                for item in results:
                    texts = []
                    if isinstance(item, dict) and 'rec_texts' in item and item['rec_texts']:
                        for text in item['rec_texts']:
                            texts.append(OCRTextItem(
                                text=text,
                                confidence=1.0,
                                bbox=(0, 0, 0, 0)
                            ))
                    
                    all_results.append(OCRResult(
                        texts=texts,
                        success=True,
                        engine=self.engine_type
                    ))
            
            while len(all_results) < len(images):
                all_results.append(OCRResult(
                    texts=[],
                    success=False,
                    engine=self.engine_type,
                    error_message="No result returned"
                ))
            
            elapsed = time.time() - start_time
            logger.info(f"PP-OCRv5 batch recognized {len(images)} images in {elapsed:.2f}s (gpu={use_gpu})")
            
            return all_results
            
        except Exception as e:
            logger.error(f"PP-OCRv5 batch recognition failed: {e}")
            return [OCRResult(
                texts=[],
                success=False,
                engine=self.engine_type,
                error_message=str(e)
            ) for _ in images]
        
        finally:
            for path in cleanup_paths:
                if os.path.exists(path):
                    os.remove(path)
