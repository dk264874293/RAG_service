'''Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-24 10:18:35
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-24 10:44:28
FilePath: /RAG_service/chain/memory/window_mem.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
import os
from dotenv import load_dotenv
from langchain_core.messages.utils import (
    trim_messages,
    count_tokens_approximately
)
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, before_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import tool

load_dotenv()

model = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.7,
    streaming=True
)

@tool
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}"

tools = [get_weather]

# 创建自定义中间件，用于修剪消息历史
@before_model
def trim_messages_middleware(state, config):  # 接受两个参数
    """修剪消息历史，保持最近的384个token"""
    return {
        "llm_input_messages": trim_messages(
            state["messages"],
            strategy="last",  # 保留最后的消息（最新的消息）
            token_counter=count_tokens_approximately,
            max_tokens=384,  # 窗口大小限制（以token计算）
            start_on="human",  # 确保从人类消息开始
            end_on=("human", "tool"),  # 在人类或工具消息结束
        )
    }

checkpointer = InMemorySaver()  # 修正变量名

agent = create_agent(
    model=model,
    tools=tools,
    checkpointer=checkpointer,  # 使用正确的参数名
    middleware=[trim_messages_middleware]
)

# 示例使用
if __name__ == "__main__":
    print("窗口记忆机制演示")
    print("=" * 50)
    print("特性:")
    print("- 保持最近384个token的对话历史")
    print("- 自动删除超出窗口的旧消息")
    print("- 保持消息的时间顺序")
    print("- 确保对话的连续性")
    print()
    
    # 配置
    config = {
        "configurable": {
            "thread_id": "window-demo-1"
        }
    }
    
    # 演示对话
    demo_messages = [
        "你好，我是张三，今年25岁",
        "我住在北京，是一名软件工程师",
        "我喜欢编程和阅读",
        "请问今天北京的天气怎么样？",
        "你还记得我的名字和职业吗？"
    ]
    
    print("开始演示对话:")
    print("-" * 30)
    
    for i, message in enumerate(demo_messages, 1):
        print(f"\n[轮次 {i}] 用户: {message}")
        
        try:
            # 调用agent处理消息
            response = agent.invoke(
                {"messages": [{"role": "user", "content": message}]},
                config=config
            )
            
            # 显示AI回复
            if response and "messages" in response:
                ai_message = response["messages"][-1]
                if hasattr(ai_message, 'content'):
                    print(f"[轮次 {i}] AI: {ai_message.content}")
                else:
                    print(f"[轮次 {i}] AI: {ai_message}")
            
        except Exception as e:
            print(f"[轮次 {i}] 错误: {e}")
    
    print("\n" + "=" * 50)
    print("窗口记忆机制演示完成！")
    print("注意：由于窗口限制，早期的对话可能会被自动删除")