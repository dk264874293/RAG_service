"""
分析数据提取器
从测试PDF文件中提取结构化的分析数据
"""

import re
import logging
from typing import List, Dict, Any, Optional
from ..models.compliance import AnalysisItem

logger = logging.getLogger(__name__)


class AnalysisDataExtractor:
    """分析数据提取器"""

    def __init__(self):
        """初始化提取器"""
        # 常见的分析项目关键词
        self.analysis_keywords = {
            "悬浮物": ["悬浮物", "SS", "总悬浮固体"],
            "化学需氧量": ["化学需氧量", "COD", "CODcr"],
            "总磷": ["总磷", "TP"],
            "氨氮": ["氨氮", "NH3-N"],
            "pH": ["pH", "酸碱度", "PH"],
            "总氮": ["总氮", "TN"],
            "重金属": ["铅", "镉", "铬", "汞", "砷", "铜", "锌", "镍"],
            "颗粒物": ["颗粒物", "PM"],
        }

        # 方法依据正则表达式
        self.method_patterns = [
            r"(GB/T\s*\d+-\d{4})",
            r"(HJ\s*\d+-\d{4})",
            r"(GB\s*\d+\.\d+-\d{4})",
        ]

        # 计算公式正则表达式
        self.formula_patterns = [
            r"C\s*=\s*([^＝\n]+)",
            r"计算公式[：:]\s*([^\n]+)",
            r"公式[：:]\s*([^\n]+)",
        ]

        # 数值提取正则
        self.number_patterns = [
            r"(\d+\.?\d*)\s*mg/L",
            r"(\d+\.?\d*)\s*mg/kg",
            r"(\d+\.?\d*)\s*μg/L",
            r"(\d+\.?\d*)\s*g/L",
        ]

    def extract_from_pdf_text(self, pdf_text: str) -> List[AnalysisItem]:
        """
        从PDF文本中提取分析数据

        Args:
            pdf_text: PDF文本内容

        Returns:
            分析项目列表
        """
        items = []
        sections = self._split_into_sections(pdf_text)

        for section in sections:
            item = self._extract_analysis_item(section)
            if item and item.project_name:
                items.append(item)
                logger.info(f"提取分析项目: {item.project_name}")

        return items

    def _split_into_sections(self, text: str) -> List[str]:
        """
        将文本分割成多个分析项目段落

        Args:
            text: 完整文本

        Returns:
            段落列表
        """
        sections = []
        lines = text.split("\n")
        current_section = []

        for line in lines:
            line = line.strip()

            # 检测是否是新的分析项目开始
            is_new_section = False
            for keyword in ["分析项目", "Method", "项目", "测试"]:
                if keyword in line and "结果" not in line:
                    if current_section:
                        sections.append("\n".join(current_section))
                    current_section = [line]
                    is_new_section = True
                    break

            if not is_new_section and current_section:
                current_section.append(line)

        # 添加最后一个段落
        if current_section:
            sections.append("\n".join(current_section))

        return sections

    def _extract_analysis_item(self, section_text: str) -> Optional[AnalysisItem]:
        """
        从段落中提取单个分析项目

        Args:
            section_text: 段落文本

        Returns:
            分析项目对象
        """
        # 提取项目名称
        project_name = self._extract_project_name(section_text)
        if not project_name:
            return None

        # 提取方法依据
        method_basis = self._extract_method_basis(section_text)

        # 提取计算公式
        calculation_formula = self._extract_formula(section_text)

        # 提取检出限
        detection_limit = self._extract_detection_limit(section_text)

        # 提取测量值
        measured_value, unit = self._extract_measured_value(section_text)

        return AnalysisItem(
            project_name=project_name,
            method_basis=method_basis,
            calculation_formula=calculation_formula,
            detection_limit=detection_limit,
            measured_value=measured_value,
            unit=unit,
            raw_data={"section_text": section_text},
        )

    def _extract_project_name(self, text: str) -> Optional[str]:
        """提取项目名称"""
        lines = text.split("\n")
        for line in lines[:5]:  # 只检查前5行
            line = line.strip()
            # 查找"分析项目"后的内容
            if "分析项目" in line:
                match = re.search(r"分析项目\s*[：:：]?\s*(.+)", line)
                if match:
                    return match.group(1).strip()

            # 检查常见项目关键词
            for project, keywords in self.analysis_keywords.items():
                for keyword in keywords:
                    if keyword in line:
                        return project

        return None

    def _extract_method_basis(self, text: str) -> Optional[str]:
        """提取方法依据"""
        for pattern in self.method_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        # 查找"方法依据"关键词
        match = re.search(r"方法依据[：:：]?\s*([^\n]+)", text)
        if match:
            return match.group(1).strip()

        return None

    def _extract_formula(self, text: str) -> Optional[str]:
        """提取计算公式并清理"""
        for pattern in self.formula_patterns:
            match = re.search(pattern, text)
            if match:
                formula = match.group(1).strip()

                # 清理公式中的多余内容
                # 移除中文说明、标点符号、单位说明等
                # 只保留数学公式核心部分

                # 步骤1: 移除尾部的中文说明和标点
                formula = re.sub(r"[：；，。]\s*[^\s=×÷/0-9^a-zA-Z△Δ\n]+$", "", formula)

                # 步骤2: 移除单位说明（如"mg/L"、"mol/L"、"μg"等）
                formula = re.sub(
                    r"(浓度|计算|标准溶液|mol/L|mL|μg|mg/L|mg/kg|g|kg|g/L|kg/L).*(\s*[：:：]?\s*[^\)]*\)",
                    "",
                    formula,
                )

                # 步骤3: 移除中文字符（保留字母、数字、运算符、希腊字母）
                # 只保留：a-zA-Z0-9×÷/0-9^()[]{}△Δ∫
                # 注意：保留中文括号和等号，因为它们可能是参数分隔符
                cleaned_formula = re.sub(
                    r"[^\s=a-zA-Z0-9×÷/0-9^()\[\]\s{}△Δ∫。\s\n]", "", formula
                )

                # 步骤4: 清理多余空格
                cleaned_formula = re.sub(r"\s+", " ", cleaned_formula)

                # 步骤5: 移除括号外的文本说明
                # 移除"计算："、"公式："等前缀
                cleaned_formula = re.sub(
                    r"^(计算|公式)\s*[：:：]\s*", "", cleaned_formula
                )

                # 最终清理
                final_formula = cleaned_formula.strip()

                if final_formula:
                    return final_formula

        return None

    def _extract_detection_limit(self, text: str) -> Optional[float]:
        """提取检出限"""
        # 查找"检出限"或"检测限"
        patterns = [
            r"检出限[（(]?mg/L[）)]?\s*[：:：]?\s*(\d+\.?\d*)",
            r"检测限[（(]?mg/L[）)]?\s*[：:：]?\s*(\d+\.?\d*)",
            r"检出限\s*[：:：]?\s*(\d+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return None

    def _extract_measured_value(
        self, text: str
    ) -> tuple[Optional[float], Optional[str]]:
        """提取测量值和单位"""
        # 尝试多种数值模式
        for pattern in self.number_patterns:
            matches = re.findall(pattern, text)
            if matches:
                try:
                    # 提取单位
                    unit_match = re.search(r"mg/L|mg/kg|μg/L|g/L", pattern)
                    unit = unit_match.group(0) if unit_match else None

                    # 返回最后一个匹配的值（通常是最新的结果）
                    value = float(matches[-1])
                    return value, unit
                except (ValueError, IndexError):
                    continue

        # 查找"报出结果"或"结果"列
        result_pattern = r"报出结果\s*mg/L\s*[:：]?\s*(\d+\.?\d*)"
        match = re.search(result_pattern, text)
        if match:
            try:
                return float(match.group(1)), "mg/L"
            except ValueError:
                pass

        return None, None

    def parse_formula_parameters(
        self, formula: str, section_text: str
    ) -> Dict[str, float]:
        """
        从公式文本中解析参数值

        Args:
            formula: 计算公式
            section_text: 包含参数值的文本

        Returns:
            参数字典 {参数名: 参数值}
        """
        parameters = {}

        # 提取公式中的变量名（通常是大写字母或希腊字母）
        # 常见变量：C, V, m, f, △W, W1, W2等
        variable_pattern = r"([A-Za-z△]+)(?=[^A-Za-z△]|$)"
        variables = re.findall(variable_pattern, formula)

        for var in variables:
            # 查找该变量在文本中的值
            # 例如：W1(g) 82.1269
            value_pattern = (
                rf"{re.escape(var)}\s*[：:：]?\s*[（(]?\s*[^\)]*\)?\s*(\d+\.?\d*)"
            )
            match = re.search(value_pattern, section_text)
            if match:
                try:
                    parameters[var] = float(match.group(1))
                except ValueError:
                    continue

        # 特殊处理：△W
        if "△W" in formula or "ΔW" in formula:
            # 尝试从表格中提取W恒重值
            w_constant_pattern = r"W恒重\s*[（(]?\s*g\s*[）)]?\s*[：:：]?\s*(\d+\.?\d*)"
            match = re.search(w_constant_pattern, section_text)
            if match:
                try:
                    parameters["△W"] = float(match.group(1))
                except ValueError:
                    pass

        return parameters
