from pydantic import BaseModel, Field
from typing import List, Optional


class UploadResponse(BaseModel):
    """单个文件上传响应模型"""

    status: str = Field(..., description="上传状态: success/failed")
    message: str = Field(..., description="详细信息消息")
    file_id: str = Field(..., description="文件唯一标识符（UUID格式）")
    file_name: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型扩展名（如 .pdf）")
    processing_status: str = Field(..., description="文档处理状态: success/failed")
    content_preview: Optional[str] = Field(None, description="内容预览（最多500字符）")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "文件上传成功: document.pdf",
                "file_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "document.pdf",
                "file_size": 1024000,
                "file_type": ".pdf",
                "processing_status": "success",
                "content_preview": "这是文档的前500个字符内容预览...",
            }
        }


class BatchUploadResponse(BaseModel):
    """批量文件上传响应模型"""

    status: str = Field(..., description="批量上传状态: completed")
    message: str = Field(..., description="批量上传结果摘要")
    results: List[UploadResponse] = Field(..., description="每个文件的详细上传结果")
    total: int = Field(..., description="上传文件总数")
    success: int = Field(..., description="成功处理的文件数")
    failed: int = Field(..., description="处理失败的文件数")

    class Config:
        schema_extra = {
            "example": {
                "status": "completed",
                "message": "批量上传完成: 成功 2 个，失败 1 个",
                "results": [
                    {
                        "status": "success",
                        "file_id": "550e8400-e29b-41d4-a716-4466554400000",
                        "file_name": "doc1.pdf",
                        "file_size": 1024000,
                        "file_type": ".pdf",
                        "processing_status": "success",
                    },
                    {
                        "status": "success",
                        "file_id": "550e8400-e29b-41d4-a716-4466554400001",
                        "file_name": "doc2.docx",
                        "file_size": 512000,
                        "file_type": ".docx",
                        "processing_status": "success",
                    },
                    {
                        "status": "failed",
                        "file_id": "",
                        "file_name": "doc3.txt",
                        "file_size": 0,
                        "file_type": ".txt",
                        "processing_status": "failed",
                    },
                ],
                "total": 3,
                "success": 2,
                "failed": 1,
            }
        }


class UploadHistoryItem(BaseModel):
    """上传历史记录项模型"""

    file_id: str = Field(..., description="文件唯一标识符")
    file_name: str = Field(..., description="原始文件名")
    file_size: int = Field(..., description="文件大小（字节）")
    file_type: str = Field(..., description="文件类型扩展名")
    uploaded_at: str = Field(..., description="上传时间（ISO 8601格式）")
    processing_status: str = Field(..., description="文档处理状态")
    content_preview: Optional[str] = Field(None, description="内容预览")
    process_message: Optional[str] = Field(None, description="处理消息或错误信息")

    class Config:
        schema_extra = {
            "example": {
                "file_id": "550e8400-e29b-41d4-a716-4466554400000",
                "file_name": "document.pdf",
                "file_size": 1024000,
                "file_type": ".pdf",
                "uploaded_at": "2026-01-29T15:41:22",
                "processing_status": "success",
                "content_preview": "这是文档的前500个字符内容预览...",
                "process_message": "处理成功",
            }
        }


class UploadHistoryList(BaseModel):
    """上传历史列表响应模型"""

    items: List[UploadHistoryItem] = Field(..., description="上传历史记录列表")
    total: int = Field(..., description="历史记录总数")

    class Config:
        schema_extra = {
            "example": {
                "items": [
                    {
                        "file_id": "550e8400-e29b-41d4-a716-4466554400000",
                        "file_name": "document.pdf",
                        "file_size": 1024000,
                        "file_type": ".pdf",
                        "uploaded_at": "2026-01-29T15:41:22",
                        "processing_status": "success",
                    }
                ],
                "total": 1,
            }
        }
