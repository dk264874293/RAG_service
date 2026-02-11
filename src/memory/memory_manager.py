"""
Memory管理器
统一管理多种类型的Memory
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base import BaseMemory, MemoryType
from .conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Memory管理器

    功能：
    1. 统一管理多种Memory类型
    2. 自动路由到合适的Memory
    3. 提供简单的API接口
    """

    def __init__(self, config: Any):
        """
        初始化Memory管理器

        Args:
            config: 配置对象
        """
        self.config = config

        # 初始化各种Memory
        self.memories: Dict[MemoryType, BaseMemory] = {}

        # 对话记忆
        if config.enable_conversation_memory:
            self.conversation_memory = ConversationMemory(
                max_messages=config.get("conversation_max_messages", 100),
                max_tokens=config.get("conversation_max_tokens", 4000),
                enable_summarization=config.get("enable_summarization", True),
            )
            self.memories[MemoryType.CONVERSATION] = self.conversation_memory

        # TODO: 实现其他Memory类型
        # - ShortTermMemory: Redis临时存储
        # - LongTermMemory: 向量数据库长期存储
        # - EpisodicMemory: 基于场景的记忆

    async def add_conversation_message(
        self,
        content: str,
        role: str,
        conversation_id: str = "default",
        user_id: Optional[str] = None,
    ) -> str:
        """
        添加对话消息

        Args:
            content: 消息内容
            role: 角色 (user/assistant/system)
            conversation_id: 会话ID
            user_id: 用户ID

        Returns:
            消息ID
        """
        if MemoryType.CONVERSATION not in self.memories:
            logger.warning("Conversation memory not enabled")
            return ""

        metadata = {
            "role": role,
            "conversation_id": conversation_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.conversation_memory.add(content, metadata)

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> list:
        """获取对话历史"""
        if MemoryType.CONVERSATION not in self.memories:
            return []

        return await self.conversation_memory.get_conversation_history(
            conversation_id,
            limit=limit,
        )

    async def search_conversations(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """搜索对话历史"""
        if MemoryType.CONVERSATION not in self.memories:
            return []

        filters = {}
        if conversation_id:
            filters["conversation_id"] = conversation_id

        return await self.conversation_memory.search(query, k, filters)

    async def cleanup_old_memories(
        self,
        days: int = 30,
    ) -> Dict[str, int]:
        """
        清理过期记忆

        Args:
            days: 清理N天前的记忆

        Returns:
            各类型Memory清理的数量
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        results = {}

        for memory_type, memory in self.memories.items():
            count = await memory.cleanup(cutoff_time)
            results[memory_type.value] = count

        logger.info(f"Cleaned up old memories: {results}")
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "available_memory_types": list(self.memories.keys()),
        }

        for memory_type, memory in self.memories.items():
            stats[memory_type.value] = memory.get_stats() if hasattr(memory, 'get_stats') else {}

        return stats
