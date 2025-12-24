'''Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-23 15:31:09
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-23 16:55:54
FilePath: /RAG_service/chain/memory/short_mem.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
import json
from langchain.agents import create_agent
from langchain_community.chat_models import ChatTongyi
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv

load_dotenv()

checkpointer = InMemorySaver()

def get_weather(city:str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

model = ChatTongyi(
    model_name="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.5,
)

agent = create_agent(
    model=model,
    tools=[get_weather],
    checkpointer=checkpointer,
)

config = {
    "configurable": {
        "thread_id":"1"
    }
}

sf_response = agent.invoke(
    {"messages":[{"role": "user", "content":"what is weather in sf"}]},
    config=config
)

my_response = agent.invoke(
    {"messages": [{"role":"user","content":"what about new york?"}]},
    config=config
)

def serialize_response(obj):
    """将响应对象转换为可序列化的字段"""
    if hasattr(obj, "__dict__"):
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith("-"):
                continue
            result[key] = serialize_value(value)
        return result
    elif isinstance(obj,(list,tuple)):
        return [serialize_value(item) for item in obj]
    elif isinstance(obj,dict):
        return {k:serialize_value(v) for k,v in obj.items()}
    else:
        return str(obj)

def serialize_value(value):
    """递归序列化值"""
    if hasattr(value,"__dict__"):
        return serialize_response(value)
    elif isinstance(value,(list, tuple)):
        return [serialize_value(item) for item in value]
    elif isinstance(value,dict):
        return {k:serialize_value(v) for k,v in value.items()}
    else:
        try:
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            return str(value)

print(json.dumps(serialize_response(my_response),indent=2, ensure_ascii=False))
    