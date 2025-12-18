from langchain_community.chat_models import ChatTongyi
from dotenv import load_dotenv
import os

load_dotenv()

# 打印环境变量是否设置
print(f"DASHSCOPE_API_KEY is set: {os.getenv('DASHSCOPE_API_KEY') is not None}")

# 尝试使用不同的模型名称
model_names = ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-vl-plus"]

for model_name in model_names:
    try:
        print(f"\nTrying model: {model_name}")
        llm = ChatTongyi(
            model_name=model_name,
            temperature=0.7,
            streaming=True
        )
        # 尝试简单调用
        response = llm.invoke("你好，测试一下")
        print(f"Success! Response: {response}")
        break
    except Exception as e:
        print(f"Error: {e}")
