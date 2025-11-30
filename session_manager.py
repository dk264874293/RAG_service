'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-11-30 10:34:45
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-11-30 12:11:26
FilePath: /RAG_service/session_manager.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from typing import Dict, List, Optional
import time
from collections import defaultdict
import  json
from datetime import datetime

class SessionManager:
    def __init__(self, max_history: int = 5):
        # 添加正确的类型注解
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history = max_history
        self.last_activity_time: Dict[str, float] = {}
    
    # 确保_update_activity方法在正确位置
    def _update_activity(self, session_id: str):
        """更新会话的最后活动时间"""
        self.last_activity_time[session_id] = time.time()

    def get_history(self, session_id:str) -> List[Dict]:
        """获取会话历史记录"""
        self._update_activity(session_id)
        return self.sessions[session_id]

    def add_message(self,session_id: str, user_message: str, bot_reply: str):
        """添加消息到会话历史记录"""
        self._update_activity(session_id)
        self.sessions[session_id].append({
            "user_message": user_message,
            "bot_reply": bot_reply,
            "timestamp": datetime.now().isoformat(),
            "unix_timestamp": time.time()
        })
        # 修复变量名错误
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]

    def clear_history(self, session_id: str):
        """清除会话历史记录"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.last_activity_time:
            del self.last_activity_time[session_id]

    def get_session_stats(self) -> Dict:
        """获取所有会话的统计信息"""
        # 修复拼写错误
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len([s for s, t in self.last_activity_time.items() if time.time() - t < 3000]),
            "total_messages": sum(len(history) for history in self.sessions.values())
        }

    def clearup_inactive_sessions(self, timeout_hours: int = 20):
        """清理不活跃的会话"""
        current_time = time.time()
        timeout_seconds = timeout_hours * 3600

        # 修复变量名不匹配问题
        inactive_sessions = [
            session_id for session_id, last_time in self.last_activity_time.items()
            if current_time - last_time > timeout_seconds
        ]
        
        for session_id in inactive_sessions:
            self.clear_history(session_id)

        return len(inactive_sessions)