'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-05 13:35:03
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-05 14:12:48
FilePath: /RAG_service/chain/dashscope_embedding.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
# from langchain.chains import LLMRouterChain, MultiPromptChain
from langchain_core.language_models import BaseLLM
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Tongyi
from dotenv import load_dotenv
import os
load_dotenv()

# 1. 定义任务名称与描述
names_and_descriptions = [
    ("physics", ["用于解答物理相关问题，例如力学、电磁学等"]), 
    ("math", ["用于解答数学相关问题，例如代数、几何、微积分等"]), 
]

embedding = DashScopeEmbeddings(model="text-embedding-v2")

descriptions = []

names = []
for name, desc_list in names_and_descriptions:
    for desc in desc_list:
        descriptions.append(desc)
        names.append(name)

vectorstore = Chroma(embedding_function=embedding)

vectorstore.add_texts(texts=descriptions, metadatas=[{"name":name} for name in names])

def get_relevant_chain_name(question:str) -> str:
    docs = vectorstore.similarity_search(question, k=1)
    return docs[0].metadata["name"]

llm = Tongyi(model_name="qwen-plus",temperature=1)

physics_prompt = PromptTemplate(
    template="你是一个物理专家，请回答以下问题：\n{input}",
    input_variables=["input"]
)

math_prompt = PromptTemplate(
    template="你是一个数学专家，请回答以下问题：\n{input}",
    input_variables=["input"]
)

destination_chains = {
    "physics": physics_prompt | llm,
    "math": math_prompt | llm,
}

default_chain = PromptTemplate.from_template("请回答以下问题：{input}") | llm

def run_router_chain(question:str) -> str:
    chain_name = get_relevant_chain_name(question)
    if chain_name in destination_chains:
        return destination_chains[chain_name].invoke(question)
    else:
        return default_chain(question)

result = run_router_chain("牛顿第一定律是什么？")
print(result)