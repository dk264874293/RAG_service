import os 
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from mem0 import Memory
from mem0.configs.base import MemoryConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.llms.configs import LlmConfig 
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage,HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExpressCustomerService:
    def __init__(self):
        """初始化快递客服助手"""
        self.api_key = self._get_api_key()
        print(self.api_key)
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        # 初始化组件
        self.openai_client = None
        self.llm = None
        self.mem0 = None
        self.prompt = None

        self._initialize_components()
    
    def _get_api_key(self):
        """获取API密钥"""
        api_key = os.getenv("DASHSCOPE_API_KEY");
        if not api_key:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")
        logger.info("API密钥已获取")
        return api_key

    def _test_api_connection(self):
        """测试API连接"""
        try:
            response = self.openai_client.chat.completions.create(
                model="qwen-plus",
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=10
            )
            logger.info("API连接成功")  
            return True
        except Exception as e:
            logger.error(f"API连接失败: {e}")
            return False

    def _initialize_components(self):
        """初始化组件"""
        try:
            # 1. 初始化OpenAI客户端
            self.openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("OpenAI客户端已初始化")

            # 2. 测试api链接
            if not self._test_api_connection():
                raise Exception("OpenAI客户端未连接")

            # 3. 初始化langchain组件
            self.llm = ChatOpenAI(
                model_name="qwen-plus",
                openai_api_key=self.api_key,
                base_url=self.base_url,
                temperature=0.7
            )
            logger.info("langchain组件已初始化")
            config = MemoryConfig(
                llm=LlmConfig (
                    provider="openai",
                    config={
                        "model":"qwen-plus",
                        "api_key":self.api_key,
                        "openai_base_url":self.base_url,
                    }
                ),
                embedder=EmbedderConfig(
                    provider="openai",
                    config={
                        "model":"text-embedding-v2",
                        "api_key": self.api_key,
                        "openai_base_url":self.base_url,
                    }
                   
                )
            )
            self.mem0 = Memory(config=config)
            logger.info("Mem0组件已初始化")
            self._initialize_prompt()

        except Exception as e:
            logger.error(f"初始化OpenAI客户端失败: {e}")
            raise
    
    def _initialize_prompt(self):
        """初始化提示模板"""
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""您是一位专业的快递行业智能客服助手。请使用提供的上下文信息来个性化您的回复，记住用户的偏好和历史交互记录。

                您的主要职责包括：
                1. 快递查询服务：帮助用户查询包裹状态、物流轨迹、预计送达时间
                2. 寄件服务：提供寄件指导、价格咨询、时效说明、包装建议
                3. 问题解决：处理快递延误、丢失、损坏等问题，提供解决方案
                4. 服务咨询：介绍各类快递服务、收费标准、服务范围
                5. 投诉建议：接收用户反馈，记录投诉信息并提供处理方案

                回复时请保持：
                - 专业、礼貌、耐心的服务态度
                - 准确、及时的信息提供
                - 个性化的服务体验
                - 如果没有具体信息，可以基于快递行业常识提供建议

                请用中文回复，语气亲切专业。"""),
            MessagesPlaceholder(variable_name="context"),
            HumanMessage(content="{input}")
        ])
        
    def retrieve_context(self, query: str, user_id: str) -> str:
        """从Mem0检索相关上下文信息"""
        try:
            memories = self.mem0.search(query, user_id=user_id)

            if memories and "results" in memories and memories["results"]:
                serialized_memories = ' '.join([
                    mem.get("memory", "") for mem in memories["results"]
                ])
            else:
                serialized_memories = "暂无相关历史记录"
            
            context = [
                {
                    "role": "system",
                    "content": f"相关历史信息: {serialized_memories}"
                },
                {
                    "role": "user",
                    "content": query
                }
            ]

            return context
        except Exception as e:
            logger.error(f"从Mem0检索上下文失败: {e}")
            return  [
                {
                    "role": "system", 
                    "content": "相关历史信息: 暂无相关历史记录"
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
    def generate_response(self,user_input:str,context:List[Dict]) -> str:
        """使用llm生成回复"""
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({
                "context": context,
                "input": user_input
            })
            return response.content
        except Exception as e:
            logger.error(f"生成回复时出错: {str(e)}")
            return "抱歉，我现在遇到了一些技术问题，请稍后再试。如有紧急情况，请联系人工客服。"

    def save_interaction(self, user_id:str, user_input:str, assistant_response:str):
        """将交互记录保存到Mem0"""
        try:
            interaction = [
                {
                    "role": "user",
                    "content": user_input
                },
                {
                    "role": "assistant",
                    "content": assistant_response
                }
            ]
            self.mem0.add(interaction, user_id=user_id)
        except Exception as e:
            logger.warning(f"保存交互记录时出错: {str(e)}")

    def chat_turn(self, user_input: str, user_id: str) -> str:
        """处理一次聊天轮次"""
        try:
            # 检索上下文
            context = self.retrieve_context(user_input, user_id)
            
            # 生成回复
            response = self.generate_response(user_input, context)
            
            # 保存交互记录
            self.save_interaction(user_id, user_input, response)
            
            return response
        except Exception as e:
            logger.error(f"聊天轮次处理出错: {str(e)}")
            return "抱歉，我现在遇到了一些技术问题，请稍后再试。如有紧急情况，请联系人工客服。"

    def run_interactive_chat(self):
        """运行交互式聊天"""
        print("=" * 60)
        print("欢迎使用智能快递客服助手！")
        print("=" * 60)
        print("我可以帮您处理各种快递相关问题：")
        print("快递查询、寄件服务、问题处理、服务介绍等")
        print("输入 'quit'、'exit' 或 '再见' 结束对话")
        print("=" * 60)

        user_id = input("请输入您的客户ID:(或直接回撤使用默认ID):").strip()
        if not user_id:
            user_id = "default_user_id"

        print(f"您好！您的客户ID是: {user_id}")
        print("-" * 60)

        while True:
            try:
                user_input = input("您: ").strip()
                if user_input.lower() in ['quit', 'exit', '再见', '退出', 'bye']:
                    print("快递客服: 感谢您使用我们的服务！祝您生活愉快，期待下次为您服务！")
                    break

                if not user_input:
                    print("快递客服: 请输入您的问题，以便我更好地帮助您。")
                    continue


                response = self.chat_turn(user_input, user_id)
                print(f"快递客服: {response}\n")

            except KeyboardInterrupt:
                print("\n快递客服: 感谢您使用我们的服务！再见！")
                break
            except Exception as e:
                logger.error(f"交互过程中出错: {str(e)}")
                print("快递客服: 系统出现异常，请稍后重试。")

def main():
    """主程序入口"""
    try:
        # 创建客服助手实例
        service = ExpressCustomerService()
        
        # 运行交互式聊天
        service.run_interactive_chat()
        
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        print("\n请检查以下事项：")
        print("1. 确保已设置DASHSCOPE_API_KEY环境变量")
        print("2. 确保网络连接正常")
        print("3. 确保API密钥有效且有足够权限")
        print("4. 确保已安装所有必需的依赖包")


if __name__ == "__main__":
    main()
