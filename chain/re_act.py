# 导入依赖
'''
物流场景 ReACT Agent
使用 ReAct 框架实现物流查询、运费计算、库存查询等功能
'''
import sys
import types

# 创建一个模拟的langchain模块来解决langchain.verbose和langchain.debug问题
mock_langchain = types.ModuleType('langchain')
mock_langchain.verbose = False
mock_langchain.debug = False
sys.modules['langchain'] = mock_langchain

from langchain_community.llms import Tongyi
from langchain_classic.agents import create_react_agent
from langchain_classic.agents import AgentExecutor
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from dotenv import load_dotenv
import logging

# 初始化环境变量
load_dotenv()

# 物流场景mock工具

def track_package(tracking_number: str) -> str:
    """物流单号查询工具，输入物流单号，返回物流信息"""
    if tracking_number == "SF123456":
        return "当前物流信息: [2024-05-20 10:30] 已签收，签收人: 张三；[2024-05-20 08:45] 正在派送中；[2024-05-19 15:30] 到达目的地城市；[2024-05-18 10:00] 包裹已发出"
    return f"未找到物流单号 {tracking_number} 的信息"

def calculate_shipping_cost(params: str) -> str:
    """计算运费，输入出发地,目的地,重量(kg)，返回运费"""
    try:
        origin, destination, weight = params.split(",")
        weight = float(weight)
        if origin in ["北京", "上海", "广州", "深圳"] and destination in ["北京", "上海", "广州", "深圳"]:
            cost = weight * 10 + 15
        else:
            cost = weight * 12 + 20
        return f"从{origin}到{destination}，重量{weight}kg的运费为: {cost}元"
    except Exception:
        return "参数格式错误，请输入'出发地,目的地,重量(kg)'格式"

def check_inventory(product_id: str) -> str:
    """查询库存，输入产品ID，返回库存数量"""
    inventory = {
        "A001": 150,
        "B002": 30,
        "C003": 0,
        "D004": 200
    }
    if product_id in inventory:
        return f"产品 {product_id} 的库存数量为: {inventory[product_id]}"
    return f"未找到产品 {product_id} 的库存信息"

# 主函数
def main():
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=== 物流 ReACT Agent===")
    
    try:
        # 1. 创建工具列表
        # 定义可用工具
        tools = [
            Tool(
                name="track_package",
                func=track_package,
                description="物流单号查询工具，输入物流单号，返回物流信息，例如：SF123456"
            ),
            Tool(
                name="calculate_shipping_cost",
                func=calculate_shipping_cost,
                description="计算运费，输入'出发地,目的地,重量(kg)'格式，例如：北京,上海,2"
            ),
            Tool(
                name="check_inventory",
                func=check_inventory,
                description="查询库存，输入产品ID，返回库存数量，例如：A001"
            )
        ]

        # 2. 定义ReACT提示模板
        react_prompt_template = """你是一个专业的物流咨询助手，需要根据用户问题，利用可用工具来帮助用户解答。

可用工具：
{tools}

使用以下格式回答：

Question: 你需要回答的输入问题
Thought: 你应该始终思考下一步要做什么
Action: 要执行的操作，必须是 [{tool_names}] 之一
Action Input: 操作的输入
Observation: 操作的结果
... (这个Thought/Action/Action Input/Observation可以重复N次)
Thought: 我现在知道最终答案了
Final Answer: 对原始输入问题的最终答案

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        # 3. 创建提示模板
        prompt = PromptTemplate(
            template=react_prompt_template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={"tools": "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])},
        )

        # 4. 初始化Tongyi模型和create_react_agent
        model = Tongyi(temperature=0)
        agent = create_react_agent(model, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3,
            return_intermediate_steps=True
        )
        
        # 测试案例
        test_cases = [
            "查询快递单号 SF123456",
            "从北京到上海寄2公斤包裹多少钱", 
            "查询商品A001的库存"
        ]

        for i, question in enumerate(test_cases, 1):
            print(f"--- 测试案例 {i} ---")
            print(f"问题: {question}")
            print("-" * 50)
            
            try:
                result = agent_executor.invoke({"input": question})
                print(f"\n最终答案: {result.get('output', '无结果')}")
                
                # 显示中间步骤
                if 'intermediate_steps' in result:
                    print(f"执行步骤数: {len(result['intermediate_steps'])}")
                    
            except Exception as e:
                print(f"Agent执行错误: {e}")
                
                # 提供备选答案，确保用户能看到正确结果
                print("\n使用直接工具调用作为备选:")
                if i == 1:  # 查询快递单号
                    backup_result = track_package("SF123456")
                    print(f"备选答案: {backup_result}")
                elif i == 2:  # 计算运费
                    backup_result = calculate_shipping_cost("北京,上海,2")
                    print(f"备选答案: {backup_result}")
                elif i == 3:  # 查询库存
                    backup_result = check_inventory("A001")
                    print(f"备选答案: {backup_result}")
            
            print("\n" + "="*60 + "\n")
            
    except Exception as e:
        print(f"初始化错误: {e}")
        print("请确保已设置 DASHSCOPE_API_KEY 环境变量")

# 执行主函数
if __name__ == "__main__":
    main()