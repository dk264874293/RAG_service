# ocr_module/__init__.py
from typing import List, Union, Optional, Dict, Any
import numpy as np
from PIL import Image
import logging
from pathlib import Path

from .config.base_config import ConfigManager
from .core.ocr_factory import OCRFactory
from .utils.cache_manager import CacheManager

class OCRService:
    """
    OCR服务主类，提供工程化的OCR功能
    """
    
    def __init__(self, 
                 config_path: Optional[str] = None,
                 engine: Optional[str] = None,
                 **kwargs):
        """
        初始化OCR服务
        
        Args:
            config_path: 配置文件路径
            engine: 指定OCR引擎，如不指定则使用配置文件中的默认引擎
            **kwargs: 动态配置参数，会覆盖配置文件中的设置
        """
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config
        
        # 更新动态配置
        if kwargs:
            self.config_manager.update_config(**kwargs)
        self.kwargs = kwargs
        self.logger.info(f"OCR服务初始化参数 ---->>>>: {self.config}")
        
        # 选择引擎
        self.engine_name = engine or self.config.default_engine
        self.logger.info(f"Using OCR engine: {self.engine_name}")
        
        # 初始化组件
        self.ocr_engine = None
        self.preprocessor = None
        self.postprocessor = None
        self.cache_manager = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化所有组件"""
        try:
            # 初始化缓存
            if self.config.enable_cache:
                self.cache_manager = CacheManager(
                    ttl=self.config.cache_ttl,
                    max_size=1000
                )
            
            # 初始化OCR引擎
            engine_config = self._get_engine_config()
            self.ocr_engine = OCRFactory.create_engine(
                self.engine_name,
                config = engine_config
            )
            self.ocr_engine.initialize()
            
            self.logger.info("OCR service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize OCR service: {e}")
            raise
    
    def _get_engine_config(self) -> Dict[str, Any]:
        """获取引擎特定配置"""
        config_dict = self.config.dict()
        
        # 添加引擎特定配置
        engine_config_key = f"{self.engine_name}_config"
        if hasattr(self.config, engine_config_key):
            engine_specific = getattr(self.config, engine_config_key)
            config_dict.update(engine_specific)
        
        # 添加所有传入的 kwargs，确保 api_endpoint 等参数被包含
        config_dict.update(self.kwargs)
        return config_dict
    
    def recognize(self, 
                  image_input: Union[str, Path, np.ndarray, Image.Image, bytes],
                  preprocess: bool = None,
                  postprocess: bool = None,
                  return_format: str = None,
                  **kwargs) -> Union[str, Dict, List[Dict]]:
        """
        识别单张图片
        
        Args:
            image_input: 图像输入，支持多种格式
            preprocess: 是否启用预处理，None时使用配置
            postprocess: 是否启用后处理，None时使用配置
            return_format: 返回格式，支持 'text', 'json', 'dict'
            **kwargs: 其他参数传递给OCR引擎
        
        Returns:
            识别结果，格式取决于return_format参数
        """
        # 生成缓存键
        cache_key = None
        if self.cache_manager:
            cache_key = self._generate_cache_key(image_input, kwargs)
            cached = self.cache_manager.get(cache_key)
            if cached is not None:
                self.logger.debug("Cache hit")
                return self._format_result(cached, return_format)
        
        # 读取和预处理图像
        image_array = self._load_image(image_input)
        
        if preprocess or (preprocess is None and self.config.preprocess_enabled):
            if self.preprocessor:
                image_array = self.preprocessor.process(image_array)
        
        # OCR识别
        try:
            raw_results = self.ocr_engine.recognize(image_array, **kwargs)
        except Exception as e:
            self.logger.error(f"OCR recognition failed: {e}")
            raw_results = []
        
        # 后处理
        if postprocess or (postprocess is None and self.config.postprocess_enabled):
            if self.postprocessor:
                raw_results = self.postprocessor.process(raw_results)
        
        # 缓存结果
        if cache_key and self.cache_manager:
            self.cache_manager.set(cache_key, raw_results)
        
        return self._format_result(raw_results, return_format)
    
    def recognize_batch(self, 
                       image_inputs: List[Union[str, Path, np.ndarray, Image.Image, bytes]],
                       preprocess: bool = None,
                       postprocess: bool = None,
                       parallel: bool = None,
                       **kwargs) -> List:
        """
        批量识别图片
        
        Args:
            image_inputs: 图像输入列表
            preprocess: 是否启用预处理
            postprocess: 是否启用后处理
            parallel: 是否并行处理
            **kwargs: 其他参数
        
        Returns:
            识别结果列表
        """
        parallel = parallel if parallel is not None else self.config.enable_parallel
        
        if parallel and len(image_inputs) > 1:
            return self._recognize_parallel(image_inputs, preprocess, postprocess, **kwargs)
        else:
            results = []
            for img_input in image_inputs:
                result = self.recognize(img_input, preprocess, postprocess, **kwargs)
                results.append(result)
            return results
    
    def _recognize_parallel(self, image_inputs, preprocess, postprocess, **kwargs):
        """并行处理"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        results = [None] * len(image_inputs)
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    self.recognize, 
                    img_input, 
                    preprocess, 
                    postprocess, 
                    **kwargs
                ): idx for idx, img_input in enumerate(image_inputs)
            }
            
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    self.logger.error(f"Failed to process image {idx}: {e}")
                    results[idx] = []
        
        return results
    
    def _load_image(self, image_input):
        """加载图像为numpy数组"""
        if isinstance(image_input, (str, Path)):
            import cv2
            return cv2.imread(str(image_input))
        elif isinstance(image_input, Image.Image):
            return np.array(image_input)
        elif isinstance(image_input, bytes):
            import cv2
            nparr = np.frombuffer(image_input, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_input, np.ndarray):
            return image_input
        else:
            raise TypeError(f"Unsupported image type: {type(image_input)}")
    
    def _generate_cache_key(self, image_input, kwargs):
        """生成缓存键"""
        import hashlib
        import json
        
        # 基于图像内容生成哈希
        if isinstance(image_input, (str, Path)):
            path_str = str(image_input)
            stat = Path(path_str).stat()
            key_data = f"{path_str}_{stat.st_mtime}_{stat.st_size}"
        elif isinstance(image_input, (np.ndarray, bytes)):
            if isinstance(image_input, np.ndarray):
                image_bytes = image_input.tobytes()
            else:
                image_bytes = image_input
            key_data = hashlib.md5(image_bytes).hexdigest()
        else:
            key_data = str(image_input)
        
        # 添加配置参数
        params_str = json.dumps(kwargs, sort_keys=True)
        full_key = f"{self.engine_name}_{key_data}_{params_str}"
        
        return hashlib.md5(full_key.encode()).hexdigest()
    
    def _format_result(self, results, return_format):
        """格式化输出结果"""
        if return_format is None:
            return_format = self.config.output_format
        
        if return_format == 'text':
            return "\n".join([r.text for r in results])
        elif return_format == 'json':
            import json
            return json.dumps([r.__dict__ for r in results], ensure_ascii=False)
        elif return_format == 'dict':
            return [r.__dict__ for r in results]
        else:
            return results
    
    def switch_engine(self, engine_name: str):
        """切换OCR引擎"""
        if engine_name not in OCRFactory.get_available_engines():
            raise ValueError(f"Unsupported engine: {engine_name}")
        
        self.engine_name = engine_name
        self.logger.info(f"Switching to OCR engine: {engine_name}")
        
        # 重新初始化引擎
        engine_config = self._get_engine_config()
        self.ocr_engine = OCRFactory.create_engine(engine_name, engine_config)
        self.ocr_engine.initialize()
    
    def get_engine_info(self) -> Dict[str, Any]:
        """获取当前引擎信息"""
        if self.ocr_engine:
            return self.ocr_engine.get_engine_info()
        return {}