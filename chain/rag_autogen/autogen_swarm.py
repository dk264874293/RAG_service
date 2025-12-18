'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-18 07:21:50
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-18 08:09:29
FilePath: /RAG_service/chain/rag_autogen/autogen_dom.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import asyncio
import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import HandoffTermination, MaxMessageTermination
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import HandoffMessage

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


async def main():
    model_client = OpenAIChatCompletionClient(
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        model_info=model_info_qwen_plus,
        parallel_tool_calls = False
    )

    agent = AssistantAgent(
        "Alice",
        model_client = model_client,
        handoffs=['user'],
        system_message="你是爱丽丝，你只回答关于你自己的问题，如果需要的话向用户寻求帮助。"
    )

    termination = HandoffTermination(target="user") | MaxMessageTermination(3)

    team = Swarm([agent], termination_condition=termination)

    await Console(team.run_stream(
        task="鲍勃的生日是哪一天？"
    ))

    await Console(
        team.run_stream(
            task=HandoffMessage(source="user", target="Alice", content="Bob's birthday is on 1st January.")
        )
    )
asyncio.run(main())