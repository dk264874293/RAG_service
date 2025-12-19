from typing import Annotated
import os
from langchain_core.messages import convert_to_messages
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START,MessagesState
from langgraph.types import Command
from langchain_community.chat_models import ChatTongyi
from dotenv import load_dotenv
load_dotenv()

def pretty_print_message(message,indent=False):
    """
    美化单条消息的打印输出。
    
    Args:
        message: 要打印的消息对象。
        indent (bool): 是否添加缩进（用于子图）。
    """
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message)
        return
    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented)

def pretty_print_messages(update, last_message = False):
    """
    美化消息更新的打印输出。
    
    Args:
        update: 包含消息更新的对象。
        last_message (bool): 是否仅打印最后一条消息（用于子图）。
    """
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        if len(ns) == 0:
            return
        graph_id = ns[-1].split(":")[0]
        print(f"来自子图{graph_id}的更新")
        print("\n")
        is_subgraph = True

    for node_name, node_update in update.items():
        update_label = f"来自子图{node_name}的更新"
        if is_subgraph:
            update_label = '\t' + update_label
        print(update_label)
        print("\n")
        messages = convert_to_messages(node_update["messages"])
        if last_message:
            messages = messages[-1:]
        for m in messages:
            pretty_print_message(m, indent=is_subgraph)
        print("\n")

def create_handoff_tool(*,agent_name:str,description:str | None = None):
    """
    工厂函数：创建一个可以将控制权移交给指定代理的特殊工具。
    这是实现多代理协作的核心机制。
    
    Args:
        agent_name (str): 目标代理的名称。
        description (str, optional): 该工具的描述。
        
    Returns:
        function: 一个可被智能体调用的工具函数。
    """
    name = f"transfer_to_{agent_name}"
    description = description or f"转移到{agent_name}"

    @tool(name,description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id:Annotated[str, InjectedToolCallId]
    ) -> Command:
        tool_message = {
            "role": "tool",
            "content": f"成功转移到{agent_name}",
            "name":name,
            "tool_call_id":tool_call_id
        }
        return Command(
            goto=agent_name,
            update={"messages":state["messages"] + [tool_message]},
            graph=Command.PARENT
        )
    return handoff_tool
    
transfer_to_hotel_assistant = create_handoff_tool(
    agent_name="hotel_assistant",
    description="将用户转接给酒店预订助理。",
)

transfer_to_flight_assistant = create_handoff_tool(
    agent_name="flight_assistant",
    description="将用户转接给机票预订助理。",
)

def book_hotel(hotel_name:str):
    """模拟预订酒店的操作"""
    return f"已成功预订{hotel_name}的住宿"

def book_flight(from_airport:str, to_airport:str):
    """模拟预订机票的操作"""
    return f"已成功预订从{from_airport}到{to_airport}的航班"

chat_llm = ChatTongyi(
    model="qwen-plus",
    # base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
)

flight_assistant = create_agent(
    model=chat_llm,
    name="flight_assistant",
    tools=[book_flight,transfer_to_hotel_assistant],
    system_prompt="你是一位专业的航班预订助理。你的任务是帮助用户预订航班。如果用户还需要预订酒店，请使用 transfer_to_hotel_assistant 工具将他们转接给酒店助理。"
)

hotel_assistant = create_agent(
    model=chat_llm,
    name="hotel_assistant",
    tools=[book_hotel,transfer_to_flight_assistant],
    system_prompt="你是一位专业的酒店预订助理。你的任务是帮助用户预订酒店。如果用户还需要预订航班，请使用 transfer_to_flight_assistant 工具将他们转接给航班助理。"
)

multi_agent_graph = (
    StateGraph(MessagesState)
    .add_node(flight_assistant)
    .add_node(hotel_assistant)
    .add_edge(START, "flight_assistant")
    .compile()
)

for chunk in multi_agent_graph.stream(
    {
        "messages": [
            {
                "role":"user",
                "content":"请帮我预订一张从波士顿(BOS)到纽约(JFK)的机票，以及在麦克基特里克酒店(McKittrick Hotel)的住宿"
            }
        ]
    }
):
    pretty_print_messages(chunk)