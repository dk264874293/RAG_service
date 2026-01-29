'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-25 13:45:32
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-25 16:20:31
FilePath: /RAG_service/src/extractor/ocr_module/core/ocr_factory.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# core/ocr_factory.py
from .base_ocr import BaseOCR
from .paddle_ocr import PaddleOCRWrapper
# from .easy_ocr import EasyOCRWrapper
# from .tesseract_ocr import TesseractOCRWrapper
from typing import Dict, Type, Any, List

class OCRFactory:
    _engines: Dict[str, Type[BaseOCR]] = {
        'paddle': PaddleOCRWrapper,
        # 'easyocr': EasyOCRWrapper,
        # 'tesseract': TesseractOCRWrapper
    }
    
    @classmethod
    def register_engine(cls, name: str, engine_class: Type[BaseOCR]):
        """注册新的OCR引擎"""
        cls._engines[name] = engine_class
    
    @classmethod
    def create_engine(cls, 
                     engine_name: str,
                     config: Dict[str, Any]) -> BaseOCR:
        """创建OCR引擎实例"""
        if engine_name not in cls._engines:
            raise ValueError(f"Unsupported OCR engine: {engine_name}")
        
        engine_class = cls._engines[engine_name]
        return engine_class(config)
    
    @classmethod
    def get_available_engines(cls) -> List[str]:
        """获取可用的OCR引擎列表"""
        return list(cls._engines.keys())