"""
公式计算验证器
执行数学公式计算，验证测量值的正确性
"""

import re
import logging
import math
from typing import Dict, Optional, Tuple
from ..models.compliance import CalculationResult, FormulaParameter

logger = logging.getLogger(__name__)


class FormulaCalculator:
    """公式计算器"""

    def __init__(self):
        """初始化计算器"""
        # 常用数学函数映射
        self.math_functions = {
            "log": math.log10,
            "ln": math.log,
            "sqrt": math.sqrt,
            "abs": abs,
            "pow": pow,
            "exp": math.exp,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
        }

        # 单位换算因子
        self.unit_conversions = {
            "g_to_mg": 1000,
            "kg_to_g": 1000,
            "L_to_mL": 1000,
            "mg/L_to_g/mL": 0.001,
        }

    def calculate(
        self,
        formula: str,
        parameters: Dict[str, float],
        result_unit: Optional[str] = None,
    ) -> CalculationResult:
        """
        根据公式和参数计算结果

        Args:
            formula: 计算公式（如"C=△W/V×10^6"）
            parameters: 参数字典（如{"△W": 0.123, "V": 100}）
            result_unit: 结果单位

        Returns:
            计算结果对象
        """
        try:
            # 标准化公式
            standardized_formula = self._standardize_formula(formula)

            # 构建计算表达式
            expression = self._build_expression(standardized_formula, parameters)

            # 安全计算
            calculated_value = self._safe_eval(expression)

            return CalculationResult(
                formula=formula,
                input_values=parameters,
                calculated_value=calculated_value,
                calculated_unit=result_unit,
                is_valid=True,
            )

        except Exception as e:
            logger.error(f"公式计算失败: formula={formula}, error={e}")
            return CalculationResult(
                formula=formula,
                input_values=parameters,
                calculated_value=0.0,
                calculated_unit=result_unit,
                is_valid=False,
            )

    def _standardize_formula(self, formula: str) -> str:
        """
        标准化公式格式

        转换：
        - "×" → "*"
        - "÷" → "/"
        - "10^6" → "10**6"
        - "△W" → "delta_W"
        - "ΔW" → "delta_W"

        Args:
            formula: 原始公式

        Returns:
            标准化后的公式
        """
        standardized = formula

        # 替换乘除符号
        standardized = standardized.replace("×", "*")
        standardized = standardized.replace("÷", "/")

        # 替换科学计数法
        standardized = re.sub(r"10\^(\d+)", r"10**\1", standardized)
        standardized = re.sub(r"10\*\*(\d+)", r"10**\1", standardized)
        standardized = re.sub(r"e([+-]?\d+)", r"e\1", standardized)

        # 替换希腊字母和特殊符号
        standardized = standardized.replace("△", "delta_")
        standardized = standardized.replace("Δ", "delta_")
        standardized = standardized.replace("Σ", "sum_")
        standardized = standardized.replace("∫", "integral_")

        # 提取目标变量（C=...）
        if "=" in standardized:
            parts = standardized.split("=")
            standardized = parts[1].strip()

        return standardized

    def _build_expression(self, formula: str, parameters: Dict[str, float]) -> str:
        """
        构建可执行的表达式

        Args:
            formula: 标准化后的公式
            parameters: 参数值字典

        Returns:
            可执行的表达式字符串
        """
        expression = formula

        # 替换参数值为实际值
        for param_name, param_value in parameters.items():
            # 标准化参数名
            standardized_param = param_name.replace("△", "delta_").replace(
                "Δ", "delta_"
            )
            expression = re.sub(
                rf"\b{re.escape(standardized_param)}\b", str(param_value), expression
            )

        return expression

    def _safe_eval(self, expression: str) -> float:
        """
        安全地计算表达式

        只允许基本数学运算和预定义的函数

        Args:
            expression: 数学表达式

        Returns:
            计算结果

        Raises:
            ValueError: 表达式非法
        """
        # 白名单检查：只允许数字、运算符、数学函数
        allowed_chars = set(
            "0123456789.+-*/()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
        )

        # 检查表达式中的每个字符
        for char in expression:
            if char not in allowed_chars:
                raise ValueError(f"非法字符: {char}")

        # 构建安全的环境
        safe_dict = {
            **self.math_functions,
        }

        try:
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return float(result)
        except Exception as e:
            raise ValueError(f"表达式计算错误: {e}")

    def verify_calculation(
        self,
        calculated_value: float,
        measured_value: float,
        tolerance_percent: float = 10.0,
    ) -> Tuple[bool, Optional[str]]:
        """
        验证计算值与测量值是否一致

        Args:
            calculated_value: 计算值
            measured_value: 测量值
            tolerance_percent: 允许的误差百分比

        Returns:
            (是否通过验证, 错误消息)
        """
        if measured_value == 0:
            return False, "测量值为0"

        # 计算相对误差
        relative_error = (
            abs(calculated_value - measured_value) / abs(measured_value) * 100
        )

        if relative_error <= tolerance_percent:
            return True, None
        else:
            return (
                False,
                f"计算值{calculated_value:.2f}与测量值{measured_value:.2f}误差{relative_error:.2f}%，超过{tolerance_percent}%",
            )

    def parse_complex_formula(self, formula_text: str) -> Dict[str, any]:
        """
        解析复杂公式文本，提取公式和参数说明

        Args:
            formula_text: 包含公式和参数说明的文本

        Returns:
            {"formula": "C=...", "parameters": {...}}
        """
        result = {"formula": None, "parameters": {}}

        lines = formula_text.split("\n")

        for line in lines:
            line = line.strip()

            # 提取公式
            if "C=" in line or "P=" in line:
                formula_match = re.search(r"([CP]=[^\n;]+)", line)
                if formula_match:
                    result["formula"] = formula_match.group(1)

            # 提取参数说明（格式：C：...；V：...）
            param_match = re.search(r"([A-Za-z]+)[：:]\s*([^；;\n]+)", line)
            if param_match:
                param_name = param_match.group(1)
                param_desc = param_match.group(2).strip()
                result["parameters"][param_name] = param_desc

        return result

    def extract_parameters_from_table(
        self, table_text: str, formula: str
    ) -> Dict[str, float]:
        """
        从表格文本中提取参数值

        Args:
            table_text: 表格文本内容
            formula: 计算公式（用于识别需要哪些参数）

        Returns:
            参数值字典
        """
        parameters = {}

        # 从公式中提取变量名
        variable_pattern = r"([A-Za-z]+)(?=[^A-Za-z]|$)"
        variables = re.findall(variable_pattern, formula)

        for var in variables:
            # 在表格中查找该变量的值
            # 常见格式：W1(g) 82.1269, W恒重(g) 0.1234
            patterns = [
                rf"{re.escape(var)}\s*[（(][^）)]*[）)]\s*(\d+\.?\d*)",
                rf"{re.escape(var)}\s*[：:：]\s*(\d+\.?\d*)",
            ]

            for pattern in patterns:
                match = re.search(pattern, table_text)
                if match:
                    try:
                        parameters[var] = float(match.group(1))
                        break
                    except ValueError:
                        continue

        return parameters
