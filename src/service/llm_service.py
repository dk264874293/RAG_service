"""
LLM服务 - 提供统一的LLM调用接口
支持OpenAI和DashScope (通义千问)
"""

import logging
from typing import Optional, Dict, Any
from langchain_community.llms import Tongyi
from langchain_openai import OpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM服务封装

    支持的提供商:
    - dashscope: 阿里云通义千问
    - openai: OpenAI
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化LLM服务

        Args:
            config: 配置字典
                - provider: 提供商名称 ("dashscope" | "openai")
                - model: 模型名称
                - temperature: 温度参数
                - api_key: API密钥 (可选，优先从环境变量读取)
                - base_url: API基础URL (可选)
        """
        self.provider = config.get("provider", "dashscope")
        self.model = config.get("model", "qwen-plus")
        self.temperature = config.get("temperature", 0.7)

        if self.provider == "dashscope":
            self._init_dashscope(config)
        elif self.provider == "openai":
            self._init_openai(config)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _init_dashscope(self, config: Dict[str, Any]):
        """初始化DashScope (通义千问)"""
        try:
            from config import settings

            api_key = config.get("api_key") or settings.dashscope_api_key

            self.llm = Tongyi(
                model_name=self.model,
                dashscope_api_key=api_key,
                temperature=self.temperature,
            )

            logger.info(f"Initialized DashScope LLM: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize DashScope LLM: {e}")
            raise

    def _init_openai(self, config: Dict[str, Any]):
        """初始化OpenAI"""
        try:
            from config import settings

            api_key = config.get("api_key") or settings.openai_api_key
            base_url = config.get("base_url") or settings.openai_api_base

            self.llm = OpenAI(
                model=self.model,
                openai_api_key=api_key,
                base_url=base_url,
                temperature=self.temperature,
            )

            logger.info(f"Initialized OpenAI LLM: {self.model}")

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI LLM: {e}")
            raise

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        生成文本

        Args:
            prompt: 输入提示词
            **kwargs: 额外参数 (如 max_tokens, top_p等)

        Returns:
            生成的文本
        """
        try:
            # LangChain的LLM默认是同步的，我们需要在异步上下文中调用
            # 使用简单的方式直接调用
            result = self.llm.invoke(prompt, **kwargs)
            return str(result)

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    async def generate_stream(self, prompt: str, **kwargs):
        """
        流式生成文本

        Args:
            prompt: 输入提示词
            **kwargs: 额外参数

        Yields:
            生成的文本片段
        """
        try:
            for chunk in self.llm.stream(prompt, **kwargs):
                yield str(chunk)

        except Exception as e:
            logger.error(f"LLM stream generation failed: {e}")
            raise

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
        }


class LLMServiceBuilder:
    """LLM服务构建器 - 简化创建流程"""

    @staticmethod
    def build_dashscope(
        model: str = "qwen-plus",
        temperature: float = 0.7,
        api_key: Optional[str] = None,
    ) -> LLMService:
        """
        构建DashScope LLM服务

        Args:
            model: 模型名称 (qwen-turbo, qwen-plus, qwen-max)
            temperature: 温度参数
            api_key: API密钥 (可选)

        Returns:
            LLMService实例
        """
        config = {
            "provider": "dashscope",
            "model": model,
            "temperature": temperature,
        }
        if api_key:
            config["api_key"] = api_key

        return LLMService(config)

    @staticmethod
    def build_openai(
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> LLMService:
        """
        构建OpenAI LLM服务

        Args:
            model: 模型名称
            temperature: 温度参数
            api_key: API密钥 (可选)
            base_url: API基础URL (可选)

        Returns:
            LLMService实例
        """
        config = {
            "provider": "openai",
            "model": model,
            "temperature": temperature,
        }
        if api_key:
            config["api_key"] = api_key
        if base_url:
            config["base_url"] = base_url

        return LLMService(config)
