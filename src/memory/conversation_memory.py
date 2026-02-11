"""
对话历史管理
支持多轮对话的上下文保持
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import deque
import json

from .base import BaseMemory, MemoryType

logger = logging.getLogger(__name__)


class ConversationMemory(BaseMemory):
    """
    对话历史管理器

    功能:
    1. 存储对话历史
    2. 限制上下文窗口大小
    3. 总结压缩旧对话
    4. 按会话隔离
    """

    def __init__(
        self,
        max_messages: int = 100,
        max_tokens: int = 4000,
        enable_summarization: bool = True,
        summarization_threshold: int = 20,
    ):
        """
        初始化对话记忆

        Args:
            max_messages: 最多保留消息数
            max_tokens: 最大token数（用于限制上下文窗口）
            enable_summarization: 是否启用自动总结
            summarization_threshold: 超过此消息数后触发总结
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.enable_summarization = enable_summarization
        self.summarization_threshold = summarization_threshold

        # 会话存储: conversation_id -> messages
        self.conversations: Dict[str, deque] = {}

    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        添加对话消息

        Args:
            content: 消息内容
            metadata: 元数据（role, conversation_id, timestamp等）

        Returns:
            消息ID
        """
        metadata = metadata or {}
        conversation_id = metadata.get("conversation_id", "default")

        # 创建会话
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = deque(maxlen=self.max_messages)

        # 生成消息ID
        message_id = metadata.get("message_id") or f"{conversation_id}_{len(self.conversations[conversation_id])}_{datetime.now().timestamp()}"

        # 添加消息
        message = {
            "id": message_id,
            "content": content,
            "role": metadata.get("role", "user"),
            "timestamp": metadata.get("timestamp", datetime.utcnow().isoformat()),
            "metadata": metadata,
        }

        self.conversations[conversation_id].append(message)

        # 检查是否需要总结
        if self.enable_summarization and len(self.conversations[conversation_id]) >= self.summarization_threshold:
            await self._summarize_conversation(conversation_id)

        # 检查token限制
        await self._enforce_token_limit(conversation_id)

        return message_id

    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """搜索对话历史"""
        conversation_id = filters.get("conversation_id") if filters else None

        if not conversation_id or conversation_id not in self.conversations:
            return []

        results = []
        query_lower = query.lower()

        # 在历史消息中搜索
        for message in reversed(self.conversations[conversation_id]):
            if query_lower in message["content"].lower():
                results.append(message)
                if len(results) >= k:
                    break

        return results

    async def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取消息"""
        for conversation_id, messages in self.conversations.items():
            for msg in messages:
                if msg["id"] == memory_id:
                    return msg
        return None

    async def update(self, memory_id: str, content: str, metadata: Optional[Dict] = None]) -> bool:
        """更新消息（不支持）"""
        logger.warning(f"Conversation messages are immutable")
        return False

    async def delete(self, memory_id: str) -> bool:
        """删除消息"""
        for conversation_id, messages in self.conversations.items():
            for i, msg in enumerate(messages):
                if msg["id"] == memory_id:
                    del messages[i]
                    return True
        return False

    async def cleanup(self, older_than: datetime) -> int:
        """清理过期会话"""
        count = 0
        expired_conversations = []

        for conversation_id, messages in self.conversations.items():
            # 检查最后一条消息的时间
            if messages:
                last_msg = messages[-1]
                last_time = datetime.fromisoformat(last_msg["timestamp"])

                if last_time < older_than:
                    expired_conversations.append(conversation_id)
                    count += len(messages)

        # 删除过期会话
        for conv_id in expired_conversations:
            del self.conversations[conv_id]

        logger.info(f"Cleaned up {len(expired_conversations)} conversations, {count} messages")
        return count

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        if conversation_id not in self.conversations:
            return []

        messages = list(self.conversations[conversation_id])
        if limit:
            messages = messages[-limit:]

        return messages

    async def _summarize_conversation(self, conversation_id: str) -> None:
        """
        总结对话历史

        当消息数量达到阈值时，总结旧消息为新摘要
        """
        messages = self.conversations[conversation_id]

        if len(messages) < self.summarization_threshold:
            return

        # 保留最近的消息
        recent_messages = list(messages)[-10:]

        # 总结旧消息
        old_messages = list(messages)[:-10]
        summary = await self._generate_summary(old_messages)

        # 创建摘要消息
        summary_message = {
            "id": f"{conversation_id}_summary_{datetime.now().timestamp()}",
            "content": summary,
            "role": "system",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "type": "summary",
                "summarized_count": len(old_messages),
            },
        }

        # 清空旧消息，添加摘要和最近消息
        self.conversations[conversation_id].clear()
        self.conversations[conversation_id].append(summary_message)
        self.conversations[conversation_id].extend(recent_messages)

        logger.info(f"Summarized {len(old_messages)} messages in conversation {conversation_id}")

    async def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        try:
            from src.service.llm_service import LLMService

            # 简化的提示词
            prompt = "请总结以下对话的主要内容：\n\n"
            for msg in messages[:20]:  # 只取前20条避免token过多
                prompt += f"{msg['role']}: {msg['content']}\n"

            prompt += "\n\n请用简洁的语言总结这段对话。"

            llm_service = LLMService({"provider": "dashscope", "model": "qwen-plus"})
            summary = await llm_service.generate(prompt)

            return summary.strip()

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return "对话历史摘要生成失败"

    async def _enforce_token_limit(self, conversation_id: str) -> None:
        """
        强制执行token限制
        """
        import tiktoken

        messages = self.conversations[conversation_id]

        # 粗略估算token数（中文字符*2）
        total_chars = sum(len(msg["content"]) for msg in messages)
        estimated_tokens = total_chars * 2

        while estimated_tokens > self.max_tokens and len(messages) > 1:
            # 移除最旧的消息
            removed = messages.popleft()
            estimated_tokens -= len(removed["content"]) * 2
            logger.debug(f"Removed message to enforce token limit: {removed['id']}")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_messages = sum(len(msgs) for msgs in self.conversations.values())
        return {
            "total_conversations": len(self.conversations),
            "total_messages": total_messages,
            "enable_summarization": self.enable_summarization,
        }
