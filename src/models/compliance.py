"""
合规性检查数据模型
定义分析数据、标准、检查结果等数据结构
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


class AnalysisItem(BaseModel):
    """分析项目数据"""

    project_name: str = Field(..., description="分析项目名称，如'悬浮物'、'化学需氧量'")
    method_basis: Optional[str] = Field(
        None, description="方法依据，如'GB/T 11901-1989'"
    )
    analysis_date: Optional[str] = Field(None, description="分析日期")
    calculation_formula: Optional[str] = Field(None, description="计算公式")
    detection_limit: Optional[float] = Field(None, description="检出限（mg/L或mg/kg）")
    measured_value: Optional[float] = Field(None, description="测量值")
    unit: Optional[str] = Field(None, description="单位，如'mg/L'、'mg/kg'")
    raw_data: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="原始数据"
    )


class StandardRequirement(BaseModel):
    """标准要求"""

    standard_code: str = Field(..., description="标准编号，如'GB 5085.1-2007'")
    standard_name: str = Field(..., description="标准名称")
    indicator: str = Field(..., description="指标名称")
    limit_value: Optional[float] = Field(None, description="限值")
    limit_type: Optional[str] = Field(None, description="限值类型，如'≤'、'≥'、'范围'")
    limit_range: Optional[tuple] = Field(None, description="限值范围（用于范围型限值）")
    unit: Optional[str] = Field(None, description="单位")
    description: Optional[str] = Field(None, description="标准描述")
    source_document: Optional[str] = Field(None, description="来源文档")


class CalculationResult(BaseModel):
    """计算结果"""

    formula: str = Field(..., description="使用的公式")
    input_values: Dict[str, float] = Field(..., description="输入值")
    calculated_value: float = Field(..., description="计算结果")
    calculated_unit: Optional[str] = Field(None, description="计算结果单位")
    is_valid: bool = Field(..., description="计算是否有效")


class ComplianceCheckItem(BaseModel):
    """单项合规性检查结果"""

    analysis_item: AnalysisItem = Field(..., description="分析项目")
    matched_standard: Optional[StandardRequirement] = Field(
        None, description="匹配的标准"
    )
    calculation_result: Optional[CalculationResult] = Field(
        None, description="计算结果"
    )
    is_compliant: Optional[bool] = Field(None, description="是否合规")
    violation_reason: Optional[str] = Field(None, description="违规原因")
    match_confidence: float = Field(default=0.0, description="匹配置信度（0-1）")


class ComplianceCheckRequest(BaseModel):
    """合规性检查请求"""

    test_pdf_path: str = Field(..., description="测试PDF文件路径")
    gb_directory: str = Field(default="src/pdfs/GB", description="国标目录路径")
    enable_formula_calculation: bool = Field(
        default=True, description="是否启用公式计算验证"
    )
    enable_vector_retrieval: bool = Field(
        default=True, description="是否启用向量检索匹配标准"
    )


class ComplianceCheckResponse(BaseModel):
    """合规性检查响应"""

    request_id: str = Field(..., description="请求ID")
    test_file: str = Field(..., description="测试文件")
    check_time: datetime = Field(default_factory=datetime.now, description="检查时间")
    total_items: int = Field(default=0, description="总检查项数")
    compliant_count: int = Field(default=0, description="合规项数")
    non_compliant_count: int = Field(default=0, description="不合规项数")
    unknown_count: int = Field(default=0, description="未知状态项数")
    check_results: List[ComplianceCheckItem] = Field(
        default_factory=list, description="检查结果列表"
    )
    summary: Optional[str] = Field(None, description="汇总信息")


class FormulaParameter(BaseModel):
    """公式参数"""

    parameter_name: str = Field(..., description="参数名称，如'C'、'△W'、'V'")
    value: Optional[float] = Field(None, description="参数值")
    unit: Optional[str] = Field(None, description="参数单位")
    description: Optional[str] = Field(None, description="参数描述")
