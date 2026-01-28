'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-25 13:37:44
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-26 07:33:07
FilePath: /RAG_service/src/extractor/ocr_module/core/base_ocr.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# core/base_ocr.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Optional
from PIL import Image
import numpy as np
from dataclasses import dataclass

@dataclass
class OCRResult:
    text: str
    confidence: float
    label: str
    bbox: List[List[int]]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    page_num: int = 1
    block_num: int = 0
    line_num: int = 0
    
@dataclass
class PageResult:
    page_num: int
    width: int
    height: int
    results: List[OCRResult]
    layout_info: Optional[Dict] = None

class BaseOCR(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initialized = False
        
    @abstractmethod
    def initialize(self):
        """初始化OCR引擎"""
        pass
    
    @abstractmethod
    def recognize(self, 
                  image: Union[str, np.ndarray, Image.Image, bytes],
                  **kwargs) -> List[OCRResult]:
        """识别单张图片"""
        pass
    
    @abstractmethod
    def recognize_batch(self, 
                       images: List[Union[str, np.ndarray, Image.Image, bytes]],
                       **kwargs) -> List[List[OCRResult]]:
        """批量识别"""
        pass
    
    @abstractmethod
    def get_engine_info(self) -> Dict[str, Any]:
        """获取引擎信息"""
        pass
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """默认预处理"""
        # 可由子类重写
        return image
    
    def postprocess(self, results: List[OCRResult]) -> List[OCRResult]:
        """默认后处理"""
        # 过滤低置信度结果
        if self.config.get('confidence_threshold', 0) > 0:
            results = [
                r for r in results 
                if r.confidence >= self.config['confidence_threshold']
            ]
        return results