'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-17 15:33:11
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-17 21:46:59
FilePath: /RAG_service/chain/rag_autogen/rag_lifht.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEfrom

'''
from typing import Any, Dict,List
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import HandoffTermination, TextMentionTermination
from autogen_agentchat.messages import HandoffMessage
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv
import asyncio
import os

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

def refund_flight(flight_id: str) -> str:
    """
    模拟执行航班退款操作的工具函数。
    在真实场景中，此函数会调用航空公司或票务系统的API。
    
    Args:
        flight_id (str): 需要退款的航班ID。
        
    Returns:
        str: 退款操作的结果信息。
    """
    return f"航班{flight_id} 已成功退款"

travel_agent = AssistantAgent(
    "travel_agent",
    model_client=model_client,
    handoffs=["flights_refunder", "user"],
    system_message="""
你是一位专业的旅行顾问。
你的主要职责是接待客户并初步评估他们的请求。
- 如果客户的请求涉及航班退款，请将任务移交给专门处理此事的 'flights_refunder'。
- 如果你需要向客户获取更多信息（例如行程细节），你必须先在消息中清楚地提出你的问题，然后才能将任务移交给 'user'。
- 当你确认所有事项都已妥善处理完毕后，请输出 'TERMINATE' 来结束本次服务流程。"""
)

flights_refunder = AssistantAgent(
    "flights_refunder",
    model_client=model_client,
    handoffs=["travel_agent", "user"],
    tools=[refund_flight],
    system_message="""
你是一位专注于处理航班退款的专家代理。
你的工作是高效、准确地完成退款操作。
- 你只需要客户提供航班参考号即可启动退款流程。
- 你可以使用 'refund_flight' 工具来执行实际的退款操作。
- 如果缺少关键信息（如航班号），你必须先发送一条消息说明你需要什么信息，然后将任务移交给 'user' 以等待回复。
- 当你成功完成退款交易后，请将控制权交还给 'travel_agent'，由其进行最终确认并向客户通报结果。"""
)

termination = (
    HandoffTermination(target="user") | # 当任务被移交给 "user" 时，流程暂停，等待用户输入
    TextMentionTermination("TERMINATE")  # 当任何消息中包含 "TERMINATE" 字样时，流程完全结束
)

# 创建 Swarm 团队，将两个代理组织起来，并指定终止条件。
# 所有代理共享相同的消息上下文，发言顺序由最新的 HandoffMessage 决定。
team = Swarm(
    [travel_agent, flights_refunder],
    termination_condition=termination,
)

task = "我需要退掉我的航班。"

async def run_team_stream() -> None:
    """
        运行团队并处理与用户的交互循环。
        该函数处理自动化流程与人工输入之间的切换。
    """
    print("开始运行团队...")
    # 创建一个局部变量current_task，初始化为全局task
    current_task = task
    
    while True:
        print(f"执行任务: {current_task}")
        # 运行团队并获取结果
        result = await team.run(task=current_task)
        print("获取到结果...")
        
        # 打印智能体的回复
        if hasattr(result, 'messages') and result.messages:
            print(f"消息数量: {len(result.messages)}")
            for msg in result.messages:
                print(f"消息来源: {msg.source}")
                if hasattr(msg, 'target'):
                    print(f"消息目标: {msg.target}")
                print(f"消息类型: {type(msg).__name__}")
                if hasattr(msg, 'content'):
                    print(f"消息内容: {msg.content}")
            
            last_message = result.messages[-1]
            if hasattr(last_message, 'content'):
                print(f"最新消息: {last_message.source}: {last_message.content}")
            
            # 检查是否需要用户输入
            need_user_input = False
            
            # 检查最新消息是否是HandoffMessage且目标是"user"
            if isinstance(last_message, HandoffMessage) and last_message.target == "user":
                need_user_input = True
            
            # 检查所有消息，看是否有请求用户信息的内容
            for msg in result.messages:
                if hasattr(msg, 'content'):
                    # 确保content是字符串类型
                    if isinstance(msg.content, str):
                        content = msg.content.lower()
                        if any(keyword in content for keyword in ["航班参考号", "需要您的", "请提供", "请输入", "请告知"]):
                            need_user_input = True
                            break
                        if "transferred to user" in content:
                            need_user_input = True
                            break
            
            if need_user_input:
                print("需要用户输入...")
                # 等待用户输入
                user_message = input("用户：")
                print(f"用户输入: {user_message}")
                
                # 检查是否需要终止
                if user_message.strip().upper() == "TERMINATE":
                    print("收到终止命令...")
                    break
                
                # 创建一个新的HandoffMessage，目标是当前的智能体而不是"user"
                # 或者直接将用户输入作为消息内容发送
                current_task = HandoffMessage(
                    content=user_message,
                    source="user",
                    target=last_message.source  # 将用户输入发送回刚才请求信息的智能体
                )
            elif hasattr(last_message, 'content') and "TERMINATE" in last_message.content:
                # 如果收到终止命令，结束循环
                print("收到终止命令...")
                break
            else:
                # 否则，结束循环
                break

if __name__ == "__main__":
    asyncio.run(run_team_stream())

    