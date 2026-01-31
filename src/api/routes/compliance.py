"""
合规性检查API路由
提供环境监测数据合规性检查的API接口
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from ...service.compliance_service import ComplianceCheckService
from ...models.compliance import ComplianceCheckRequest, ComplianceCheckResponse
from ..dependencies import get_retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/compliance", tags=["Compliance Check"])


class ComplianceCheckFileRequest(BaseModel):
    """合规性检查请求（文件上传版）"""

    enable_formula_calculation: bool = Field(
        default=True, description="是否启用公式计算验证"
    )
    enable_vector_retrieval: bool = Field(
        default=True, description="是否启用向量检索匹配标准"
    )


@router.post("/check", response_model=ComplianceCheckResponse)
async def check_compliance_by_file(
    file: UploadFile = File(..., description="测试PDF文件"),
    enable_formula_calculation: bool = Form(default=True),
    enable_vector_retrieval: bool = Form(default=True),
):
    """
    上传文件并执行合规性检查

    接收测试PDF文件，执行以下检查：
    1. 提取分析数据（项目、方法、公式、结果）
    2. 匹配国标标准
    3. 执行公式计算验证
    4. 检查是否符合标准限值
    5. 返回合规性报告

    参数：
    - file: 测试PDF文件
    - enable_formula_calculation: 是否启用公式计算验证（默认True）
    - enable_vector_retrieval: 是否启用向量检索（默认True）
    """
    import uuid

    try:
        logger.info(f"接收合规性检查请求: file={file.filename}")

        # 验证文件类型
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="只支持PDF文件")

        # 保存上传的文件
        upload_dir = Path("./data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_id = str(uuid.uuid4())
        file_path = upload_dir / f"{file_id}.pdf"

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        logger.info(f"文件已保存: {file_path}")

        # 创建合规性检查请求
        request = ComplianceCheckRequest(
            test_pdf_path=str(file_path),
            enable_formula_calculation=enable_formula_calculation,
            enable_vector_retrieval=enable_vector_retrieval,
        )

        # 获取检索服务（如果启用）
        retrieval_service = None
        if enable_vector_retrieval:
            retrieval_service = get_retrieval_service()

        # 创建合规性检查服务
        compliance_service = ComplianceCheckService(retrieval_service=retrieval_service)

        # 执行检查
        result = await compliance_service.check_compliance(request)

        logger.info(
            f"合规性检查完成: 合规={result.compliant_count}, "
            f"不合规={result.non_compliant_count}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"合规性检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")


@router.post("/check-by-path", response_model=ComplianceCheckResponse)
async def check_compliance_by_path(
    request: ComplianceCheckRequest, retrieval_service=None
):
    """
    通过文件路径执行合规性检查

    接收PDF文件路径，执行合规性检查。

    参数：
    - test_pdf_path: 测试PDF文件路径
    - gb_directory: 国标目录路径（默认: src/pdfs/GB）
    - enable_formula_calculation: 是否启用公式计算验证（默认True）
    - enable_vector_retrieval: 是否启用向量检索（默认True）
    """
    try:
        logger.info(f"接收合规性检查请求: path={request.test_pdf_path}")

        # 验证文件存在
        if not Path(request.test_pdf_path).exists():
            raise HTTPException(
                status_code=404, detail=f"文件不存在: {request.test_pdf_path}"
            )

        # 获取检索服务（如果启用）
        retrieval = None
        if request.enable_vector_retrieval:
            retrieval = get_retrieval_service()

        # 创建合规性检查服务
        compliance_service = ComplianceCheckService(retrieval_service=retrieval)

        # 执行检查
        result = await compliance_service.check_compliance(request)

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"合规性检查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")


@router.get("/standards")
async def list_available_standards(gb_directory: str = "src/pdfs/GB"):
    """
    列出国标目录中的所有标准文件

    返回国标目录中的所有PDF标准文件列表。
    """
    try:
        gb_dir = Path(gb_directory)

        if not gb_dir.exists():
            raise HTTPException(
                status_code=404, detail=f"国标目录不存在: {gb_directory}"
            )

        standards = []
        for pdf_file in gb_dir.glob("*.pdf"):
            standards.append(
                {
                    "filename": pdf_file.name,
                    "path": str(pdf_file),
                    "size": pdf_file.stat().st_size,
                }
            )

        return {
            "status": "success",
            "gb_directory": gb_directory,
            "count": len(standards),
            "standards": sorted(standards, key=lambda x: x["filename"]),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出标准失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"列出标准失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "compliance_check", "version": "1.0.0"}
