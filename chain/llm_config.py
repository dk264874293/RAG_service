from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class LLMConfig:
    """LLM 配置数据类"""
    name: str
    description: str
    params: Dict[str, Any]


# 预设配置模板
PRESET_CONFIGS = {
    "conservative": VLLMConfig(
        name="保守型",
        description="低随机性，适合需要准确性的任务",
        params={
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 10,
            "repetition_penalty": 1.1,
            "max_tokens": 512
        }
    ),
    
    "balanced": VLLMConfig(
        name="平衡型",
        description="平衡创意和准确性，适合大多数场景",
        params={
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 50,
            "repetition_penalty": 1.1,
            "frequency_penalty": 0.1,
            "max_tokens": 1024
        }
    ),
    
    "creative": VLLMConfig(
        name="创意型",
        description="高随机性，适合创意写作和头脑风暴",
        params={
            "temperature": 1.2,
            "top_p": 0.95,
            "top_k": 100,
            "repetition_penalty": 1.05,
            "presence_penalty": 0.2,
            "max_tokens": 2048
        }
    ),
    
    "precise": VLLMConfig(
        name="精确型",
        description="极低随机性，适合代码生成和技术文档",
        params={
            "temperature": 0.01,
            "top_p": 0.7,
            "top_k": 5,
            "repetition_penalty": 1.2,
            "frequency_penalty": 0.3,
            "max_tokens": 1024
        }
    ),
    
    "diverse": VLLMConfig(
        name="多样型",
        description="强调内容多样性，减少重复",
        params={
            "temperature": 0.8,
            "top_p": 0.9,
            "top_k": 80,
            "repetition_penalty": 1.3,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.4,
            "max_tokens": 1536
        }
    ),
    
    "beam_search": VLLMConfig(
        name="束搜索型",
        description="使用束搜索，适合需要高质量输出的场景",
        params={
            "temperature": 0.6,
            "use_beam_search": True,
            "best_of": 3,
            "length_penalty": 1.2,
            "early_stopping": True,
            "max_tokens": 1024
        }
    )
}
