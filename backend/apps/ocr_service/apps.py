# -*- coding: utf-8 -*-
import os
from django.apps import AppConfig


class OcrServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ocr_service'
    verbose_name = 'OCR 服务'
    
    def ready(self):
        """应用启动时预热 OCR 模型"""
        import threading
        
        if os.environ.get('RUN_MAIN') == 'true':
            return
        
        if getattr(self, '_warmup_started', False):
            return
        
        self._warmup_started = True
        
        def warmup_ocr_models():
            """在后台线程中预热 OCR 模型"""
            # PaddlePaddle 环境变量配置（必须在 import paddle 之前设置）
            os.environ['FLAGS_use_mkldnn'] = '0'
            os.environ['FLAGS_cinn_new_group_scheduler'] = '0'
            os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
            os.environ['FLAGS_enable_pir_api'] = '0'
            os.environ['FLAGS_check_cuda_version'] = '0'
            os.environ['FLAGS_skip_allocator_mem_check'] = '1'
            # 解决 kernel not registered 问题（reshape, full_int_array 等）
            os.environ['FLAGS_new_executor_serial_run'] = '1'
            os.environ['FLAGS_enable_new_ir'] = '0'
            os.environ['FLAGS_enable_new_ir_in_executor'] = '0'
            os.environ['FLAGS_use_cinn'] = '0'
            os.environ['FLAGS_enable_new_executor'] = '0'
            os.environ['FLAGS_enable_pir'] = '0'
            
            from backend.log_config import get_logger
            logger = get_logger(__name__)
            
            try:
                from django.conf import settings
                
                warmup_enabled = getattr(settings, 'OCR_WARMUP_ENABLED', True)
                if not warmup_enabled:
                    logger.info("OCR 模型预热已禁用")
                    return
                
                try:
                    import paddleocr
                except ImportError:
                    logger.info("PaddleOCR 未安装，跳过 PP-OCRv5 模型预热")
                    return
                
                from .models import OCRConfig
                
                active_ppocr_configs = OCRConfig.objects.filter(
                    provider='ppocr',
                    is_active=True
                )
                
                if active_ppocr_configs.exists():
                    logger.info("开始预热 PP-OCRv5 模型...")
                    
                    try:
                        from .adapters.ppocr import PPOCRAdapter
                        
                        adapter = PPOCRAdapter()
                        adapter.initialize()
                        logger.info("PP-OCRv5 模型预热完成")
                    except ImportError as e:
                        logger.warning(f"PP-OCRv5 依赖未安装: {e}")
                    except Exception as e:
                        logger.warning(f"PP-OCRv5 模型预热失败: {e}")
                else:
                    logger.info("未找到激活的 PP-OCRv5 配置，跳过预热")
                    
            except Exception as e:
                logger.warning(f"OCR 模型预热过程出错: {e}")
        
        warmup_thread = threading.Thread(target=warmup_ocr_models, daemon=True)
        warmup_thread.start()
