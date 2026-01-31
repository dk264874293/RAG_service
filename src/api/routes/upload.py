import asyncio
import logging
from typing import List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from src.api.dependencies import get_upload_service
from src.schemas.upload import (
    UploadResponse,
    BatchUploadResponse,
    UploadHistoryList,
)
from src.service.upload_service import UploadService
from src.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/upload", tags=["文件上传"])

# 并发限制：最多同时处理 3 个文件，避免资源耗尽
upload_semaphore = asyncio.Semaphore(3)


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service),
):
    """单文件上传并自动处理"""
    try:
        logger.info(f"收到文件上传请求: {file.filename}")

        await upload_service.validate_file(file)

        result = await upload_service.process_upload(file)

        logger.info(f"文件上传成功: {file.filename}, ID: {result['file_id']}")

        return UploadResponse(
            status="success",
            message=f"文件上传成功: {file.filename}",
            file_id=result["file_id"],
            file_name=file.filename,
            file_size=result["file_size"],
            file_type=result["file_type"],
            processing_status="success" if result["success"] else "failed",
            content_preview=result["content_preview"],
        )

    except ValidationError as e:
        logger.warning(f"文件验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/batch", response_model=BatchUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    upload_service: UploadService = Depends(get_upload_service),
):
    """批量上传并自动处理多个文件"""
    try:
        logger.info(f"收到批量文件上传请求，共 {len(files)} 个文件")

        if len(files) > 10:
            raise HTTPException(
                status_code=400,
                detail=f"批量上传最多支持10个文件，当前上传: {len(files)}",
            )

        async def process_single_file(file: UploadFile) -> UploadResponse:
            try:
                try:
                    await upload_service.validate_file(file)
                except ValidationError as e:
                    return UploadResponse(
                        status="failed",
                        message=str(e),
                        file_id="",
                        file_name=file.filename or "unknown",
                        file_size=0,
                        file_type="",
                        processing_status="failed",
                    )

                result = await upload_service.process_upload(file)

                return UploadResponse(
                    status="success" if result["success"] else "failed",
                    message=result["process_msg"],
                    file_id=result["file_id"],
                    file_name=file.filename,
                    file_size=result["file_size"],
                    file_type=result["file_type"],
                    processing_status="success" if result["success"] else "failed",
                    content_preview=result["content_preview"],
                )

            except Exception as e:
                logger.error(f"文件处理失败 {file.filename}: {e}")
                return UploadResponse(
                    status="failed",
                    message=f"处理失败: {str(e)}",
                    file_id="",
                    file_name=file.filename or "unknown",
                    file_size=0,
                    file_type="",
                    processing_status="failed",
                )

        async def process_with_semaphore(file: UploadFile) -> UploadResponse:
            async with upload_semaphore:
                return await process_single_file(file)

        tasks = [process_with_semaphore(file) for file in files]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        failed_count = sum(1 for r in results if r.status == "failed")
        success_count = sum(1 for r in results if r.status == "success")

        logger.info(
            f"批量上传完成: 总计={len(files)}, 成功={success_count}, 失败={failed_count}"
        )

        return BatchUploadResponse(
            status="completed",
            message=f"批量上传完成: 成功 {success_count} 个，失败 {failed_count} 个",
            results=results,
            total=len(files),
            success=success_count,
            failed=failed_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


@router.get("/", response_model=UploadHistoryList)
async def get_upload_history(
    limit: int = 50,
    upload_service: UploadService = Depends(get_upload_service),
):
    """获取上传历史记录"""
    try:
        items = upload_service.get_history(limit)
        total = upload_service.get_total_count()

        return UploadHistoryList(
            items=items,
            total=total,
        )
    except Exception as e:
        logger.error(f"获取上传历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取上传历史失败: {str(e)}")


@router.get("/{file_id}")
async def get_upload_status(
    file_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    """获取指定文件的上传和处理状态"""
    try:
        file_info = upload_service.get_file_status(file_id)
        if file_info is None:
            raise HTTPException(status_code=404, detail=f"文件不存在: {file_id}")

        return file_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件状态失败: {str(e)}")


@router.get("/{file_id}/content")
async def get_upload_content(
    file_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    """获取文件处理后的内容"""
    try:
        content = await upload_service.get_file_content(file_id)
        return content
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件内容失败: {str(e)}")


@router.delete("/{file_id}")
async def delete_uploaded_file(
    file_id: str,
    upload_service: UploadService = Depends(get_upload_service),
):
    """删除上传的文件及其处理结果"""
    try:
        result = await upload_service.delete_file(file_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


@router.put("/{file_id}", response_model=UploadResponse)
async def update_uploaded_file(
    file_id: str,
    file: UploadFile = File(...),
    upload_service: UploadService = Depends(get_upload_service),
):
    """
    更新已上传的文件

    删除旧文件的所有处理结果（包括向量索引），然后重新处理新文件
    """
    try:
        logger.info(f"收到文件更新请求: {file_id} -> {file.filename}")

        await upload_service.delete_file(file_id)
        logger.info(f"已删除旧文件: {file_id}")

        result = await upload_service.process_upload(file)
        logger.info(f"文件更新成功: {file.filename}, ID: {result['file_id']}")

        return UploadResponse(
            status="success",
            message=f"文件更新成功: {file.filename}",
            file_id=result["file_id"],
            file_name=file.filename,
            file_size=result["file_size"],
            file_type=result["file_type"],
            processing_status="success" if result["success"] else "failed",
            content_preview=result["content_preview"],
        )

    except ValueError as e:
        logger.warning(f"文件更新失败: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        logger.warning(f"文件验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件更新失败: {str(e)}")
