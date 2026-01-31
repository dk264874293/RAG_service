"""
合规性检查服务
整合数据提取、标准匹配、公式计算，完成完整的合规性检查流程
"""

import logging
import uuid
import pypdfium2
from typing import List, Optional

from ..models.compliance import (
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceCheckItem,
    AnalysisItem,
    StandardRequirement,
    CalculationResult,
)
from ..extractor.analysis_data_extractor import AnalysisDataExtractor
from ..compliance.standard_matcher import StandardMatcher
from ..compliance.formula_calculator import FormulaCalculator

logger = logging.getLogger(__name__)


class ComplianceCheckService:
    """合规性检查服务"""

    def __init__(self, retrieval_service=None, gb_directory="src/pdfs/GB"):
        """
        初始化合规性检查服务

        Args:
            retrieval_service: 向量检索服务（用于智能标准匹配）
            gb_directory: 国标PDF目录路径
        """
        self.retrieval_service = retrieval_service
        self.gb_directory = gb_directory

        # 初始化子模块
        self.data_extractor = AnalysisDataExtractor()
        self.standard_matcher = StandardMatcher(retrieval_service)
        self.formula_calculator = FormulaCalculator()

        logger.info("合规性检查服务初始化完成")

    async def check_compliance(
        self, request: ComplianceCheckRequest
    ) -> ComplianceCheckResponse:
        """
        执行合规性检查

        流程：
        1. 从测试PDF中提取分析数据
        2. 为每个分析项目匹配国标标准
        3. 如果有计算公式，执行公式计算验证
        4. 检查测量值是否符合标准限值
        5. 汇总检查结果

        Args:
            request: 合规性检查请求

        Returns:
            合规性检查响应
        """
        request_id = str(uuid.uuid4())
        logger.info(
            f"开始合规性检查: request_id={request_id}, file={request.test_pdf_path}"
        )

        try:
            # 1. 提取测试PDF文本
            pdf_text = self._extract_pdf_text(request.test_pdf_path)
            if not pdf_text:
                return self._error_response(
                    request_id, request.test_pdf_path, "无法提取PDF文本"
                )

            # 2. 提取分析数据
            analysis_items = self.data_extractor.extract_from_pdf_text(pdf_text)
            if not analysis_items:
                return self._error_response(
                    request_id, request.test_pdf_path, "未找到分析数据"
                )

            logger.info(f"提取到{len(analysis_items)}个分析项目")

            # 3. 逐项检查合规性
            check_results = []
            for item in analysis_items:
                check_result = await self._check_single_item(item, request)
                check_results.append(check_result)

            # 4. 汇总结果
            response = self._build_response(
                request_id, request.test_pdf_path, check_results
            )

            logger.info(
                f"合规性检查完成: 合规={response.compliant_count}, "
                f"不合规={response.non_compliant_count}, "
                f"未知={response.unknown_count}"
            )

            return response

        except Exception as e:
            logger.error(f"合规性检查失败: {e}", exc_info=True)
            return self._error_response(
                request_id, request.test_pdf_path, f"检查过程出错: {str(e)}"
            )

    async def _check_single_item(
        self, analysis_item: AnalysisItem, request: ComplianceCheckRequest
    ) -> ComplianceCheckItem:
        """
        检查单个分析项目的合规性

        Args:
            analysis_item: 分析项目数据
            request: 检查请求配置

        Returns:
            单项检查结果
        """
        logger.info(f"检查分析项目: {analysis_item.project_name}")

        result = ComplianceCheckItem(analysis_item=analysis_item, match_confidence=0.0)

        # 1. 匹配国标标准
        matched_standard = self.standard_matcher.match_standard(
            analysis_item.project_name, analysis_item.method_basis, request.gb_directory
        )

        if matched_standard:
            result.matched_standard = matched_standard
            result.match_confidence = 0.9
            logger.info(f"匹配到标准: {matched_standard.standard_code}")
        else:
            logger.warning(f"未找到匹配的标准: {analysis_item.project_name}")

        # 2. 公式计算验证（如果启用且有公式）
        calculation_result = None
        if request.enable_formula_calculation and analysis_item.calculation_formula:
            try:
                # 提取参数
                parameters = self.data_extractor.parse_formula_parameters(
                    analysis_item.calculation_formula,
                    analysis_item.raw_data.get("section_text", ""),
                )

                if parameters:
                    calculation_result = self.formula_calculator.calculate(
                        analysis_item.calculation_formula,
                        parameters,
                        analysis_item.unit,
                    )
                    result.calculation_result = calculation_result

                    # 验证计算值与测量值
                    if analysis_item.measured_value and calculation_result.is_valid:
                        is_valid, error_msg = (
                            self.formula_calculator.verify_calculation(
                                calculation_result.calculated_value,
                                analysis_item.measured_value,
                                tolerance_percent=10.0,
                            )
                        )

                        if not is_valid:
                            logger.warning(f"公式验证失败: {error_msg}")

            except Exception as e:
                logger.error(f"公式计算失败: {e}")

        # 3. 合规性检查（如果有标准限值且有测量值）
        if matched_standard and analysis_item.measured_value:
            is_compliant, violation_reason = self.standard_matcher.check_compliance(
                analysis_item.measured_value, matched_standard, analysis_item.unit
            )

            result.is_compliant = is_compliant
            result.violation_reason = violation_reason

            if is_compliant:
                logger.info(f"合规: {analysis_item.project_name}")
            else:
                logger.warning(
                    f"不合规: {analysis_item.project_name}, 原因: {violation_reason}"
                )

        return result

    def _extract_pdf_text(self, pdf_path: str) -> Optional[str]:
        """
        提取PDF文本

        Args:
            pdf_path: PDF文件路径

        Returns:
            提取的文本，失败返回None
        """
        try:
            pdf = pypdfium2.PdfDocument(pdf_path)
            text = ""
            for page in pdf:
                textpage = page.get_textpage()
                text += textpage.get_text_range()
            pdf.close()
            return text
        except Exception as e:
            logger.error(f"提取PDF文本失败: {pdf_path}, error={e}")
            return None

    def _build_response(
        self, request_id: str, test_file: str, check_results: List[ComplianceCheckItem]
    ) -> ComplianceCheckResponse:
        """
        构建合规性检查响应

        Args:
            request_id: 请求ID
            test_file: 测试文件
            check_results: 检查结果列表

        Returns:
            合规性检查响应
        """
        # 统计结果
        total_items = len(check_results)
        compliant_count = sum(1 for r in check_results if r.is_compliant is True)
        non_compliant_count = sum(1 for r in check_results if r.is_compliant is False)
        unknown_count = total_items - compliant_count - non_compliant_count

        # 生成汇总信息
        summary_parts = []
        if compliant_count > 0:
            summary_parts.append(f"合规{compliant_count}项")
        if non_compliant_count > 0:
            summary_parts.append(f"不合规{non_compliant_count}项")
        if unknown_count > 0:
            summary_parts.append(f"无法确定{unknown_count}项")

        summary = ", ".join(summary_parts) if summary_parts else None

        # 提取不合规项目详情
        non_compliant_details = []
        for result in check_results:
            if result.is_compliant is False:
                non_compliant_details.append(
                    f"- {result.analysis_item.project_name}: "
                    f"{result.analysis_item.measured_value}"
                    f"{result.analysis_item.unit or ''}, "
                    f"{result.violation_reason}"
                )

        if non_compliant_details:
            summary += "\n\n不合规详情:\n" + "\n".join(non_compliant_details)

        return ComplianceCheckResponse(
            request_id=request_id,
            test_file=test_file,
            total_items=total_items,
            compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            unknown_count=unknown_count,
            check_results=check_results,
            summary=summary,
        )

    def _error_response(
        self, request_id: str, test_file: str, error_message: str
    ) -> ComplianceCheckResponse:
        """
        构建错误响应

        Args:
            request_id: 请求ID
            test_file: 测试文件
            error_message: 错误消息

        Returns:
            错误响应
        """
        return ComplianceCheckResponse(
            request_id=request_id,
            test_file=test_file,
            total_items=0,
            compliant_count=0,
            non_compliant_count=0,
            unknown_count=0,
            check_results=[],
            summary=error_message,
        )
