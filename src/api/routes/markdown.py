from fastapi import APIRouter, Depends, HTTPException

from config import settings
from src.api.dependencies import get_markdown_service
from src.schemas.markdown import (
    MarkdownFileList,
    MarkdownContent,
    MarkdownSaveRequest,
    MarkdownSaveResponse,
)
from src.service.markdown_service import MarkdownService

router = APIRouter(prefix="/api/markdown", tags=["Markdown管理"])


@router.get("/files", response_model=MarkdownFileList)
async def get_markdown_files(
    markdown_service: MarkdownService = Depends(get_markdown_service),
):
    """获取所有Markdown文件列表"""
    if not settings.markdown_editor_enabled:
        raise HTTPException(status_code=403, detail="Markdown编辑器未启用")

    files = markdown_service.list_files()
    return MarkdownFileList(files=files)


@router.get("/file/{file_path:path}", response_model=MarkdownContent)
async def get_markdown_file(
    file_path: str,
    markdown_service: MarkdownService = Depends(get_markdown_service),
):
    """读取指定Markdown文件内容"""
    if not settings.markdown_editor_enabled:
        raise HTTPException(status_code=403, detail="Markdown编辑器未启用")

    file_data = markdown_service.get_file(file_path)
    return MarkdownContent(**file_data)


@router.post("/file/{file_path:path}", response_model=MarkdownSaveResponse)
async def save_markdown_file(
    file_path: str,
    request: MarkdownSaveRequest,
    markdown_service: MarkdownService = Depends(get_markdown_service),
):
    """保存Markdown文件"""
    if not settings.markdown_editor_enabled:
        raise HTTPException(status_code=403, detail="Markdown编辑器未启用")

    result = markdown_service.save_file(file_path, request.content)
    return MarkdownSaveResponse(**result)
