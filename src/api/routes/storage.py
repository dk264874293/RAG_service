"""
存储访问路由
Author: RAG Service Team
Date: 2026-01-10
Description: 提供本地文件访问和URL生成接口
"""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path as FastAPIPath
from fastapi.responses import FileResponse

from config import settings
from src.api.dependencies import get_storage_service
from src.service.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("/local/{file_path:path}")
async def get_local_file(
    file_path: str = FastAPIPath(..., description="文件路径"),
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    访问本地文件

    用于访问存储在本地文件系统中的文件
    支持上传文件、处理结果等

    Args:
        file_path: 文件路径（相对于数据目录）

    Returns:
        文件内容
    """
    # 构建完整路径
    data_dir = Path(settings.upload_dir).parent
    full_path = (data_dir / file_path).resolve()

    # 安全检查：确保路径在允许的目录内
    if not str(full_path).startswith(str(data_dir)):
        raise HTTPException(status_code=403, detail="非法文件路径")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="路径不是文件")

    # 返回文件
    return FileResponse(
        path=str(full_path),
        filename=full_path.name,
        media_type="application/octet-stream",
    )


@router.get("/url/{file_path:path}")
async def get_file_url(
    file_path: str = FastAPIPath(..., description="文件路径"),
    expires: int = 3600,
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    获取文件访问URL

    返回文件的访问URL（可能是OSS预签名URL）
    如果使用本地存储，返回本地访问路径

    Args:
        file_path: 文件路径
        expires: URL过期时间（秒），默认3600秒（1小时）

    Returns:
        包含URL的响应
    """
    try:
        url = storage_service.get_file_url(file_path, expires)

        if url:
            return {
                "url": url,
                "expires_in": expires,
                "storage_type": storage_service.get_storage_type(),
            }
        else:
            # 本地存储，返回本地访问路径
            return {
                "url": f"/api/storage/local/{file_path}",
                "storage_type": storage_service.get_storage_type(),
                "note": "本地存储，使用本地访问路径",
            }
    except Exception as e:
        logger.error(f"Failed to get file URL for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="获取文件URL失败")


@router.get("/info/{file_path:path}")
async def get_file_info(
    file_path: str = FastAPIPath(..., description="文件路径"),
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    获取文件元数据

    返回文件的大小、修改时间等元数据信息

    Args:
        file_path: 文件路径

    Returns:
        文件元数据
    """
    try:
        metadata = await storage_service.get_file_metadata(file_path)
        metadata["storage_type"] = storage_service.get_storage_type()
        return metadata
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        logger.error(f"Failed to get file metadata for {file_path}: {e}")
        raise HTTPException(status_code=500, detail="获取文件信息失败")


@router.get("/list")
async def list_files(
    prefix: str = "",
    limit: int = 100,
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    列出文件

    根据前缀和限制列出文件

    Args:
        prefix: 文件路径前缀
        limit: 最大返回数量

    Returns:
        文件列表
    """
    try:
        files = await storage_service.list_files(prefix, limit)
        return {
            "files": files,
            "count": len(files),
            "storage_type": storage_service.get_storage_type(),
            "prefix": prefix,
        }
    except Exception as e:
        logger.error(f"Failed to list files with prefix {prefix}: {e}")
        raise HTTPException(status_code=500, detail="列出文件失败")


@router.get("/status")
async def get_storage_status(
    storage_service: StorageService = Depends(get_storage_service),
):
    """
    获取存储服务状态

    返回当前使用的存储类型和配置信息

    Returns:
        存储服务状态
    """
    return {
        "storage_type": storage_service.get_storage_type(),
        "is_using_fallback": storage_service.is_using_fallback(),
        "configured_type": settings.storage_type,
        "oss_configured": bool(
            settings.oss_access_key_id
            and settings.oss_access_key_secret
            and settings.oss_endpoint
            and settings.oss_bucket_name
        ),
        "fallback_enabled": settings.oss_fallback_to_local,
    }
