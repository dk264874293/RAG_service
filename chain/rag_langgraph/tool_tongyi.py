import importlib.util
import os
from typing import TypeDict, Dict, Callable

def tool(name:str,description:str = ""):
    def decorator(func):
        func.is_tool = True
        func.tool_name = name
        func.description = description
        return func
    return decorator

def load_tools_from_directory(tools_dir: str) -> Dict[str, Callable]:
    """
    动态工具加载器 - 运行时扫描目录
    与静态加载的核心区别
    """
    tools = {}

    # 检查目录是否存在
    if not os.path.exists(tools_dir):
        print(f" 工具目录不存在: {tools_dir}")
        return tools

    print(f"扫描工具目录：{tools_dir}")

    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and not filename.startswith("__"):
            file_path = os.path.join(tool_dir, filename)
            module_name = filename[:-3]

            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 扫描模块中的工具函数
                for attr_name in dir(module):
                    obj = getattr(module, attr_name)
                    if hasattr(obj, "is_tool"):
                        tools[obj.tool_name] = obj
                        print(f" 发现工具: {obj.tool_name} ({obj.description})")
            except Exception as e:
                print(f" 加载工具模块 {module_name} 失败: {e}")

    return tools

def load_customer_tools(customer_id:str, base_dir: str ="customers") -> Dict[str, Callable]:
    """
    为特定客户动态加载工具 - 真实业务场景
    """
    customer_tools_dir = os.path.join(base_dir, customer_id, "tools")
    print(f" 为客户 {customer_id} 加载专属工具...")
    return load_tools_from_directory(customer_tools_dir)

def load_tools_by_config(config:dict) -> Dict[str, Callable]:
    """
    根据配置动态加载工具 - 支持 A/B 测试
    """
    tools = {}

    for tool_config in config.get('enabled_tools', []):
        tools_dir = tool_config["directory"]
        enabled_tools = tool_config.get("tools", [])

        dir_tools = load_tools_from_directory(tools_dir)

        if enabled_tools:
            for tool_name in enabled_tools:
                if tool_name in dir_tools:
                    tools[tool_name] = dir_tools[tool_name]
        else:
            tools.update(dir_tools)

    return tools

class AgentState(TypeDict):
    task: str
    tools: dict
    result: str
    customer_id: str

def dynamic_load_tools_node(state: AgentState) -> AgentState:
    """
    动态加载工具节点 - 核心区别
    """
    customer_id = state.get("customer_id", "default")

    # 通用工具目录加载，运行时扫描
    general_tools = load-tools_from_directory("tools/")

    # 从客户专属目录加载
    customer_tools = load_tools_by_config(customer_id)

    # 根据配置加载
    config = {
        "enabled_tools": [
            {
                "directory": "tools/",
                "tools": ["calculator", "text_processor"]
            },
            {
                "directory": f"customers/{customer_id}/tools/"
            }
        ]
    }

    config_tools = load_tools_by_config(config)

    all_tools = {}
    all_tools.update(general_tools)
    all_tools.update(customer_tools)
    all_tools.update(config_tools)

    state["tools"] = all_tools
    print(f" 动态加载完成，共 {len(all_tools)} 个工具: {list(all_tools.keys())}")
    
    return state

def hot_reload_tools(state:AgentState) -> AgentState:
    """
    热重载工具 - 无需重启即可更新工具
    """
    print(" 执行热重载...")
    return dynamic_load_tools_node(state)

# 运行演示
def run_dynamic_agent(task:str, customer_id:str = "default"):
    state = AgentState(
        task=task,
        tools={},
        result="",
        customer_id=customer_id,
    )
    print(f" 启动动态 Agent (客户: {customer_id})")
    print("=" * 50)

    state = dynamic_load_tools_node(state)

    if state["tools"]:
        tool_name = list(state["tools"].keys())[0]
        print(f"使用工具： {tool_name}")
        state["result"] = f"使用 {tool_name} 处理任务: {task}"
    else:
        state["result"] = "未加载到任何工具"
    return state

if __name__ == "__main__":
    # 创建示例工具文件内容（实际使用时这些应该是独立文件）
    print(" 模拟工具目录结构:")
    print("tools/")
    print("├── math_tools.py")
    print("├── text_tools.py") 
    print("customers/")
    print("├── customer_a/tools/")
    print("└── customer_b/tools/")
    print()
    
    # 运行演示
    result = run_dynamic_agent("处理数据", "customer_a")
    print(f"\n 最终结果: {result['result']}")