from dotenv import load_dotenv
from langchain_community.chat_models import  ChatTongyi
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_community.embeddings import DashScopeEmbeddings
import json
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()


urls = [
    "https://lilianweng.github.io/posts/2023-06-23-agent/",  # AI代理相关文章
    "https://lilianweng.github.io/posts/2023-03-15-prompt-engineering/",  # 提示工程文章
    "https://lilianweng.github.io/posts/2023-10-25-adv-attack-llm/",  # LLM对抗攻击文章
]

llm = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True
)
llm_json_mode = ChatTongyi(
    model_name="qwen-turbo",
    temperature=0.7,
    streaming=True,
    format="json"
)

# 使用自定义请求头创建 WebBaseLoader
docs = [WebBaseLoader(
    web_paths=[url],
        requests_kwargs={
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
            "timeout": 30  # 添加超时避免挂起
        }
).load() for url in urls]

docs_list = [item for sublist in docs for item in sublist]


text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    chunk_size = 1000,
    chunk_overlap = 200
)

doc_splits = text_splitter.split_documents(docs_list)

vectorstore = SKLearnVectorStore.from_documents(
    documents = doc_splits,
    embedding = DashScopeEmbeddings(model="text-embedding-v3")
)

retriever = vectorstore.as_retriever(k=3)

print('retriever', retriever)

# 定义路由的系统指令，用于决定问题应该路由到向量存储还是网络搜索
router_instructions = """You are an expert at routing a user question to a vectorstore or web search.

The vectorstore contains documents related to agents, prompt engineering, and adversarial attacks.

Use the vectorstore for questions on these topics. For all else, and especially for current events, use web-search.

Return JSON with single key, datasource, that is 'websearch' or 'vectorstore' depending on the question."""

test_web_search = llm_json_mode.invoke([SystemMessage(content=router_instructions)]  # 系统消息包含路由指令
    + [
        HumanMessage(
            content="Who is favored to win the NFC Championship game in the 2024 season?"  # 询问2024赛季NFC冠军赛的热门球队
        )
    ]
)