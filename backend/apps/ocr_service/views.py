# -*- coding: utf-8 -*-
"""
OCR 服务 API 视图
"""
import base64
import uuid
import time
from io import BytesIO

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage

from backend.log_config import get_logger

from .models import OCRConfig, OCRTask
from .serializers import (
    OCRConfigSerializer,
    OCRConfigListSerializer,
    OCRTaskSerializer,
    OCRRecognizeSerializer,
    OCRRecognizeResultSerializer
)
from .adapters import (
    get_ocr_service,
    OCREngineType,
    OCRLanguage,
    OCRConfig as OCRConfigData,
    TesseractAdapter,
    PPOCRAdapter,
    OnlineOCRAdapter,
)

logger = get_logger(__name__)


class OCRConfigViewSet(viewsets.ModelViewSet):
    """OCR 配置管理"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return OCRConfig.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return OCRConfigListSerializer
        return OCRConfigSerializer
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """获取所有启用的 OCR 配置"""
        configs = OCRConfig.objects.filter(is_active=True)
        serializer = OCRConfigListSerializer(configs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        
        OCRConfig.objects.filter(is_default=True).update(is_default=False)
        
        config.is_default = True
        config.save()
        
        return Response({'message': f'已将 {config.name} 设置为默认配置'})
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """测试 OCR 配置"""
        config = self.get_object()
        
        image = request.FILES.get('image')
        if not image:
            return Response({'error': '请上传测试图片'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from PIL import Image
            img = Image.open(image)
            
            ocr_config = OCRConfigData(
                engine_type=self._get_engine_type(config.provider),
                language=OCRLanguage.CHINESE_ENGLISH,
                use_gpu=config.use_gpu,
                min_confidence=config.min_confidence,
                online_provider=config.provider,
                online_api_key=config.api_key,
                online_base_url=config.base_url,
                online_model=config.model_name,
            )
            
            service = get_ocr_service()
            result = service.recognize(img, config=ocr_config)
            
            return Response({
                'success': result.success,
                'text': result.text,
                'confidence': result.confidence,
                'engine': result.engine.value,
                'error_message': result.error_message
            })
            
        except Exception as e:
            logger.error(f"OCR test failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_engine_type(self, provider: str) -> OCREngineType:
        """根据提供商获取引擎类型"""
        if provider == 'tesseract':
            return OCREngineType.TESSERACT
        elif provider == 'ppocr':
            return OCREngineType.PPOCR
        else:
            return OCREngineType.ONLINE


class OCRTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """OCR 任务查询"""
    permission_classes = [IsAuthenticated]
    serializer_class = OCRTaskSerializer
    
    def get_queryset(self):
        return OCRTask.objects.all()


class OCRRecognizeView(APIView):
    """OCR 识别接口"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        serializer = OCRRecognizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image = serializer.validated_data['image']
        config_id = serializer.validated_data.get('config_id')
        language = serializer.validated_data.get('language', 'chi_sim+eng')
        return_details = serializer.validated_data.get('return_details', False)
        
        try:
            from PIL import Image
            img = Image.open(image)
            
            ocr_config = None
            engine_type = OCREngineType.TESSERACT
            
            if config_id:
                try:
                    config = OCRConfig.objects.get(id=config_id, is_active=True)
                    ocr_config = OCRConfigData(
                        engine_type=self._get_engine_type(config.provider),
                        language=self._get_language(language),
                        use_gpu=config.use_gpu,
                        min_confidence=config.min_confidence,
                        online_provider=config.provider,
                        online_api_key=config.api_key,
                        online_base_url=config.base_url,
                        online_model=config.model_name,
                    )
                    engine_type = ocr_config.engine_type
                except OCRConfig.DoesNotExist:
                    pass
            
            if not ocr_config:
                ocr_config = OCRConfigData(
                    engine_type=OCREngineType.TESSERACT,
                    language=self._get_language(language),
                )
            
            service = get_ocr_service()
            start_time = time.time()
            result = service.recognize(img, engine_type=engine_type, config=ocr_config)
            processing_time = time.time() - start_time
            
            response_data = {
                'success': result.success,
                'text': result.text,
                'confidence': result.confidence,
                'engine': result.engine.value,
                'processing_time': round(processing_time, 3),
            }
            
            if return_details:
                response_data['texts'] = [item.to_dict() for item in result.texts]
            
            if not result.success:
                response_data['error_message'] = result.error_message
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"OCR recognition failed: {e}")
            return Response({
                'success': False,
                'error_message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_engine_type(self, provider: str) -> OCREngineType:
        if provider == 'tesseract':
            return OCREngineType.TESSERACT
        elif provider == 'ppocr':
            return OCREngineType.PPOCR
        else:
            return OCREngineType.ONLINE
    
    def _get_language(self, lang_str: str) -> OCRLanguage:
        lang_map = {
            'chi_sim': OCRLanguage.CHINESE,
            'eng': OCRLanguage.ENGLISH,
            'chi_sim+eng': OCRLanguage.CHINESE_ENGLISH,
            'japan': OCRLanguage.JAPANESE,
            'korean': OCRLanguage.KOREAN,
        }
        return lang_map.get(lang_str, OCRLanguage.CHINESE_ENGLISH)


class OCRRecognizeBase64View(APIView):
    """OCR 识别接口（Base64 图片）"""
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]
    
    def post(self, request):
        image_base64 = request.data.get('image')
        if not image_base64:
            return Response({'error': '请提供 base64 编码的图片'}, status=status.HTTP_400_BAD_REQUEST)
        
        config_id = request.data.get('config_id')
        language = request.data.get('language', 'chi_sim+eng')
        
        try:
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            
            image_data = base64.b64decode(image_base64)
            
            from PIL import Image
            img = Image.open(BytesIO(image_data))
            
            ocr_config = None
            engine_type = OCREngineType.TESSERACT
            
            if config_id:
                try:
                    config = OCRConfig.objects.get(id=config_id, is_active=True)
                    ocr_config = OCRConfigData(
                        engine_type=self._get_engine_type(config.provider),
                        language=self._get_language(language),
                        use_gpu=config.use_gpu,
                        min_confidence=config.min_confidence,
                        online_provider=config.provider,
                        online_api_key=config.api_key,
                        online_base_url=config.base_url,
                        online_model=config.model_name,
                    )
                    engine_type = ocr_config.engine_type
                except OCRConfig.DoesNotExist:
                    pass
            
            if not ocr_config:
                ocr_config = OCRConfigData(
                    engine_type=OCREngineType.TESSERACT,
                    language=self._get_language(language),
                )
            
            service = get_ocr_service()
            result = service.recognize(img, engine_type=engine_type, config=ocr_config)
            
            return Response({
                'success': result.success,
                'text': result.text,
                'confidence': result.confidence,
                'engine': result.engine.value,
                'error_message': result.error_message if not result.success else None
            })
            
        except Exception as e:
            logger.error(f"OCR recognition failed: {e}")
            return Response({
                'success': False,
                'error_message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_engine_type(self, provider: str) -> OCREngineType:
        if provider == 'tesseract':
            return OCREngineType.TESSERACT
        elif provider == 'ppocr':
            return OCREngineType.PPOCR
        else:
            return OCREngineType.ONLINE
    
    def _get_language(self, lang_str: str) -> OCRLanguage:
        lang_map = {
            'chi_sim': OCRLanguage.CHINESE,
            'eng': OCRLanguage.ENGLISH,
            'chi_sim+eng': OCRLanguage.CHINESE_ENGLISH,
        }
        return lang_map.get(lang_str, OCRLanguage.CHINESE_ENGLISH)


@api_view(['GET'])
def ocr_engines(request):
    """获取可用的 OCR 引擎列表"""
    service = get_ocr_service()
    available_engines = service.get_available_engines()
    
    engines = []
    for engine_type in OCREngineType:
        engines.append({
            'type': engine_type.value,
            'name': engine_type.name,
            'available': engine_type in available_engines
        })
    
    return Response({'engines': engines})


@api_view(['GET'])
def ocr_check_installation(request):
    """检查 OCR 引擎安装状态"""
    results = {}
    
    results['tesseract'] = TesseractAdapter.check_installation()
    results['ppocr'] = PPOCRAdapter.check_installation()
    
    return Response(results)


@api_view(['GET'])
def ocr_gpu_status(request):
    """检查 GPU 加速状态"""
    from .gpu_utils import get_gpu_info, check_gpu_requirements
    
    info = get_gpu_info()
    requirements = check_gpu_requirements()
    
    return Response({
        'gpu_info': info,
        'requirements': requirements,
    })


class OCRBatchRecognizeView(APIView):
    """批量 OCR 识别接口"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request):
        from .serializers import OCRBatchRecognizeSerializer
        
        images = request.FILES.getlist('images')
        if not images:
            return Response({'error': '请上传图片文件'}, status=status.HTTP_400_BAD_REQUEST)
        
        config_id = request.data.get('config_id')
        language = request.data.get('language', 'chi_sim+eng')
        
        try:
            from PIL import Image
            
            ocr_config = None
            engine_type = OCREngineType.TESSERACT
            
            if config_id:
                try:
                    config = OCRConfig.objects.get(id=config_id, is_active=True)
                    ocr_config = OCRConfigData(
                        engine_type=self._get_engine_type(config.provider),
                        language=self._get_language(language),
                        use_gpu=config.use_gpu,
                        min_confidence=config.min_confidence,
                        online_provider=config.provider,
                        online_api_key=config.api_key,
                        online_base_url=config.base_url,
                        online_model=config.model_name,
                    )
                    engine_type = ocr_config.engine_type
                except OCRConfig.DoesNotExist:
                    pass
            
            if not ocr_config:
                ocr_config = OCRConfigData(
                    engine_type=OCREngineType.TESSERACT,
                    language=self._get_language(language),
                )
            
            service = get_ocr_service()
            results = []
            all_texts = []
            total_confidence = 0
            success_count = 0
            
            for idx, image_file in enumerate(images):
                try:
                    img = Image.open(image_file)
                    start_time = time.time()
                    result = service.recognize(img, engine_type=engine_type, config=ocr_config)
                    processing_time = time.time() - start_time
                    
                    text = self._clean_text(result.text) if result.success else ''
                    
                    results.append({
                        'index': idx,
                        'filename': image_file.name,
                        'success': result.success,
                        'text': text,
                        'confidence': result.confidence,
                        'processing_time': round(processing_time, 3),
                        'error_message': result.error_message if not result.success else None
                    })
                    
                    if result.success and text:
                        all_texts.append(text)
                        total_confidence += result.confidence
                        success_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process image {idx}: {e}")
                    results.append({
                        'index': idx,
                        'filename': image_file.name,
                        'success': False,
                        'text': '',
                        'error_message': str(e)
                    })
            
            combined_text = self._clean_combined_text('\n\n'.join(all_texts))
            avg_confidence = total_confidence / success_count if success_count > 0 else 0
            
            return Response({
                'success': success_count > 0,
                'total': len(images),
                'processed': success_count,
                'results': results,
                'combined_text': combined_text,
                'confidence': round(avg_confidence, 3),
            })
            
        except Exception as e:
            logger.error(f"Batch OCR recognition failed: {e}")
            return Response({
                'success': False,
                'error_message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_engine_type(self, provider: str) -> OCREngineType:
        if provider == 'tesseract':
            return OCREngineType.TESSERACT
        elif provider == 'ppocr':
            return OCREngineType.PPOCR
        else:
            return OCREngineType.ONLINE
    
    def _get_language(self, lang_str: str) -> OCRLanguage:
        lang_map = {
            'chi_sim': OCRLanguage.CHINESE,
            'eng': OCRLanguage.ENGLISH,
            'chi_sim+eng': OCRLanguage.CHINESE_ENGLISH,
            'japan': OCRLanguage.JAPANESE,
            'korean': OCRLanguage.KOREAN,
        }
        return lang_map.get(lang_str, OCRLanguage.CHINESE_ENGLISH)
    
    def _clean_text(self, text: str) -> str:
        """清理单个 OCR 识别结果"""
        if not text:
            return ''
        
        import re
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        return text
    
    def _clean_combined_text(self, text: str) -> str:
        """清理合并后的文本，确保格式整洁"""
        if not text:
            return ''
        
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        return text
