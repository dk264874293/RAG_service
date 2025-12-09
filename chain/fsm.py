'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2025-12-08 15:10:51
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2025-12-08 21:33:45
FilePath: /RAG_service/chain/fsm.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from langchain_community.llms import Tongyi
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from enum import Enum
from typing import Dict, List ,Any , Optional
import json
from dotenv import load_dotenv

load_dotenv()

class OrderState(Enum):
    START = "开始"
    ORDER_VALIDATED = "订单已验证"
    PAYMENT_CHECKED = "付款状态已检查"
    PAYMENT_PROCESSED = "付款已处理"
    INVOICE_GENERATED = "发票已开具"
    END = "结束"
    ERROR = "错误"

class OrderProcessGraph:
    def __init__(self):
        self.current_state = OrderState.START
        self.context = {}
        self.history = []

        # Mock 数据
        self.orders = {
            "ORD001": {
                "customer": "张三",
                "product": "iPhone 15", 
                "amount": 7999,
                "date": "2024-01-10",
                "payment_status": "未付款"
            },
            "ORD002": {
                "customer": "李四",
                "product": "MacBook Pro",
                "amount": 15999, 
                "date": "2024-01-08",
                "payment_status": "未付款"
            },
            "ORD003": {
                "customer": "王五",
                "product": "iPad Air",
                "amount": 4999,
                "date": "2024-01-12", 
                "payment_status": "已付款"
            }
        }

        self.llm = None
        try:
            self.llm = Tongyi(
                temperature=0,
                model_name="gwen-plus",
                # dashscope_api_key=os.getenv("DASHSCOPE_API_KEY")
            )
        except Exception as e:
            print(f"初始化LLM时出错: {e}")

    def add_to_history(self,from_state:OrderState,to_state:OrderState,action: str, result: str):
        self.history.append({
            'from': from_state.value,
            'to': to_state.value,
            'action': action,
            'result': result
        })

    def generate_message_with_llm(self, template_str: str, variables:Dict) -> str:
        if not self.llm:
            return template_str.format(**variables)

        try:
            prompt = PromptTemplate.from_template(template_str + " 请生成一个专业简洁的确认消息。")
            chain = prompt | self.llm | StrOutputParser()
            return chain.invoke(variables)
        except Exception as e:
            print(f"LLM调用出错: {e}")
            return template_str.format(**variables)

    def validate_order_node(self,order_number:str) -> Dict[str, Any]:
        """验证订单节点"""
        print(f"  执行节点: validate_order_node")
        print(f"  当前状态: {self.current_state.value}")

        if self.current_state != OrderState.START:
            message = f"错误：当前状态为{self.current_state.value},无法验证订单"
            return {
                "success": False,
                "message": message,
                'next_state': OrderState.ERROR
            }
        if order_number in self.orders:
            order_info = self.orders[order_number]
            self.context.update({
                "order_number": order_number,
                "order_info": order_info
            })

            # 使用LangChain 生成消息
            template = "订单验证成功！订单号: {order_number}, 客户: {customer}, 商品: {product}, 金额: {amount}元"
            message = self.generate_message_with_llm(template,{
                'order_number': order_number,
                'customer': order_info['customer'],
                'product': order_info['product'],
                'amount': order_info['amount']
            })

            self.add_to_history(
                self.current_state,
                OrderState.ORDER_VALIDATED,
                "验证订单",
                message
            )

            self.current_state = OrderState.ORDER_VALIDATED

            return {
                "success": True,
                "message": message,
                'next_state': OrderState.ORDER_VALIDATED
            }
        else:
            message = f"订单号 {order_number} 不存在"
            self.add_to_history(self.current_state, OrderState.ERROR, "验证订单", message)
            self.current_state = OrderState.ERROR
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

    def check_payment_node(self) -> Dict[str,Any]:
        """检查付款节点"""
        print(f"当前节点: check_payment_node")
        print(f"当前状态:{self.current_state.value}")

        if self.current_state != OrderState.ORDER_VALIDATED:
            message = f"错误：当前节点为{self.current_state.value}，无法进行付款操作"
            return {
                "success": false,
                "message": message,
                'next_state':OrderState.ERROR
            }
        
        order_info = self.context.get("order_info",{})
        payment_status = order_info.get('payment_status', '未付款')
        
        if payment_status == '已付款':
            template = "付款状态检查完成：订单已付款，可以直接开具发票"
            message = self.generate_message_with_llm(template, {})
            self.context['payment_confirmed'] = True
            next_state = OrderState.PAYMENT_PROCESSED
        else:
            template = "付款状态检查完成：订单未付款，需要先处理付款"
            message = self.generate_message_with_llm(template, {})
            self.context['payment_confirmed'] = False
            next_state = OrderState.PAYMENT_CHECKED

        self.add_to_history(
            self.current_state,
            next_state,
            "检查付款状态",
            message
        )
        self.current_state = next_state

        return {
            'success': True,
            'message': message,
            'next_state': next_state,
            'payment_status': payment_status
        }

    def process_payment_node(self, payment_method: str = "支付宝") -> Dict[str, Any]:
        """处理付款节点"""
        print(f"当前节点: process_payment_node")
        print(f"当前状态:{self.current_state.value}")

        if self.current_state != OrderState.PAYMENT_CHECKED:
            message = f"错误：当前状态为 {self.current_state.value}，无法处理付款"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        order_info = self.context.get("order_info",{})
        amount = order_info.get("amount", 0)
        order_number = self.context.get("order_number", "000")

        template = '付款处理完成！付款金额: {amount}元，付款方式: {payment_method}，交易号: TXN{order_number}-2024'

        message = self.generate_message_with_llm(template,{
            "amount": amount,
            "payment_method": payment_method,
            "order_number": order_number
        })

        self.context.update({
            'payment_amount': amount,
            'payment_method': payment_method,
            'transaction_id': f"TXN{order_number}-2024",
            'payment_confirmed': True
        })

        self.add_to_history(self.current_state,OrderState.PAYMENT_PROCESSED,"处理付款", message)

        self.current_state = OrderState.PAYMENT_PROCESSED

        return {
            "success": True,
            "message": message,
            'next_state': OrderState.PAYMENT_PROCESSED
        }

    def generate_invoice_node(self, invoice_type:str = "电子发票") -> Dict[str, Any]:
        """开局发票节点"""
        print(f"当前节点: generate_invoice_node")
        print(f"当前状态:{self.current_state.value}")

        if self.current_state != OrderState.PAYMENT_PROCESSED:
            message = f"错误：当前状态为 {self.current_state.value}，无法开具发票。必须先完成付款处理"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        order_info = self.context.get("order_info",{})
        amount = order_info.get("amount", 0)
        order_number = self.context.get("order_number", "000")
        invoice_number = f"INV{order_number}-2024"

        template = "发票开具完成！发票号: {invoice_number}，金额: {amount}元，类型: {invoice_type}"

        message = self.generate_message_with_llm(template,{
            "invoice_number": invoice_number,
            "amount": amount,
            "invoice_type": invoice_type
        })

        self.context.update({
            'invoice_number': invoice_number,
            'invoice_amount': amount,
            'invoice_type': invoice_type,
            'invoice_status': '已开具'
        })

        self.add_to_history(self.current_state, OrderState.INVOICE_GENERATED,'开具发票', message)

        self.current_state = OrderState.INVOICE_GENERATED

        return {
            "success": True,
            "message": message,
            'next_state': OrderState.INVOICE_GENERATED
        }

    def end_node(self) -> Dict[str,Any]:
        """结束节点"""
        print(f"  执行节点: end_node")
        print(f"  当前状态:{self.current_state.value}")

        if self.current_state != OrderState.INVOICE_GENERATED:
            message = f"错误：当前状态为{self.current_state.value}, 流程未完成"
            return {
                'success': False,
                'message': message,
                'next_state': OrderState.ERROR
            }

        template = '订单处理流程已完成，所有步骤执行成功'

        message = self.generate_message_with_llm(template, {})

        self.add_to_history(self.current_state, OrderState.END, '结束节点', message)

        self.current_state = OrderState.END

        return {
            "success": True,
            "message": message,
            'next_state': OrderState.END
        }

    def should_process_payment(self) -> bool:
        """判断是否需要处理付款"""
        return not self.context.get('payment_confirmed', False)

    def get_status(self) -> str:
        """获取当前状态"""
        """获取当前状态"""
        result = f"""
当前状态: {self.current_state.value}
流程上下文: {json.dumps(self.context, ensure_ascii=False, indent=2)}
"""
        
        if self.history:
            result += f"\n状态转换历史:\n"
            for i, step in enumerate[Any](self.history, 1):
                result += f"  {i}. {step['from']} → {step['to']} ({step['action']})\n"
        
        return result

    def reset(self):
        """重置状态机"""
        self.current_state = OrderState.START
        self.context = {}
        self.history = []

class OrderProcessExecutor:
    def __init__(self):
        self.graph = OrderProcessGraph()

    def execute_workflow(self, order_number: str, payment_method: str = "支付宝", invoice_type: str = "电子发票"):
        """执行完整的工作流程"""
        print(f"=== 开始处理订单 {order_number} ===\n")
        
        # 步骤1: 验证订单
        print("步骤1: 验证订单")
        result1 = self.graph.validate_order_node(order_number)
        print(f"结果: {result1['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")
        
        if not result1['success']:
            return result1
        
        # 步骤2: 检查付款状态
        print("步骤2: 检查付款状态")
        result2 = self.graph.check_payment_node()
        print(f"结果: {result2['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")
        
        if not result2['success']:
            return result2
        
        # 条件分支：如果未付款，则处理付款
        if self.graph.should_process_payment():
            print("步骤3: 处理付款")
            result3 = self.graph.process_payment_node(payment_method)
            print(f"结果: {result3['message']}")
            print(f"状态转换: {self.graph.current_state.value}\n")
            
            if not result3['success']:
                return result3
        else:
            print("步骤3: 跳过付款处理（订单已付款）")
            print(f"当前状态保持: {self.graph.current_state.value}\n")
        
        # 步骤4: 开具发票
        print("步骤4: 开具发票")
        result4 = self.graph.generate_invoice_node(invoice_type)
        print(f"结果: {result4['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")
        
        if not result4['success']:
            return result4
        
        # 步骤5: 结束流程
        print("步骤5: 结束流程")
        result5 = self.graph.end_node()
        print(f"结果: {result5['message']}")
        print(f"状态转换: {self.graph.current_state.value}\n")
        
        return result5

    def get_status(self):
        return self.graph.get_status()

    def reset(self):
        self.graph.reset()


def demo_fsm_langchain_complete():
    """演示完整的LangChain集成FSM实现"""
    print("=== 基于状态机的订单处理系统（LangChain完整版） ===\n")
    
    executor = OrderProcessExecutor()

    print("--- 演示1: 未付款订单的完整流程 ---")
    result1 = executor.execute_workflow("ORD001", "微信支付", "增值税专用发票")

    print("--- 最终状态 ---")
    print(executor.get_status())
    print("="*80 + "\n")

    # 演示2: 已付款订单的流程
    print("--- 演示2: 已付款订单的流程 ---")
    executor.reset()
    result2 = executor.execute_workflow("ORD003", "支付宝", "电子普通发票")
    
    print("--- 最终状态 ---")
    print(executor.get_status())
    print("="*80 + "\n")

if __name__ == "__main__":
    demo_fsm_langchain_complete()