# -*- coding: utf-8 -*-
"""
在线 OCR 大模型适配器
支持 OpenAI GPT-4V、智谱 GLM-4V、百度 AI OCR 等
"""
import base64
from enum import Enum
from typing import List, Optional, Union, Any, Dict
from io import BytesIO

from PIL import Image
import numpy as np
import httpx

from backend.log_config import get_logger
from .base import BaseOCRAdapter, OCRResult, OCRTextItem, OCRLanguage, OCRConfig, OCREngineType

logger = get_logger(__name__)


class OnlineOCRProvider(Enum):
    """在线 OCR 服务提供商"""
    OPENAI = 'openai'
    ZHIPU = 'zhipu'
    BAIDU = 'baidu'
    TENCENT = 'tencent'
    ALIYUN = 'aliyun'
    CUSTOM = 'custom'


class OnlineOCRAdapter(BaseOCRAdapter):
    """在线 OCR 大模型适配器"""
    
    PROVIDER_CONFIGS = {
        OnlineOCRProvider.OPENAI: {
            'default_model': 'gpt-4o',
            'default_base_url': 'https://api.openai.com/v1',
        },
        OnlineOCRProvider.ZHIPU: {
            'default_model': 'glm-4v',
            'default_base_url': 'https://open.bigmodel.cn/api/paas/v4',
        },
    }
    
    def __init__(self, config: Optional[OCRConfig] = None):
        super().__init__(config)
        
        provider_str = self.config.online_provider or 'openai'
        try:
            self.provider = OnlineOCRProvider(provider_str.lower())
        except ValueError:
            self.provider = OnlineOCRProvider.CUSTOM
    
    @property
    def engine_type(self) -> OCREngineType:
        return OCREngineType.ONLINE
    
    def initialize(self) -> bool:
        """
        初始化在线 OCR 引擎
        
        Returns:
            是否初始化成功
        """
        if not self.config.online_api_key and self.provider not in [OnlineOCRProvider.CUSTOM]:
            logger.warning("API key not configured for online OCR")
            self._initialized = False
            return False
        
        if not self.config.online_base_url:
            provider_config = self.PROVIDER_CONFIGS.get(self.provider, {})
            self.config.online_base_url = provider_config.get('default_base_url')
        
        logger.info(f"Online OCR initialized: provider={self.provider.value}")
        self._initialized = True
        return True
    
    def _image_to_base64(self, image: Union[Image.Image, np.ndarray, str]) -> str:
        """将图像转换为 base64 编码"""
        img = self.load_image(image)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _build_openai_request(
        self,
        image_base64: str,
        language: Optional[OCRLanguage] = None
    ) -> Dict[str, Any]:
        """构建 OpenAI API 请求"""
        lang_hint = "中文" if language in [OCRLanguage.CHINESE, OCRLanguage.CHINESE_ENGLISH] else "English"
        
        return {
            "model": self.config.online_model or 'gpt-4o',
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"请识别这张图片中的所有{lang_hint}文字，直接输出识别结果，不要添加任何解释或格式化。如果图片中没有文字，请输出'无文字'。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096
        }
    
    def _build_zhipu_request(
        self,
        image_base64: str,
        language: Optional[OCRLanguage] = None
    ) -> Dict[str, Any]:
        """构建智谱 API 请求"""
        lang_hint = "中文" if language in [OCRLanguage.CHINESE, OCRLanguage.CHINESE_ENGLISH] else "English"
        
        return {
            "model": self.config.online_model or 'glm-4v',
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"请识别这张图片中的所有{lang_hint}文字，直接输出识别结果，不要添加任何解释或格式化。"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 4096
        }
    
    async def _call_api_async(
        self,
        image_base64: str,
        language: Optional[OCRLanguage] = None
    ) -> Dict[str, Any]:
        """异步调用在线 OCR API"""
        if self.provider == OnlineOCRProvider.OPENAI:
            request_body = self._build_openai_request(image_base64, language)
            endpoint = '/chat/completions'
        elif self.provider == OnlineOCRProvider.ZHIPU:
            request_body = self._build_zhipu_request(image_base64, language)
            endpoint = '/chat/completions'
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        base_url = self.config.online_base_url
        if not base_url:
            provider_config = self.PROVIDER_CONFIGS.get(self.provider, {})
            base_url = provider_config.get('default_base_url', '')
        
        base_url = base_url.rstrip('/')
        if not base_url.endswith(endpoint):
            url = f"{base_url}{endpoint}"
        else:
            url = base_url
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.online_api_key}"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=request_body, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def _call_api_sync(
        self,
        image_base64: str,
        language: Optional[OCRLanguage] = None
    ) -> Dict[str, Any]:
        """同步调用在线 OCR API"""
        if self.provider == OnlineOCRProvider.OPENAI:
            request_body = self._build_openai_request(image_base64, language)
            endpoint = '/chat/completions'
        elif self.provider == OnlineOCRProvider.ZHIPU:
            request_body = self._build_zhipu_request(image_base64, language)
            endpoint = '/chat/completions'
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        base_url = self.config.online_base_url
        if not base_url:
            provider_config = self.PROVIDER_CONFIGS.get(self.provider, {})
            base_url = provider_config.get('default_base_url', '')
        
        base_url = base_url.rstrip('/')
        if not base_url.endswith(endpoint):
            url = f"{base_url}{endpoint}"
        else:
            url = base_url
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.online_api_key}"
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=request_body, headers=headers)
            response.raise_for_status()
            return response.json()
    
    def recognize(
        self,
        image: Union[Image.Image, np.ndarray, str],
        language: Optional[OCRLanguage] = None,
        **kwargs
    ) -> OCRResult:
        """
        使用在线 OCR 服务识别图像中的文字
        
        Args:
            image: PIL Image、numpy array 或图像路径
            language: 识别语言
            **kwargs: 额外参数
                - async_mode: 是否使用异步模式
                
        Returns:
            OCRResult 识别结果
        """
        if not self.config.online_api_key:
            return OCRResult(
                texts=[],
                success=False,
                engine=self.engine_type,
                error_message="API key not configured"
            )
        
        try:
            image_base64 = self._image_to_base64(image)
            
            async_mode = kwargs.get('async_mode', False)
            
            if async_mode:
                import asyncio
                response = asyncio.run(self._call_api_async(image_base64, language))
            else:
                response = self._call_api_sync(image_base64, language)
            
            text = ""
            if 'choices' in response and len(response['choices']) > 0:
                message = response['choices'][0].get('message', {})
                text = message.get('content', '')
            
            if text == '无文字':
                return OCRResult(
                    texts=[],
                    success=True,
                    engine=self.engine_type
                )
            
            texts = [OCRTextItem(
                text=text,
                confidence=1.0,
                bbox=None
            )]
            
            logger.info(f"Online OCR recognized text: {text[:100]}...")
            
            return OCRResult(
                texts=texts,
                success=True,
                engine=self.engine_type,
                raw_result=response
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Online OCR API error: {e}")
            return OCRResult(
                texts=[],
                success=False,
                engine=self.engine_type,
                error_message=f"API error: {e.response.status_code}"
            )
        except Exception as e:
            logger.error(f"Online OCR recognition failed: {e}")
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
        """批量识别"""
        return [self.recognize(img, language, **kwargs) for img in images]
    
    def is_available(self) -> bool:
        """检查在线 OCR 服务是否可用"""
        return bool(self.config.online_api_key)
    
    @classmethod
    def check_configuration(cls, config: OCRConfig) -> dict:
        """
        检查在线 OCR 配置
        
        Returns:
            包含配置信息的字典
        """
        result = {
            'provider': config.online_provider,
            'model': config.online_model,
            'base_url': config.online_base_url,
            'api_key_configured': bool(config.online_api_key),
            'available': False,
            'error': None
        }
        
        if not config.online_api_key:
            result['error'] = 'API key not configured'
            return result
        
        result['available'] = True
        return result
