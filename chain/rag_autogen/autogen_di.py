'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-18 14:42:53
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-18 14:56:25
FilePath: /RAG_service/chain/rag_autogen/autogen_magentic.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import asyncio
import os
from dotenv import load_dotenv
from typing import Sequence
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat, MagenticOneGroupChat, DiGraphBuilder,GraphFlow
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

    writer = AssistantAgent(
        'writer',
        model_client=model_client,
        system_message="起草一段关于气候变化的短文",
    )

    reviewer = AssistantAgent(
        'reviewer',
        model_client=model_client,
        system_message="审核 writer 起草的文章，确保符合语法和逻辑",
    )

    builder = DiGraphBuilder()

    builder.add_node(writer)
    builder.add_node(reviewer)
    builder.add_edge(writer, reviewer)

    graph = builder.build()

    flow = GraphFlow([writer, reviewer], graph)

    await Console(flow.run_stream())

asyncio.run(main())