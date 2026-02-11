"""
Memory管理模块 - 基础接口
支持对话历史、长期记忆、上下文窗口管理
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    """Memory类型"""
    CONVERSATION = "conversation"  # 对话历史
    SHORT_TERM = "short_term"      # 短期记忆
    LONG_TERM = "long_term"        # 长期记忆
    EPISODIC = "episodic"          # 情景记忆
    SEMANTIC = "semantic"          # 语义记忆


class BaseMemory(ABC):
    """Memory基础接口"""

    @abstractmethod
    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加记忆

        Args:
            content: 记忆内容
            metadata: 元数据

        Returns:
            记忆ID
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆

        Args:
            query: 查询内容
            k: 返回结果数量
            filters: 过滤条件

        Returns:
            记忆列表
        """
        pass

    @abstractmethod
    async def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        获取记忆

        Args:
            memory_id: 记忆ID

        Returns:
            记忆内容
        """
        pass

    @abstractmethod
    async def update(self, memory_id: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        更新记忆

        Args:
            memory_id: 记忆ID
            content: 新内容
            metadata: 新元数据

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """
        删除记忆

        Args:
            memory_id: 记忆ID

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def cleanup(self, older_than: datetime) -> int:
        """
        清理过期记忆

        Args:
            older_than: 清理早于此时间的记忆

        Returns:
            删除的记忆数量
        """
        pass
