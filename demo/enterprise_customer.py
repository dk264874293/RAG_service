'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-02 13:20:28
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-02 14:19:31
FilePath: /RAG_service/demo/enterprise_customer.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from langchain_core.prompts import PromptTemplate
from langchain_community.llms import Tongyi
from langchain_core.output_parsers import BaseOutputParser
from trying import  Dict, List ,Optional

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
        return """请以JSON格式回复："""



class EnterpriseCustomerService:
    """企业级客服系统"""
    def __init__(self):
        self.setup_models()
        self.setup_chains()
        self.setup_fallback_system()
        self.performance_stats = {    # 性能统计
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "average_response_time": 0.0
        }

    def setup_models(self):
        """设置模型"""
        self.primary_model = Tongyi(
            model_name="qwen-max",
            temperature=0.3,
            max_tokens=500
        )
        self.backup_model = Tongyi(
            model_name="qwen-plus",
            temperature=0.3,
            max_tokens=500
        )

    def setup_chains(self):
        """设置链"""
        self.parser = CustomerServiceResponse()
        # 技术问题处理
        tech_prompt = PromptTemplate(
            input_variables=["question","user_info"],
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
        def create_fallback_chain(primary_chain,chain_name):
            def fallback_processor(input_data):
                try:
                    return primary_chain(input_data)
                except Exception as e:
                    logger.error(f"${chain_name} 主链调用失败尝试备用模型：{e}")
                    try:
                        backup_chain = primary_chain.first | self.backup_model | self.parser
                        return backup_chain(input_data)
                    except Exception as e:
                        print(f"{chain_name}备用链调用失败：{e},使用简单响应")
                        return {
                            "response": "抱歉，系统暂时繁忙，请稍后重试或联系人工客服。",
                            "category": "system_error",
                            "confidence": 1.0,
                            "requires_human": True
                        }

            return fallback_processor
        # 为每个链添加回退机制
        self.tech_chain_with_fallback = create_fallback_chain(self.tech_chain, "技术支持")
        self.billing_chain_with_fallback = create_fallback_chain(self.billing_chain, "账单服务")
        self.general_chain_with_fallback = create_fallback_chain(self.general_chain, "通用服务")

        # 创建智能路由分支
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
