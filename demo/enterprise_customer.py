'''Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-02 13:20:28
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-02 15:06:11
FilePath: /RAG_service/demo/enterprise_customer.py
Description: 简化版本，移除langchain依赖以测试utils模块导入和装饰器功能
'''
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chain.customer_agent import EnterpriseCustomerService


def demo_enterprise_application():
    print("=== 企业级 LangChain 客服系统演示 ===")
    
    # 初始化系统
    customer_service = EnterpriseCustomerService()
    
    # 测试用例
    test_cases = [
        {
            "question": "我的API调用出现500错误，怎么解决？",
            "user_info": {"user_id": "12345", "plan": "企业版", "region": "北京"}
        },
        {
            "question": "我想查看本月的账单详情",
            "user_info": {"user_id": "67890", "plan": "标准版", "region": "上海"}
        },
        {
            "question": "你们的服务怎么样？",
            "user_info": {"user_id": "11111", "plan": "免费版", "region": "深圳"}
        }
    ]
    
    # 单个处理演示
    print("\n--- 单个处理演示 ---")
    for i, case in enumerate(test_cases, 1):
        print(f"\n客户咨询 {i}:")
        print(f"问题: {case['question']}")
        print(f"用户信息: {case['user_info']}")
        
        result = customer_service.process_customer_inquiry(
            case["question"], 
            case["user_info"]
        )
        
        print(f"回复: {result['category']} - {result['response'][:100]}...")
     # 批量处理演示
    print(f"\n--- 批量处理演示 ---")
    batch_results = customer_service.batch_process_inquiries(test_cases)
    
    print(f"批量处理了 {len(batch_results)} 个咨询")
    for i, result in enumerate(batch_results, 1):
        print(f"结果 {i}: {result['category']} - {result['response'][:50]}...")
    
    # 性能统计
    print(f"\n--- 性能统计 ---")
    stats = customer_service.get_performance_stats()
    print(f"总请求数: {stats['total_requests']}")
    print(f"成功请求数: {stats['successful_requests']}")
    print(f"失败请求数: {stats['failed_requests']}")
    print(f"成功率: {stats['success_rate']}%")
    print(f"平均响应时间: {stats['average_response_time']}秒")


if __name__ == "__main__":
    demo_enterprise_application()

