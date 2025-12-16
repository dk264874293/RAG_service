'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-15 17:12:48
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-16 08:30:47
FilePath: /RAG_service/chain/rag_langgraph/rag_tongyi.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AErom langchain_community.chat
'''
import re
from typing import Annotated, Sequence, Literal
from typing_extensions import TypedDict
import operator

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START , END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

class GraphState(TypedDict):
    messages: Annotated[Sequence ,add_messages]
    retry_count: int

def is_valid_order_id(text: str) -> bool:
    return  bool(re.fullmatch(r"\d{10,12}", text))

def validate_input(state: GraphState) -> Literal['valid', 'invalid']:
    last_message = state["messages"][-1]
    user_input = last_message.content.strip()
    if is_valid_order_id(user_input):
        return 'valid'
    return 'invalid'

def receive_input(state: GraphState):
    user_input = state["messages"][-1].content.strip()
    return {"order_id": user_input}

def query_order(state: GraphState):
    order_id = state["messages"][-1].content.strip()    
    print(f"查询订单: {order_id}")
    return {
        "messages": [AIMessage(content="订单状态: 已发货")],
        "status": "success"
    }

def handle_invalid(state:GraphState):
    retry = state.get("retry_count", 0)
    if retry >= 2:
        reply = "输入错误次数过多，会话结束。"
        return {"messages": [AIMessage(content=reply)], "retry_count": retry + 1}
    reply = "订单号不合法，请输入10到12位数字。"
    return {"messages": [AIMessage(content=reply)], "retry_count": retry + 1}

builder = StateGraph(GraphState)

builder.add_node('receive_input',receive_input)
builder.add_node('query_order',query_order)
builder.add_node('handle_invalid',handle_invalid)

builder.add_conditional_edges(
    START,
    validate_input,
    {
        'valid': 'query_order',
        'invalid': 'handle_invalid'
    }
)

builder.add_conditional_edges(
    "handle_invalid",
    lambda s: "receive_input" if s["retry_count"] < 2 else END
)

builder.add_edge("receive_input","query_order")
builder.add_edge("query_order", END)
    
memory_saver = MemorySaver()

app = builder.compile(checkpointer = memory_saver)

config = {
    "configurable": {
        "thread_id": "1"
    }
}

response = app.invoke(
    {"messages": [HumanMessage(content="123")]},
    config=config,
)

history = app.get_state_history(config)

for snapshot in history:
    print("Messages:", snapshot.values["messages"])
    print("Retry count:", snapshot.values.get("retry_count", 0))
    print("---")

# class AgentState(BaseModel):
#     messages: Annotated[Sequence[str], operator.add] = Field(default_factory=list)
#     step_count: int = 0

# def node1(state: AgentState) -> dict:
#     print(f"[Node1] 当前 step_count: {state.step_count}")
#     new_message = f"Hello from node1 at step {state.step_count + 1}"
#     return {
#         "messages": [new_message],
#         "step_count": state.step_count + 1,
#     }

# def node2(state: AgentState) -> dict:
#     print(f"[Node2] 当前 step_count: {state.step_count}")
#     new_message = f"Goodbye from node2 at step {state.step_count + 1}"
#     return {
#         "messages": [new_message],
#         "step_count": state.step_count + 1,
#     }

# builder = StateGraph(AgentState)

# builder.add_node('node1',node1)
# builder.add_node('node2',node2)

# builder.add_edge(START, 'node1')
# builder.add_edge('node1', 'node2')
# builder.add_edge('node2', END)

# memory = MemorySaver()

# graph = builder.compile(checkpointer = memory)

# config = {"configurable": {"thread_id": "123"}}
# result = graph.invoke(
#     {"messages": ["Initial input"], "step_count": 0},
#     config=config
# )

# print("\n 最终输出:")
# print(result)

# # === 5. 获取状态历史（快照）===
# print("\n 状态变更历史（快照）:")
# state_history = list(graph.get_state_history(config))
# for state in state_history:
#     print(state)

# config = {"configurable":{'thread_id': '123',  'checkpoint_id': '1f090bb7-f882-6a9b-8001-220d0d477fdb'}}

# checkpoint_snapshot = graph.get_state(config)

# graph.invoke({"messages": ["Initial input"], "step_count": 0}, config=config)

# class GraphState(BaseModel):
#     messages: Annotated[Sequence[str], operator.add]
#     user_input: str
#     tool_calls: list
#     final_response: str

# def handle_user_input(state:GraphState) -> dict:
#     return {
#         "user_input": state.messages[-1] if state.messages  else ""
#     }

# def generate_response(state:GraphState) -> dict:
#     response = f"AI 回复： 收到你的消息 {state.user_input}"
#     return {
#         "messages": [response],
#         "final_response": response
#     }

# builder = StateGraph(GraphState)

# builder.add_node("input", handle_user_input)
# builder.add_node("llm", generate_response)

# builder.add_edge(START, "input")
# builder.add_edge("input", "llm")
# builder.add_edge("llm", END)

# graph = builder.compile()

# result = graph.invoke({
#     "messages": ["Hello from TypeDict!"],
#     "user_input": "",
#     "tool_calls": [],
#     "final_response": ""
# })
# print(result["final_response"])

# from langchain.agents import create_agent
# from langchain_community.chat_models import ChatTongyi
# from dotenv import load_dotenv

# load_dotenv()

# llm = ChatTongyi(
#     model_name="qwen-plus",
#     temperature=0.7,
#     streaming=True
# )

# agent = create_agent(
#     llm, 
#     tools=[],
#     system_prompt="You are a helpful assistant."
# )

# # response = agent.invoke({"input": "你好，帮我查一下北京今天的天气。"})

# for chunk in agent.stream(
#     {"messages":[{"role":"user","content":"你叫什么？"}]},
#     stream_mode = "messages"
# ):
#     print(chunk[0].content)
#     print("\n")