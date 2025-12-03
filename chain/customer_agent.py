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
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableBranch, RunnableLambda, RunnableSequence
from langchain_community.llms import Tongyi
from typing import Dict, List, Optional
import json
import time
import logging
from dotenv import load_dotenv
from utils.request_backoff import retry_with_backoff, timeout_handler

load_dotenv()
# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerServiceResponse(BaseOutputParser[Dict]):
    """客服响应解析器"""
    def parse(self, text: str) -> Dict:
        """解析输出"""
        try:
            # 尝试解析JSON格式
            if '{' in text and '}' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                json_str = text[start:end]
                return json.loads(json_str)
            
            # 如果不是JSON，返回简单格式
            return {
                "response": text.strip(),
                "category": "general",
                "confidence": 0.8,
                "requires_human": False
            }
        except json.JSONDecodeError:
            raise OutputParserException(f"解析失败: {e}")
    def get_format_instructions(self) -> str:
         return """请以JSON格式回复：
            {
            "response": "回复内容",
            "category": "问题类别(technical/billing/general)",
            "confidence": 0.9,
            "requires_human": false
        }"""

   

class EnterpriseCustomerService:
    def __init__(self):
        self.setup_models()
        self.setup_chain()
        self.setup_fallback_system()
        self.performance_stats = {    # 性能统计
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }

    def setup_models(self):
        self.primary_model = Tongyi(
            model_name="qwen-max",
            temperature=0.3,
            max_tokens=500
        )

        self.backup_model = Tongyi(
            model_name="qwen-plus",
            temperature=0.7,
            max_tokens=500
        )

    def setup_chain(self):
        self.parser = CustomerServiceResponse()
         
        # 技术问题处理链
        tech_prompt = PromptTemplate(
            input_variables=["question", "user_info"],
            template="""你是技术支持专家，请回答用户的技术问题。

                用户信息：{user_info}
                问题：{question}

                {format_instructions}

                请提供专业的技术解答。""",
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # 账单问题处理链
        billing_prompt = PromptTemplate(
            input_variables=["question", "user_info"],
            template="""你是账单客服专员，请处理用户的账单相关问题。

            用户信息：{user_info}
            问题：{question}

            {format_instructions}

            请提供准确的账单信息和解决方案。""",
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # 通用问题处理链
        general_prompt = PromptTemplate(
            input_variables=["question", "user_info"],
            template="""你是客服代表，请友好地回答用户问题。

        用户信息：{user_info}
        问题：{question}

        {format_instructions}

        请提供有帮助的回复。""",
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        
        # 创建处理链
        self.tech_chain = tech_prompt | self.primary_model | self.parser
        self.billing_chain = billing_prompt | self.primary_model | self.parser
        self.general_chain = general_prompt | self.primary_model | self.parser
    
    def setup_fallback_system(self):
        """设置容错系统"""
        
        # 创建带有回退机制的处理函数
        def create_fallback_chain(primary_chain, chain_name):
            def fallback_processor(input_data):
                try:
                    # 第一层：主要链处理
                    return primary_chain.invoke(input_data)
                except Exception as e:
                    logger.warning(f"{chain_name} 主链失败，尝试备用模型: {e}")
                    try:
                        # 第二层：备用模型处理
                        backup_chain = primary_chain.first | self.backup_model | self.parser
                        return backup_chain.invoke(input_data)
                    except Exception as e2:
                        logger.error(f"{chain_name} 备用模型失败，使用简单响应: {e2}")
                        # 第三层：简单响应
                        return {
                            "response": "抱歉，系统暂时繁忙，请稍后重试或联系人工客服。",
                            "category": "system_error",
                            "confidence": 1.0,
                            "requires_human": True
                        }
            
            return RunnableLambda(fallback_processor)
        
        # 为每个链添加回退机制
        self.tech_chain_with_fallback = create_fallback_chain(self.tech_chain, "技术支持")
        self.billing_chain_with_fallback = create_fallback_chain(self.billing_chain, "账单服务")
        self.general_chain_with_fallback = create_fallback_chain(self.general_chain, "通用服务")
        # 建智能路由分支
        self.smart_router = RunnableBranch(
            (self._is_technical_question, self.tech_chain_with_fallback),
            (self._is_billing_question, self.billing_chain_with_fallback),
            self.general_chain_with_fallback  # 默认分支
        )
    
    def _is_technical_question(self, x: Dict) -> bool:
        """判断是否为技术问题"""
        question = x.get("question", "").lower()
        tech_keywords = ["bug", "错误", "故障", "技术", "API", "代码", "系统", "登录", "密码"]
        return any(keyword in question for keyword in tech_keywords)
    
    def _is_billing_question(self, x: Dict) -> bool:
        """判断是否为账单问题"""
        question = x.get("question", "").lower()
        billing_keywords = ["账单", "费用", "付款", "充值", "退款", "价格", "订单"]
        return any(keyword in question for keyword in billing_keywords)
    
    @retry_with_backoff(max_attempts=3,base_delay=1.0)
    @timeout_handler(time_seconds = 30.0)
    def _process_with_retry_and_timeout(self, input_data:Dict) -> Dict:
        return self.smart_router.invoke(input_data)

        
    def process_customer_inquiry(self,question:str,user_info:Dict) -> Dict:
        start_time = time.time()
        self.performance_stats["total_requests"] += 1
        try:
            logger.info(f"处理客户咨询: {question[:50]}...")
            input_data = {
                "question": question,
                "user_info": json.dumps(user_info, ensure_ascii=False)
            }
            result = self._process_with_retry_and_timeout(input_data)

            # 添加处理时间和状态
            processing_time = round(time.time() - start_time, 2)
            result["processing_time"] = processing_time
            result["status"] = "success"
            
            # 更新性能统计
            self.performance_stats["successful_requests"] += 1
            self._update_average_response_time(processing_time)
            
            logger.info(f"处理完成，耗时: {processing_time}秒")

            return result
        except Exception as e:
            processing_time = round(time.time() - start_time, 2)
            self.performance_stats["failed_requests"] += 1
            
            logger.error(f"处理失败: {e}")
            return {
                "response": "系统出现异常，请联系技术支持。",
                "category": "system_error",
                "confidence": 0.0,
                "requires_human": True,
                "status": "error",
                "error": str(e),
                "processing_time": processing_time
            }

    def _update_average_response_time(self, new_time: float):
        """更新平均响应时间"""
        total_successful = self.performance_stats["successful_requests"]
        current_avg = self.performance_stats["average_response_time"]
        
        # 计算新的平均值
        new_avg = ((current_avg * (total_successful - 1)) + new_time) / total_successful
        self.performance_stats["average_response_time"] = round(new_avg, 2)

    def batch_process_inquiries(self, inquiries:List[Dict]) -> List[Dict]:
        """批处理查询"""
        logger.info(f"开始批处理{len(inquiries)}个查询")
        results = []
        for inquiry in inquiries:
            result = self.process_customer_inquiry(inquiry['question'], inquiry['user_info'])
            results.append(result)
        logger.info(f"批处理完成，共处理{len(results)}个查询")
        return results

    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        stats = self.performance_stats.copy()
        if stats["total_requests"] > 0:
            stats["success_rate"] = round(
                (stats["successful_requests"] / stats["total_requests"]) * 100, 2
            )
        else:
            stats["success_rate"] = 0.0
        
        return stats
