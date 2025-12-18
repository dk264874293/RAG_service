'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-18 11:19:24
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-18 11:37:36
FilePath: /RAG_service/chain/rag_autogen/autogen_roundRobin.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE

'''
import asyncio
import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_core import CancellationToken
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

model_client = OpenAIChatCompletionClient(
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model_info=model_info_qwen_plus,
    parallel_tool_calls = False
)

async def main() -> None:
    writer = AssistantAgent(
        "Writer",model_client=model_client,
        system_message="你是一个专业的文章稿件写手",
        model_client_stream = True
    )

    reviewer = AssistantAgent(
        "Reviewer",model_client=model_client,
        system_message="你是一个专业的文章审稿人",
        model_client_stream = True
    )

    user_proxy = UserProxyAgent("user_proxy")

    inner_termination = MaxMessageTermination(max_messages = 4)

    team = RoundRobinGroupChat(
        [writer, reviewer],
        termination_condition = inner_termination,
    )

    await Console(team.run_stream(task="写一篇易于理解的AI科普文章，主要针对小学读者让其可以理解AI的基本原理，字数请在1000字以内"))


    # agent1 = AssistantAgent("Assistant1", model_client=model_client)
    # agent2 = AssistantAgent("Assistant2", model_client=model_client)
    # termination = TextMentionTermination("TERMINATE")
    # team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)
    # await Console(team.run_stream(task="Tell me some jokes."))

    # async def getWeather(city: str) -> str:
    #     return f"今天{city}是晴天，气温20摄氏度."

    # assistant = AssistantAgent(
    #     'Assistant',
    #     model_client=model_client,
    #     tools=[getWeather],
    # )

    # termination = TextMentionTermination("TERMINATE") 

    # team = RoundRobinGroupChat(
    #     [assistant],
    #     termination_condition=termination,
    # )

    # await Console(team.run_stream(
    #     task = "今天上海天气怎么样"
    # ))

asyncio.run(main())