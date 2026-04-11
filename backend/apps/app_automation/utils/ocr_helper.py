# -*- coding: utf-8 -*-
"""
OCR 工具类 - 统一 OCR 服务层
支持 Tesseract 和 PP-OCRv5
"""
import os
import time
import logging
import hashlib
from typing import Any, Dict, Optional, Tuple
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageEnhance

from airtest.core.api import G, sleep as airtest_sleep

logger = logging.getLogger(__name__)


class OCRHelper:
    """OCR 辅助类 - 提供图像文字识别功能"""
    
    _ocr_cache = {}
    _cache_ttl = 2.0
    _cache_max_size = 100
    
    _ocr_service = None
    _config = None
    
    def __init__(
        self,
        ocr_engine: str = 'tesseract',
        language: str = 'chi_sim+eng',
        use_gpu: bool = False,
        min_confidence: float = 0.3
    ):
        """
        初始化 OCR 助手
        
        Args:
            ocr_engine: OCR 引擎 ('tesseract' 或 'ppocr')
            language: OCR 识别语言
            use_gpu: 是否使用 GPU 加速
            min_confidence: 最小置信度阈值
        """
        from django.conf import settings
        self._cache_max_size = getattr(settings, 'OCR_MAX_IMAGE_SIZE', 100)
        
        self.ocr_engine = ocr_engine
        self.language = language
        self.use_gpu = use_gpu
        self.min_confidence = min_confidence
        
        self._init_ocr_service()
    
    def _init_ocr_service(self):
        """初始化 OCR 服务"""
        try:
            from apps.ocr_service.adapters import (
                get_ocr_service,
                OCREngineType,
                OCRLanguage,
                OCRConfig
            )
            
            self._ocr_service = get_ocr_service()
            
            lang_map = {
                'chi_sim': OCRLanguage.CHINESE,
                'eng': OCRLanguage.ENGLISH,
                'chi_sim+eng': OCRLanguage.CHINESE_ENGLISH,
                'japan': OCRLanguage.JAPANESE,
                'korean': OCRLanguage.KOREAN,
            }
            
            engine_type_map = {
                'tesseract': OCREngineType.TESSERACT,
                'ppocr': OCREngineType.PPOCR,
            }
            
            self._config = OCRConfig(
                engine_type=engine_type_map.get(self.ocr_engine, OCREngineType.TESSERACT),
                language=lang_map.get(self.language, OCRLanguage.CHINESE_ENGLISH),
                use_gpu=self.use_gpu,
                min_confidence=self.min_confidence
            )
            
            logger.info(f"OCR 服务初始化完成: engine={self.ocr_engine}, language={self.language}")
            
        except Exception as e:
            logger.error(f"OCR 服务初始化失败: {e}")
            self._ocr_service = None
            self._config = None
    
    @staticmethod
    def _get_image_hash(img) -> str:
        """计算图片的hash值用于缓存"""
        if isinstance(img, Image.Image):
            img_array = np.array(img)
        else:
            img_array = img
        return hashlib.md5(img_array.tobytes()).hexdigest()
    
    @classmethod
    def _get_cache_key(cls, region: Tuple, img_hash: str) -> Tuple:
        """生成缓存key"""
        return (tuple(region), img_hash)
    
    @classmethod
    def _clean_cache(cls):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in cls._ocr_cache.items()
            if current_time - timestamp > cls._cache_ttl
        ]
        for key in expired_keys:
            cls._ocr_cache.pop(key, None)
        
        if len(cls._ocr_cache) > cls._cache_max_size:
            sorted_items = sorted(
                cls._ocr_cache.items(),
                key=lambda x: x[1][1]
            )
            for key, _ in sorted_items[:len(sorted_items)//2]:
                cls._ocr_cache.pop(key, None)
    
    def recognize_text(self, img, min_confidence=None, use_cache=True) -> str:
        """
        识别图片中的文本
        
        Args:
            img: PIL Image 对象
            min_confidence: 最小置信度阈值
            use_cache: 是否使用缓存
            
        Returns:
            识别出的文本字符串
        """
        if self._ocr_service is None:
            logger.error("OCR 服务未初始化")
            return ""
        
        min_conf = min_confidence if min_confidence is not None else self.min_confidence
        
        img_hash = None
        cache_key = None
        if use_cache:
            img_hash = self._get_image_hash(img)
            cache_key = (img_hash,)
            if cache_key in self._ocr_cache:
                result, timestamp = self._ocr_cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    logger.debug(f"使用缓存 OCR 结果: {result}")
                    return result
        
        try:
            from apps.ocr_service.adapters import OCREngineType
            
            result = self._ocr_service.recognize(
                img,
                engine_type=self._config.engine_type,
                config=self._config
            )
            
            if not result.success:
                logger.error(f"OCR 识别失败: {result.error_message}")
                return ""
            
            texts = []
            for item in result.texts:
                if item.confidence >= min_conf:
                    texts.append(item.text)
                    logger.debug(f"OCR: '{item.text}', 置信度: {item.confidence:.2f}")
            
            combined_text = ' '.join(texts)
            
            if use_cache and cache_key:
                self._ocr_cache[cache_key] = (combined_text, time.time())
                self._clean_cache()
            
            logger.info(f"OCR 识别结果: '{combined_text}'")
            return combined_text.strip()
            
        except Exception as e:
            logger.error(f"OCR 识别失败: {e}")
            return ""
    
    def recognize_number(self, img, allow_comma=True, use_cache=True) -> int:
        """
        识别图片中的数字
        
        Args:
            img: PIL Image 对象
            allow_comma: 是否允许逗号分隔符
            use_cache: 是否使用缓存
            
        Returns:
            识别出的数字（整数）
        """
        text = self.recognize_text(img, use_cache=use_cache)
        
        text = text.replace('o', '0').replace('O', '0')
        text = text.replace('l', '1').replace('I', '1')
        text = text.replace('?', '1')
        
        if allow_comma:
            digits = ''.join(filter(lambda x: x.isdigit() or x == ',', text))
            digits = digits.replace(',', '')
        else:
            digits = ''.join(filter(str.isdigit, text))
        
        try:
            number = int(digits) if digits else 0
            logger.info(f"提取数字: {number}")
            return number
        except ValueError:
            logger.error(f"无法将文本转换为数字: {text}")
            return 0
    
    @staticmethod
    def crop_region(region: Tuple[int, int, int, int], screenshot_path: Optional[str] = None) -> Image.Image:
        """
        裁剪屏幕指定区域
        
        Args:
            region: 坐标元组 (x1, y1, x2, y2)
            screenshot_path: 截图文件路径（可选，如果不提供则实时截图）
            
        Returns:
            裁剪后的 PIL Image
        """
        if screenshot_path and os.path.exists(screenshot_path):
            img_cv = cv2.imread(screenshot_path)
        else:
            airtest_sleep(0.3)
            img_cv = G.DEVICE.snapshot()
            if img_cv is None:
                raise RuntimeError("截图失败，snapshot 返回 None")
        
        x1, y1, x2, y2 = region
        cropped = img_cv[y1:y2, x1:x2]
        
        pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
        
        pil_img = ImageEnhance.Contrast(pil_img).enhance(2.0)
        
        return pil_img
    
    def recognize_region_text(self, region: Tuple[int, int, int, int], screenshot_path: Optional[str] = None) -> str:
        """
        识别屏幕指定区域的文本
        
        Args:
            region: 坐标元组 (x1, y1, x2, y2)
            screenshot_path: 截图文件路径（可选）
            
        Returns:
            识别出的文本
        """
        img = self.crop_region(region, screenshot_path)
        return self.recognize_text(img)
    
    def recognize_region_number(self, region: Tuple[int, int, int, int], screenshot_path: Optional[str] = None) -> int:
        """
        识别屏幕指定区域的数字
        
        Args:
            region: 坐标元组 (x1, y1, x2, y2)
            screenshot_path: 截图文件路径（可选）
            
        Returns:
            识别出的数字
        """
        img = self.crop_region(region, screenshot_path)
        return self.recognize_number(img)


_ocr_helper_instance = None


def get_ocr_helper(
    ocr_engine: str = 'tesseract',
    language: str = 'chi_sim+eng',
    use_gpu: bool = False
) -> OCRHelper:
    """
    获取全局 OCR Helper 单例实例
    
    Args:
        ocr_engine: OCR 引擎
        language: OCR 识别语言
        use_gpu: 是否使用 GPU
        
    Returns:
        OCRHelper 实例
    """
    global _ocr_helper_instance
    
    if _ocr_helper_instance is None:
        _ocr_helper_instance = OCRHelper(
            ocr_engine=ocr_engine,
            language=language,
            use_gpu=use_gpu
        )
    else:
        if (_ocr_helper_instance.ocr_engine != ocr_engine or
            _ocr_helper_instance.language != language or
            _ocr_helper_instance.use_gpu != use_gpu):
            _ocr_helper_instance = OCRHelper(
                ocr_engine=ocr_engine,
                language=language,
                use_gpu=use_gpu
            )
    
    return _ocr_helper_instance


def get_ocr_helper_from_config() -> OCRHelper:
    """
    从数据库配置获取 OCR Helper
    
    Returns:
        OCRHelper 实例
    """
    try:
        from apps.app_automation.models import AppTestConfig
        
        config = AppTestConfig.objects.first()
        if config:
            return get_ocr_helper(
                ocr_engine=config.ocr_engine,
                language=config.ocr_language,
                use_gpu=config.ocr_use_gpu
            )
    except Exception as e:
        logger.warning(f"从数据库获取 OCR 配置失败: {e}")
    
    return get_ocr_helper()
