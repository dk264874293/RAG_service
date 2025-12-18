'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-18 15:58:43
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-18 17:21:31
FilePath: /RAG_service/chain/crewai/test.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEfrom langchain.chat_models
'''
import os
from crewai import Agent, Task, Crew, LLM
# from langchain_community.llms import Tongyi 
# from langchain_community.chat_models import ChatTongyi
# from langchain.chat_models import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# llm = ChatTongyi(
#     model_name="qwen-turbo",
#     temperature=0.7,
#     streaming=True
# )

llm = LLM(
    model="qwen-plus", 
    temperature=0.7, 
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY")
)

# 创建智能体
researcher = Agent(
    role='市场研究员',
    goal='深入研究市场趋势和竞争对手',
    backstory='你是一位经验丰富的市场研究员,擅长收集和分析市场数据。',
    verbose=True,
    llm=llm
)

strategist = Agent(
    role='商业策略师',
    goal='制定有效的商业策略',
    backstory='你是一位资深商业策略师,擅长制定创新的商业计划。',
    verbose=True,
    llm=llm
)

writer = Agent(
    role='商业计划撰写人',
    goal='撰写清晰、详细的商业计划',
    backstory='你是一位专业的商业计划撰写人,擅长将复杂的信息转化为易于理解的文档。',
    verbose=True,
    llm=llm
)

# 定义任务
task1 = Task(
    description='进行简要市场研究,分析目标市场的主要特征和主要竞争对手。',
    agent=researcher,
    expected_output="一份简洁的市场研究报告,包括市场主要特征和主要竞争对手。"
)

task2 = Task(
    description='基于市场研究结果,制定7天的初步商业策略,包括产品定位和主要营销方向。',
    agent=strategist,
    expected_output="一份7天的初步商业策略计划,包括产品定位和主要营销方向。"
)

task3 = Task(
    description='将研究结果和策略整合成一份简要的7天商业计划概要。',
    agent=writer,
    expected_output="一份简要的7天商业计划概要,包括市场分析要点和主要策略方向。"
)

# 创建Crew
crew = Crew(
    agents=[researcher, strategist, writer],
    tasks=[task1, task2, task3],
    verbose=True
)

result = crew.kickoff()

print("最终的7天商业计划概要：")
print(result)
