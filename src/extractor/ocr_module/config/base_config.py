'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-25 13:36:21
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-25 13:36:26
FilePath: /RAG_service/src/extractor/ocr_module/config/base_config.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
# config/base_config.py
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import yaml
import os

class OCRLang(str, Enum):
    CHINESE = "ch"
    ENGLISH = "en"
    JAPANESE = "jp"
    KOREAN = "ko"

@dataclass
class PreprocessStep:
    name: str
    enabled: bool
    params: Dict[str, Any] = None

class OCRConfig(BaseModel):
    # 引擎配置
    default_engine: str = "paddle-api"
    use_gpu: bool = False
    gpu_id: int = 0
    languages: List[OCRLang] = [OCRLang.CHINESE, OCRLang.ENGLISH]
    batch_size: int = 8
    
    # 路径配置
    model_cache_dir: str = "./models"
    temp_dir: str = "./temp"
    
    # 性能配置
    enable_cache: bool = True
    cache_ttl: int = 3600
    enable_parallel: bool = True
    max_workers: int = 4
    
    # 预处理配置
    preprocess_enabled: bool = True
    preprocess_steps: List[PreprocessStep] = None
    
    # 后处理配置
    postprocess_enabled: bool = True
    confidence_threshold: float = 0.6
    
    # 输出配置
    output_format: str = "json"  # json, text, markdown
    include_position: bool = True
    include_confidence: bool = True
    
    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True

class ConfigManager:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/ocr_config.yaml"
        self.config = self.load_config()
        
    def load_config(self) -> OCRConfig:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # 处理环境变量
        config_data = self._resolve_env_vars(config_data)
        return OCRConfig(**config_data)
    
    def _resolve_env_vars(self, config: dict) -> dict:
        import re
        
        def replace_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, match.group(0))
        
        config_str = yaml.dump(config)
        config_str = re.sub(r'\$\{(\w+)\}', replace_var, config_str)
        return yaml.safe_load(config_str)
    
    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)