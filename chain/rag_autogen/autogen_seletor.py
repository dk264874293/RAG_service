'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-18 11:41:48
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-18 12:37:04
FilePath: /RAG_service/chain/rag_autogen/autogen_seletor.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import asyncio
import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
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
    async def lookup_hotel(location:str) -> str:
        return f"在{location}有三家酒店分别为'酒店A','酒店B','酒店C'"
    
    async def lookup_flight(origin:  str, destination: str) -> str:
        return f"从{origin}到{destination}有'航班A','航班B','航班C'"

    async def book_trip() -> str:
        return "你的旅行已经预定好了"
    
    travel_advisor = AssistantAgent(
        "Travel_Advisor",
        model_client,
        tools=[book_trip],
        description="帮助制定旅行计划。",
    )
    hotel_agent = AssistantAgent(
        "Hotel_Agent",
        model_client,
        tools=[lookup_hotel],
        description="帮助预约酒店",
    )
    flight_agent = AssistantAgent(
        "Flight_Agent",
        model_client,
        tools=[lookup_flight],
        description="帮助预约飞机航班",
    )
    termination = TextMentionTermination("TERMINATE")

    team = SelectorGroupChat(
        [travel_advisor, hotel_agent, flight_agent],
        model_client=model_client,
        termination_condition=termination,
    )
    await Console(team.run_stream(task="制定一个到北京游玩3天的计划"))

asyncio.run(main())