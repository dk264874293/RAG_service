import os
import uuid
import atexit
import logging
from dotenv import load_dotenv
from typing import List,Dict,Any,Optional
from datetime import datetime

from langgraph.graph import StateGraph,MessagesState,START,END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.messages.utils import get_buffer_string
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

load_dotenv()
FAISS_INDEX_PATH = "faiss_memory_index"
FAISS_DIMENSION = 1536
FAISS_INDEX_TYPE = "IndexFlatIP"

DEFAULT_SEARCH_K = 5
MAX_MEMORY_DISPLAY = 3
MEMORY_TRUNCATE_LENGTH = 800

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class FAISSMemoryManager:
    """初始化FAISS记忆管理器
    
    Args:
        index_path: FAISS索引文件路径
    """
    def __init__(self,index_path:str = FAISS_INDEX_PATH):
        """
        初始化FAISS内存管理器
        Args:
            index_path: FAISS索引文件路径
        """
        self.index_path = index_path
        self.embeddings = DashScopeEmbeddings()
        self.vector_store = None
        self._initialize_store()

    def _initialize_store(self) -> None:
        """初始化或加载FAISS向量存储"""
        try:
            if os.path.exists(self.index_path):
                self._load_existing_index()
            else:
                self._create_new_index()
        except Exception as e:
            logger.error(f"初始化FAISS存储失败：{e}")
            self._create_new_index()
    
    def _load_existing_index(self) -> None:
        """加载现有的FAISS索引"""
        try:
            self.vector_store = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            vector_count = self.vector_store.index.ntotal
            logger.info(f"成功加载现有FAISS索引，包含{vector_count}个向量")
            print(f"[FAISS] 加载现有索引：{vector_count}个记忆向量")
        except Exception as e:
            logger.error(f"加载FAISS索引失败：{e}，将创建新索引")
            raise e
    
    def _create_new_index(self) -> None:
        """创建新的FAISS索引"""
        try:
            init_doc = "系统初始化文档 - FAISS向量数据库已就绪"
            self.vector_store = FAISS.from_texts(
                [init_doc],
                self.embeddings,
                metadatas = [{
                    "user_id":"system",
                    "type":"init",
                    "timestamp":datetime.now().isoformat(),
                    "id":str(uuid.uuid4())
                }]
            )
            logger.info("创建新的FAISS向量索引")
            print("[FAISS]创建新的向量索引")
        except Exception as e:
            logger.error(f"创建新的FAISS索引失败：{e}")
            raise e

    def save_index(self) -> bool:
        """保存FAISS索引到磁盘
        Returns:
            bool: 是否保存成功
        """

        try:
            self.vector_store.save_local(self.index_path)
            vector_count = self.vector_store.index.ntotal
            logger.info(f"成功保存FAISS索引到{self.index_path}")
            print(f"[FAISS] 保存索引到{self.index_path}")
            return True
        except Exception as e:
            logger.error(f"保存FAISS索引失败：{e}")
            return False
    def add_memory(self,content:str,user_id:str) -> bool:
        """
        添加记忆到向量存储

        Args:
            content: 记忆内容
            user_id: 用户ID

            Returns:
                bool: 是否添加成功
        """
        try:
            document = Document(
                page_content=content,
                metadata={
                    "user_id":user_id,
                    "id":str(uuid.uuid4()),
                    "timestamp":datetime.now().isoformat()
                }
            )
            self.vector_store.add_documents([document])
            logger.info(f"添加记忆成功：{content[:50]}...")
            return True
        except Exception as e:
            logger.error(f"添加记忆到向量存储失败：{e}")
            return False

    def search_memories(self,query:str,user_id:str, k :int = DEFAULT_SEARCH_K) -> List[str]:
        """
        搜索记忆

        Args:
            query: 查询内容
            user_id: 用户ID
            k: 返回的条数

            Returns:
                List[str]: 记忆列表
        """
        try:
            documents = self.vector_store.similarity_search(
                query = query,
                k = k *2
            )

            user_memories = [
                doc for doc in documents
                if(doc.metadata.get("user_id") == user_id and doc.metadata.get("type") != "init")
            ]

            memories = [doc.page_content for doc in user_memories[:k]]

            if memories:
                logger.info(f"检索到{len(memories)}条相关记忆")
            return memories
        except Exception as e:
            logger.error(f"搜索记忆失败：{e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            total_vectors = self.vector_store.index.ntotal
            return {
                "total_vectors":total_vectors,
                "index_path":self.index_path,
                "embedding_dimension":FAISS_DIMENSION,
                "index_type":FAISS_INDEX_TYPE
            }
        except Exception as e:
            logger.error(f"获取统计信息失败：{e}")
            return {
                "total_vectors":0,
                "index_path":self.index_path,
                "embedding_dimension":FAISS_DIMENSION,
                "index_type":FAISS_INDEX_TYPE
            }

memory_manager = FAISSMemoryManager()

model = ChatTongyi(
    model="qwen-turbo",
    temperature=0.7,
    streaming=True
)

prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个具有长期记忆能力的AI助手。

    记忆能力说明：
    - 我可以记住我们之前的对话内容
    - 我会根据相关记忆来回答你的问题
    - 如果需要保存重要信息，我会使用记忆工具

    当前相关记忆：
    {recall_memory}

    请根据上述记忆和当前对话，提供有帮助的回答。"""),
    MessagesPlaceholder(variable_name="messages")
])

def get_user_id(config:RunnableConfig) -> str:
    """从配置中提取用户ID
    
    Args:
        config: 运行配置

    Returns:
        str: 用户ID
    """
    return config["configurable"].get("user_id","default_user")

@tool
def save_recall_memory(memory:str,config:RunnableConfig) -> str:
    """保存记忆

    Args:
        memory: 记忆内容
        config: 运行配置

    Returns:
        str: 保存结果
    """
    user_id = get_user_id(config)
    success = memory_manager.add_memory(memory, user_id)
    if success:
        memory_manager.save_index()
        return f"记忆已保存：{memory[:50]}..."
    else:
        return "记忆保存失败"

@tool
def get_recall_memories(query:str,config:RunnableConfig) -> List[str]:
    """获取记忆

    Args:
    query: 查询内容
    config: 运行配置

    Returns:
        List[str]: 记忆列表
    """
    user_id = get_user_id(config)
    memories = memory_manager.search_memories(query, user_id,MAX_MEMORY_DISPLAY)
    if memories:
        print(f"[记忆检索]找到{len(memories)}条相关记忆")
        for i, memory in enumerate(memories,1):
            print(f"{i}. {memory[:100]}...")
        return memories
    else:
        return ["没有找到相关记忆"]

@tool
def search_recall_memories(query:str, config:RunnableConfig) -> List[str]:
    """从FAISS向量存储中搜索相关记忆
    
    Args:
        query: 查询内容
        config: 运行配置

    Returns:
        List[str]: 相关记忆列表
    """
    user_id= get_user_id(config)
    memories = memory_manager.search_memories(query, user_id,MAX_MEMORY_DISPLAY)
    if memories:
        print(f" [记忆检索] 找到 {len(memories)} 条相关记忆")
        for i, memory in enumerate(memories, 1):
            print(f"   {i}. {memory[:100]}...")
    
    return memories


class State(MessagesState):
    """
    对话状态类
    扩展MessagesState以包含记忆相关字段
    """
    recall_memories: List[str]

def load_memories(state,config:RunnableConfig) -> State:
    """
    加载相关记忆节点

    Args:
        state: 对话状态（可能是字典或State对象）
        config: 运行配置

    Returns:
        State: 更新后的对话状态
    """
    convo_str = get_buffer_string(state["messages"])
    convo_str = convo_str[:MEMORY_TRUNCATE_LENGTH]
    
    # 搜索相关记忆
    recall_memories = search_recall_memories.invoke(convo_str, config)
    print(f"检索到的记忆{recall_memories}")
    return {
        "recall_memories": recall_memories,
    }

def agent(state) -> dict:
    """
    AI代理节点

    Args:
        state: 当前状态（可能是字典或State对象）

    Returns:
        dict: 更新后的对话状态
    """
    # 确保state是字典格式

    model_with_tools = model.bind_tools([save_recall_memory])
    recall_str = ""
    if state.get("recall_memories"):
        recall_str = "\n".join([f"• {memory}" for memory in state["recall_memories"]])

    response = prompt.invoke({
        "messages":state["messages"],
        "recall_memory": recall_str or "暂无相关记忆"
    })

    prediction = model_with_tools.invoke(response)

    return {
        "messages": state["messages"] + [prediction]
    }

def save_memory(state,config:RunnableConfig) -> State:
        """
        保存记忆节点

        Args:
            state: 对话状态（可能是字典或State对象）
            config: 运行配置

        Returns:
            State: 更新后的对话状态
        """
        messages = state["messages"]
        if len(messages) >= 2:
            user_msg = None
            ai_msg = None

            for msg in reversed(messages):
                if hasattr(msg,"role"):
                    if msg.role == "user" and user_msg is None:
                        user_msg = msg.content
                    elif msg.role == "assistant" and ai_msg is None:
                        ai_msg = msg.content
                elif isinstance(msg,dict):
                    if msg.get("role") == "user" and user_msg is None:
                        user_msg = msg.get("content")
                    elif msg.get("role") == "assistant" and ai_msg is None:
                        ai_msg = msg.get("content")
                if user_msg and ai_msg:
                    break
            if user_msg and ai_msg:
                memory_content = f"用户：{user_msg}\n助手：{ai_msg}"
                save_recall_memory.invoke(memory_content,config)
        return {}

def route_tools(state):
    """工具路由节点
    
    Args:
        state: 当前状态（可能是字典或State对象）
        
    Returns:
        str: 下一个节点名称
    """
    # 确保state是字典格式
    # state_dict = state if isinstance(state, dict) else state.__dict__
    
    msg = state["messages"][-1]
    if hasattr(msg, 'tool_calls') and msg.tool_calls:
        return "tools"
    return END

def build_graph() -> StateGraph:
    """构建状态图
    
    Returns:
        StateGraph: 状态图实例
    """
    builder = StateGraph(State)

    builder.add_node("load_memories", load_memories)
    builder.add_node("agent", agent)
    builder.add_node("save_memory", save_memory)
    builder.add_node("tools", ToolNode([
        save_recall_memory,
        get_recall_memories
    ]))

    builder.add_edge(START, 'load_memories')
    builder.add_edge('load_memories', 'agent')
    builder.add_edge("agent", "save_memory")
    builder.add_conditional_edges("save_memory", route_tools, ["tools", END])
    builder.add_edge("tools", END)

    return builder.compile()

# ================================
# 演示和工具函数
# ================================

def print_separator(title: str = "", char: str = "=", width: int = 60) -> None:
    """打印分隔符
    
    Args:
        title: 标题
        char: 分隔符字符
        width: 宽度
    """
    if title:
        title_line = f" {title} "
        padding = (width - len(title_line)) // 2
        print(f"{char * padding}{title_line}{char * padding}")
    else:
        print(char * width)

def print_stats() -> None:
    """打印统计信息"""
    stats = memory_manager.get_stats()
    print("FAISS 向量数据库统计")
    print(f" 总向量数量: {stats.get('total_vectors', 0)}")
    print(f" 索引路径: {stats.get('index_path', 'N/A')}")
    print(f" 嵌入维度: {stats.get('embedding_dimension', 'N/A')}")
    print(f"  索引类型: {stats.get('index_type', 'N/A')}")

def get_stream_chunk(chunk: Dict[str, Any]) -> None:
    """处理流式输出块
    
    Args:
        chunk: 输出块
    """
    for node, update in chunk.items():
        if update is None:
            continue
        
        # 处理消息输出
        msgs = update.get("messages")
        if msgs:
            last = msgs[-1]
            content = getattr(last, "content", None) or (
                last.get("content") if isinstance(last, dict) else None
            )
            if content:
                print(f" 助手: {content}")
        
        # 处理记忆输出
        if "recall_memories" in update and update["recall_memories"]:
            memories = update["recall_memories"]
            print(f" [激活记忆] 检索到 {len(memories)} 条相关记忆")

def run_demo_conversation(graph: StateGraph, config: Dict[str, Any]) -> None:
    """运行演示对话
    
    Args:
        graph: 状态图
        config: 配置
    """
    demo_conversations = [
        {
            "title": "第一轮对话 - 建立记忆",
            "message": "我喜欢吃苹果，特别是红富士苹果"
        },
        {
            "title": "第二轮对话 - 记忆检索",
            "message": "我喜欢吃什么水果？"
        },
        {
            "title": "第三轮对话 - 扩展记忆",
            "message": "我还喜欢吃香蕉和橙子"
        },
        {
            "title": "第四轮对话 - 综合记忆",
            "message": "总结一下我的水果偏好"
        }
    ]
    
    for i, conv in enumerate(demo_conversations, 1):
        print(f"{conv['title']}")
        print(f" 用户: {conv['message']}")
        print()
        
        for chunk in graph.stream(
            {"messages": [{"role": "user", "content": conv["message"]}]},
            config=config
        ):
            get_stream_chunk(chunk)
        
        print()
        if i < len(demo_conversations):
            input("按回车键继续下一轮对话...")
            print()

def main():
    """主程序入口"""
    print("FAISS 长期记忆系统演示")
    print(" 本演示将展示基于FAISS向量数据库的长期记忆能力")
    print(" 特性: 持久化存储、高效检索、用户隔离、记忆管理")
    print()
    
    # 显示初始统计
    print_stats()
    
    # 构建图
    graph = build_graph()
    
    # 配置
    config = {
        "configurable": {
            "thread_id": "demo-thread-1",
            "user_id": "demo-user-1",
        }
    }
    
    # 运行演示
    try:
        run_demo_conversation(graph, config)
        
        print("演示完成")
        print_stats()
        print(" FAISS长期记忆系统演示完成！")
        print(" 记忆已持久化保存，重启程序后仍可使用")
        
    except KeyboardInterrupt:
        print("\n\n  演示被用户中断")
    except Exception as e:
        logger.error(f"演示过程中发生错误: {e}")
        print(f" 演示失败: {e}")
    finally:
        # 确保保存索引
        memory_manager.save_index()


# 注册退出时保存索引
atexit.register(memory_manager.save_index)


if __name__ == "__main__":
    main()