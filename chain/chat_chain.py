'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-11-30 10:07:23
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-11-30 10:28:50
FilePath: /RAG_service/chain/chat_chain.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage
from langchain_community.llms import Tongyi
from typing import List, Dict, Any
import asyncio
import os
from dotenv import load_dotenv  

# 加载环境变量
load_dotenv()

class ChatChain:
    def __init__(self):
        self.llm = None
        self.chain = None
        self.parser = StrOutputParser()

    async def initialize(self):
        # 从环境变量中获取API密钥
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        
        self.llm = Tongyi(
            temperature=0.8,
            model_name="gwen-plus",
            dashscope_api_key=dashscope_api_key
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能客服助手，请遵循以下规则：
                1. 友好、专业地回答用户问题
                2. 如果不确定答案，诚实地说不知道
                3. 保持回答简洁明了
                4. 根据对话历史提供连贯的回复
                5. 用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}")
        ])

        self.chain = (
            RunnablePassthrough.assign(history=self._format_history)
            | self.prompt
            | self.llm
            | self.parser
        )

    async def process_message(self,message:str,history:List[Dict] = None) -> str:
        """处理用户消息"""
        try:
            input_data = {
                "message":message,
                "raw_history": history or []
            }

            response = await self.chain.ainvoke(input_data)

            return response.strip()

        except Exception as e:
            print(f"处理消息时出错: {e}")
            return "抱歉，我现在无法处理您的请求，请稍后再试。"

    def _format_history(self,input_data:Dict[str,Any]) -> List:
            """格式化历史消息为 LangChain 消息格式"""
            history = input_data.get("raw_history",[])

            if not history:
                return []

            message = []

            recent_history = history[-5:] if len(history) > 5 else history

            for item in recent_history:
                message.append(HumanMessage(content=item["user_message"]))
                message.append(AIMessage(content=item["bot_reply"]))
            return message