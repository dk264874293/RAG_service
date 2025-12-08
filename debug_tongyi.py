import traceback
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 尝试导入并初始化Tongyi模型
try:
    print("正在导入Tongyi模型...")
    from langchain_community.llms import Tongyi
    print("Tongyi模型导入成功")
    
    # 尝试初始化模型
    print("正在初始化Tongyi模型...")
    model = Tongyi(temperature=0)
    print("Tongyi模型初始化成功")
    
    # 尝试检查模型属性
    print(f"模型配置: {model.__dict__}")
    
except Exception as e:
    print(f"发生错误: {type(e).__name__}: {e}")
    print("错误堆栈:")
    traceback.print_exc()
    sys.exit(1)