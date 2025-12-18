'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-18 14:42:53
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-18 14:46:53
FilePath: /RAG_service/chain/rag_autogen/autogen_magentic.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import asyncio
import os
from dotenv import load_dotenv
from typing import Sequence
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat, MagenticOneGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import HandoffMessage
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage

load_dotenv()

model_info_qwen_plus = {
    "model_name": "qwen-plus", 
    "family": "qwen",
    "context_length": 32000,
    "vision": False,
    "function_calling": True,
    "json_output": True,
    "structured_output": True
}

model_client = OpenAIChatCompletionClient(
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model_info=model_info_qwen_plus,
    parallel_tool_calls = False
)

async def main():
    assistant = AssistantAgent(
        "Assistant",
        model_client=model_client,
    )
    team = MagenticOneGroupChat(
        [assistant],
        model_client=model_client,
    )
    await Console(team.run_stream(
        task="给费马大定理一个不同的证明"
    ))
    
asyncio.run(main())