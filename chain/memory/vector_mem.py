from tabnanny import check
from langgraph.graph import StateGraph,MessagesState,START,END
from langgraph.prebuilt import ToolNode
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.messages.utils import get_buffer_string
from typing import List
import os
import uuid
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

load_dotenv()

recall_vector_store = InMemoryVectorStore(DashScopeEmbeddings())

model = ChatTongyi(
    model="qwen-turbo",
    temperature=0.5,
    streaming=True
)

prompt = ChatPromptTemplate.from_messages([
     ("system", """
    你是一个有记忆能力的助手。请根据用户的问题和下面提供的记忆内容回答。
    如果记忆中有相关信息，请利用这些信息来回答。
    如果需要保存新的记忆，请使用save_recall_memory工具。
    
    {recall_memory}
    """),
    MessagesPlaceholder(variable_name="messages")
])

def get_user_id(config:RunnableConfig) -> str:
    """从RunnableConfig中提取用户ID"""
    return config["configurable"]["user_id"]

@tool
def save_recall_memory(memory:str,config:RunnableConfig) -> str:
    """将用户记忆保存到向量存储中"""
    user_id = get_user_id(config)
    document = Document(
        page_content=memory,
        id = str(uuid.uuid4()),
        metadata={"user_id":user_id}
    )
    recall_vector_store.add_document([document])
    return memory

@tool
def search_recall_memories(query:str,config:RunnableConfig) -> List[str]:
    """检索用户记忆"""
    user_id = get_user_id(config)
    def _filter_function(doc:Document) -> bool:
        return doc.metadata.get("user_id") == user_id
    documents = recall_vector_store.similarity_search(
        query=query,
        k=3,
        filter=_filter_function
    )
    return [doc.page_content for doc in documents]

class State(MessagesState):
    """对话状态"""
    recall_memories:List[str]

def agent(state:State) -> State:
    """处理当前状态并生成回复"""
    model_with_tools = model.bind_tools([save_recall_memory])

    recall_str = ""
    if "recall_memories" in state and state["recall_memories"]:
        recall_str = "\n".join(state["recall_memories"])

    response = prompt.invoke({
        "messages":state["messages"],
        "recall_memory": recall_str
    })
    prediction = model_with_tools.invoke(response)

    return {
        "messages": state["messages"] + [prediction]
    }

def save_memory(state:State,config:RunnableConfig) -> State:
    """保存当前对话内容到记忆中"""
    messages = state["messages"]
    if len(messages) >= 2:
        user_msg = None
        ai_msg = None

        for msg in reversed(messages):
            if hasattr(msg, "role"):
                if msg.role == "user" and user_msg is None:
                    user_msg = msg.content
                elif msg.role == "assistant" and user_msg is None:
                    user_msg = msg.get("content", "")
            elif isinstance(msg,dict):
                if msg.get("role") == "user" and user_msg is None:
                    user_msg = msg.get("content", "")
                elif msg.get('role') == "assistant" and ai_msg is None:
                    ai_msg = msg.get("content", "")
        
        if user_msg and ai_msg:
            memory_content = f"用户问：{user_msg}\n助手答：{ai_msg}"
            save_recall_memory.invoke(memory_content,config)
    return {}

def load_memories(state:State,config:RunnableConfig) -> State:
    convo_str = get_buffer_string(state["messages"])
    convo_str = convo_str[:800]
    recall_memories = search_recall_memories.invoke(convo_str,config)
    return {
        "recall_memories":recall_memories
    }

def route_tools(state:State,config:RunnableConfig) -> State:
    """根据最后一条信息决定下一步操作"""
    msg = state["messages"][-1]
    if msg.tool_calls:  # 修复拼写错误：too_calls -> tool_calls
        return "tools"
    return END


builder = StateGraph(State)
builder.add_node("load_memories", load_memories)
builder.add_node("agent", agent)
builder.add_node("save_memory", save_memory)
tools = [save_recall_memory,search_recall_memories]
builder.add_node("tools",ToolNode(tools))

builder.add_edge(START,"load_memories")
builder.add_edge("load_memories","agent")
builder.add_edge("agent","save_memory")
builder.add_conditional_edges("save_memory",route_tools,["tools",END])
builder.add_edge("tools", "agent")

memory = MemorySaver()

graph = builder.compile(checkpointer=memory)

config = {
    "configurable":{
        "thread_id":"thread-1",
        "user_id":"user-1"
    }
}

def get_stream_chunk(chunk):
    for node, update in chunk.items():
        if update is None:
            continue
        msgs = update.get("messages")
        if msgs:
            last = msgs[-1]
            content = getattr(last,"content",None) or (last.get("content") if isinstance(last,dict) else None)
            if content:
                print(content)
        if "recall_memories" in update and update["recall_memories"]:
            print(f"[检索到的记忆]{update['recall_memories']}")

for chunk in graph.stream(
    {"messages": [{
        "role":"user",
        "content": "我喜欢吃苹果"
    }]},
    config=config  # 移除冗余的 config = config
):
    get_stream_chunk(chunk)

for chunk in graph.stream(
    {"messages": [{"role": "user", "content": "我喜欢吃什么"}]},
    config=config
):
    get_stream_chunk(chunk)