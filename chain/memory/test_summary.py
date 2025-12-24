'''Test summarization middleware with multi-turn conversation'''
from langchain_community.chat_models import ChatTongyi
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages.utils import count_tokens_approximately
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize model
model = ChatTongyi(
    model_name="qwen-turbo",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
    temperature=0.5,
)

# Define tools
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}"

def get_population(city: str) -> str:
    """Get population for a given city."""
    populations = {
        "北京": "about 21.5 million",
        "上海": "about 24.8 million",
        "广州": "about 18.7 million",
        "深圳": "about 17.6 million"
    }
    return populations.get(city, "unknown population")

tools = [get_weather, get_population]

# Initialize summarization middleware
summary_middleware = SummarizationMiddleware(
    model=model,
    token_counter=count_tokens_approximately,
    trigger=("tokens", 500),  # Trigger summarization when token count exceeds 500
    keep=("tokens", 200),     # Keep only 200 tokens after summarization
    output_messages_key="messages",
)

# Create agent with middleware
checkpointer = InMemorySaver()
agent = create_agent(
    model=model,
    tools=tools,
    middleware=[summary_middleware],
    checkpointer=checkpointer,
)

# Configuration for session
config = {
    "configurable": {
        "thread_id": "test_session_1"
    }
}

# Test multi-turn conversation
print("=== Testing Multi-Turn Conversation with Summarization Middleware ===")

# First turn
print("\nTurn 1: 北京今天天气怎么样？")
response1 = agent.invoke(
    {"messages": [{"role": "user", "content": "北京今天天气怎么样？"}]},
    config=config,
)
print(f"Agent response: {response1['messages'][-1].content}")

# Second turn
print("\nTurn 2: 上海的人口有多少？")
response2 = agent.invoke(
    {"messages": [{"role": "user", "content": "上海的人口有多少？"}]},
    config=config,
)
print(f"Agent response: {response2['messages'][-1].content}")

# Third turn
print("\nTurn 3: 我刚才问了关于北京的什么问题？")
response3 = agent.invoke(
    {"messages": [{"role": "user", "content": "我刚才问了关于北京的什么问题？"}]},
    config=config,
)
print(f"Agent response: {response3['messages'][-1].content}")

print("\n=== Conversation History ===")
for msg in response3['messages']:
    print(f"{msg.type}: {msg.content[:50]}{'...' if len(msg.content) > 50 else ''}")