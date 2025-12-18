import asyncio
import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import HandoffTermination, MaxMessageTermination
from autogen_core import CancellationToken
from autogen_agentchat.ui import Console
from autogen_agentchat.messages import HandoffMessage

load_dotenv()

model_info_qwen_plus = {
    "model_name": "qwen-plus", 
    "family": "qwen",
    "context_length": 32000,
    "vision": False,
    "function_calling": True,
    "json_output": True,
    "structured_output": True
}

model_client = OpenAIChatCompletionClient(
    model="qwen-plus",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    model_info=model_info_qwen_plus,
    parallel_tool_calls = False
)

async def main() -> None:
    try:
        agent1 = AssistantAgent(
            "Assistant_1",
            model_client=model_client,
        )
        agent2=AssistantAgent("Assistant_2", model_client=model_client)

        termination = MaxMessageTermination(10)

        team = RoundRobinGroupChat(
            [agent1, agent2],
            termination_condition=termination,
        )
        
        print("开始第一次计算任务...")
        try:
            result_1 = await team.run(task="计算以下应用题，并每次返回一步计算过程：苹果比橘子多24个并且苹果是橘子的三倍，请问苹果和橘子的数量分别是多少？")
            print("第一次任务结果:", result_1)
        except asyncio.exceptions.CancelledError as ce:
            print("第一次任务被取消:", ce)
        except Exception as e:
            print("第一次任务发生错误:", type(e).__name__, str(e))

        # 模拟超时取消
        print("\n开始第二次计算任务（带取消）...")
        cancellation_token = CancellationToken()

        run_task = asyncio.create_task(
            team.run(
                task="计算以下应用题，并每次返回一步计算过程：苹果比橘子多24个并且苹果是橘子的三倍，请问苹果和橘子的数量分别是多少？",
                cancellation_token=cancellation_token,
            )
        )
        # 等待1秒后取消任务
        await asyncio.sleep(1)
        print("取消第二次任务...")
        cancellation_token.cancel()

        try:
            # 这将引发取消错误
            result_2 = await run_task
            print("第二次任务结果:", result_2)
        except asyncio.exceptions.CancelledError as ce:
            print("第二次任务被取消（预期行为）:", ce)
        except Exception as e:
            print("第二次任务发生错误:", type(e).__name__, str(e))

    except asyncio.exceptions.CancelledError as ce:
        print("主函数被取消:", ce)
    except Exception as e:
        print("主函数发生错误:", type(e).__name__, str(e))
    finally:
        print("程序结束")




    # result = await team.run(task="从1数到10，每次回答一个。")

    # print(result)

    

asyncio.run(main())