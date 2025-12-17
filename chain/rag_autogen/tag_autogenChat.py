'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-16 13:33:41
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-17 15:26:17
FilePath: /RAG_service/chain/rag_autogen/tag_autogenChat.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEfrom
'''
import os
import logging
import asyncio
from autogen_core import EVENT_LOGGER_NAME

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import UserMessage
from autogen_agentchat.messages import TextMessage
from dotenv import load_dotenv
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
        model_info=model_info_qwen_plus
    )

text_message = TextMessage(content="Hello, world!", source="User")

import asyncio

# 导入核心组件：AssistantAgent 是具备语言模型和工具调用能力的智能体
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent

# TaskResult 表示任务执行的结果对象
from autogen_agentchat.base import TaskResult

# 导入终止条件模块
# - ExternalTermination: 外部控制的终止（如手动停止）
# - TextMentionTermination: 当某条消息中包含特定文本时自动终止
from autogen_agentchat.conditions import ExternalTermination, TextMentionTermination

# RoundRobinGroupChat：轮询式小组讨论团队，多个 agent 按顺序轮流发言
from autogen_agentchat.teams import RoundRobinGroupChat

# Console：用于在终端流式输出聊天内容（可选，用于可视化）
from autogen_agentchat.ui import Console

# CancellationToken：允许外部取消异步任务（例如用户中途取消）
from autogen_core import CancellationToken

# fetch_mcp_server = StdioServerParams(command="uvx", args=["mcp-server-fetch"])

model_client = OpenAIChatCompletionClient(
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model_info=model_info_qwen_plus
)

async def main():
    # 初始化两个智能体进行对话
    assistant1 = AssistantAgent("assistant1", model_client=model_client, system_message="你是一个诗人，请创作一首关于海洋的四行诗。")
    assistant2 = AssistantAgent("assistant2", model_client=model_client, system_message="你是一个评论家，请评估这首诗并提供反馈。当你满意时回复'APPROVE'。")
    
    # 设置终止条件
    termination = TextMentionTermination("APPROVE")
    
    # 创建团队
    team = RoundRobinGroupChat([assistant1, assistant2], termination_condition=termination, max_turns=5)
    
    try:
        # 运行任务
        result = await team.run(task="写一首关于海洋的四行诗并评估")
        print("结果:", result)
    finally:
        # 确保关闭模型客户端
        await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())

# # 创建“主创”智能体（负责生成初始内容）
# primary_agent = AssistantAgent(
#     name="primary",
#     model_client = model_client,
#     system_message="你是一个智能助手"
# )
# # 创建“评论家”智能体（负责审查和反馈）
# critic_agent = AssistantAgent(
#     name="critic",
#     model_client = model_client,
#     system_message="你是一个智能助手，你的任务是提供建设性的反馈。当你收到的反馈被 addressed 时，你应该回复 'APPROVE'。",
# )

# # 定义一个终止条件：当任意消息中出现 "APPROVE" 字样时，结束整个流程
# text_termination = TextMentionTermination("APPROVE")

# team = RoundRobinGroupChat(
#     [primary_agent, critic_agent],         # 团队成员列表
#     termination_condition=text_termination        # 终止条件：检测到 APPROVE 就停
# )
# async def main():
#     result = await team.run(task="写一首关于秋天的诗")
#     print(result)

# if __name__ == "__main__":
#     asyncio.run(main())

# async def main():
#     async with McpWorkbench(fetch_mcp_server) as workbench:
#         model_client = OpenAIChatCompletionClient(
#             model="qwen-plus",
#             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
#             api_key=os.getenv("DASHSCOPE_API_KEY"),
#             model_info=model_info_qwen_plus
#         )
#         fetch_agent = AssistantAgent(
#             name="fetcher",
#             model_client=model_client,
#             workbench=workbench,
#             reflect_on_tool_use = True
#         )

#         result = await fetch_agent.run(task="Summarize the content of https://en.wikipedia.org/wiki/Seattle")
#         print(result)

# if __name__ == "__main__":
#     asyncio.run(main())
# async def web_search(query:str) -> str:
#     """Find information on the web"""
#     return "AutoGen is a programming framework for building multi-agent applications."

# agent = AssistantAgent(
#     name="assistant",
#     model_client=model_client,
#     tools=[web_search],
#     system_message="Use tools to solve tasks"
# )

# async def test():
#     result = await agent.run(task="find information on AutoGen")
#     print(result)

# async def assistant_run_stream() -> None:
#     await Console(
#         agent.run_stream
#     )

# if __name__ == "__main__":
#     asyncio.run(test())

# from io import BytesIO
# import requests
# from autogen_agentchat.messages import MultiModalMessage
# from autogen_core import Image as AGImage
# from PIL import Image

# pil_image = Image.open(BytesIO(requests.get("https://picsum.photos/300/200").content))
# img = AGImage(pil_image)

# multi_modal_message = MultiModalMessage(
#     content=["Can you describe the content of this image?", img],
#     source="User"
# )


# async def main():
#     print('multi_modal_message',multi_modal_message)

# if __name__ == "__main__":
#     asyncio.run(main())