'''Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-23 17:04:56
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-24 09:58:29
FilePath: /RAG_service/chain/memory/summary_mem.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from langchain_community.chat_models import ChatTongyi
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages.utils import count_tokens_approximately
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
import os

load_dotenv()

model = ChatTongyi(
    model_name="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.5,
)

def get_weather(city:str) -> str:
    """Get weather for a given city。"""
    return f"It's always sunny in {city}"

tools = [get_weather]

checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    tools=tools,
    middleware=[
         SummarizationMiddleware(
            model=model,
            token_counter=count_tokens_approximately,
            trigger=("tokens", 368),        # 改为元组格式
            keep=("tokens", 128),           # 改为元组格式
            output_messages_key="messages",
        )
    ],
    checkpointer=checkpointer,
)

config = {
    "configurable": {
        "thread_id":"1"
    }
}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "北京今天天气怎么样？"}]},
    config=config,
)

print(response)