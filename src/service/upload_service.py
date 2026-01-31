import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
import aiofiles
import sqlite3

from fastapi import UploadFile

from config import settings
from src.service.document_service import DocumentService
from src.exceptions import ValidationError, StorageError

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.upload_dir = Path(settings_obj.upload_dir)
        self.processed_dir = Path("./data/processed")
        self.document_service = DocumentService(settings_obj)

        # 初始化 SQLite 持久化存储
        self.db_path = Path("./data/uploads.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化 SQLite 数据库表"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS uploads (
                file_id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                processing_status TEXT NOT NULL,
                process_message TEXT,
                content_preview TEXT
            )
        """)
        conn.commit()
        conn.close()
        logger.info("SQLite 数据库初始化完成")

    async def validate_file(self, file: UploadFile) -> None:
        if not file.filename:
            raise ValidationError("文件名不能为空")

        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in self.settings.allowed_file_types:
            allowed = ", ".join(self.settings.allowed_file_types)
            raise ValidationError(f"不支持的文件类型: {file_ext}，仅支持: {allowed}")

        file_size = 0
        if hasattr(file, "size"):
            file_size = file.size
        else:
            chunk = await file.read(1024)
            file_size = len(chunk)
            await file.seek(0)

        max_size = self.settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            raise ValidationError(
                f"文件过大: {file_size / 1024 / 1024:.2f}MB，最大允许: {self.settings.max_file_size_mb}MB"
            )

    async def save_file(self, file: UploadFile) -> tuple[str, Path]:
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix.lower()
        saved_filename = f"{file_id}{file_ext}"
        saved_path = self.upload_dir / saved_filename

        self.upload_dir.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(saved_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        return file_id, saved_path

    async def process_upload(self, file: UploadFile) -> dict:
        file_id, saved_path = await self.save_file(file)

        file_stat = Path(saved_path).stat()
        file_size = file_stat.st_size
        file_type = Path(file.filename).suffix.lower()

        success, process_msg, documents = await self.document_service.process_document(
            str(saved_path), file_id, file.filename
        )

        content_preview = None
        if success and documents:
            content_preview = self.document_service.get_content_preview(
                documents[0].page_content
            )

        self.add_to_history(
            file_id,
            file.filename,
            file_size,
            file_type,
            success,
            process_msg,
            content_preview,
        )

        return {
            "file_id": file_id,
            "saved_path": saved_path,
            "file_size": file_size,
            "file_type": file_type,
            "success": success,
            "process_msg": process_msg,
            "content_preview": content_preview,
            "documents": documents,
        }

    def add_to_history(
        self,
        file_id: str,
        file_name: str,
        file_size: int,
        file_type: str,
        success: bool,
        process_msg: str,
        content_preview: Optional[str] = None,
    ):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO uploads
            (file_id, file_name, file_size, file_type, uploaded_at, processing_status, process_message, content_preview)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                file_id,
                file_name,
                file_size,
                file_type,
                datetime.now().isoformat(),
                "success" if success else "failed",
                process_msg,
                content_preview,
            ),
        )
        conn.commit()
        conn.close()
        logger.debug(f"已添加到上传历史: {file_id}")

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_id, file_name, file_size, file_type, uploaded_at,
                   processing_status, process_message, content_preview
            FROM uploads
            ORDER BY uploaded_at DESC
            LIMIT ?
        """,
            (limit,),
        )
        rows = cursor.fetchall()
        conn.close()

        items = []
        for row in rows:
            items.append(
                {
                    "file_id": row[0],
                    "file_name": row[1],
                    "file_size": row[2],
                    "file_type": row[3],
                    "uploaded_at": row[4],
                    "processing_status": row[5],
                    "process_message": row[6],
                    "content_preview": row[7],
                }
            )
        return items

    def get_total_count(self) -> int:
        """获取总上传记录数"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM uploads")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_file_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT file_id, file_name, file_size, file_type, uploaded_at,
                   processing_status, process_message, content_preview
            FROM uploads
            WHERE file_id = ?
        """,
            (file_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "file_id": row[0],
                "file_name": row[1],
                "file_size": row[2],
                "file_type": row[3],
                "uploaded_at": row[4],
                "processing_status": row[5],
                "process_message": row[6],
                "content_preview": row[7],
            }
        return None

    async def get_file_content(self, file_id: str) -> Dict[str, Any]:
        result_file = self.processed_dir / f"{file_id}.json"

        if not result_file.exists():
            raise FileNotFoundError(f"处理结果不存在: {file_id}")

        async with aiofiles.open(result_file, "r", encoding="utf-8") as f:
            content = await f.read()

        return json.loads(content)

    async def delete_file(self, file_id: str) -> dict:
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT file_name FROM uploads WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise ValueError(f"文件不存在: {file_id}")

        file_name = row[0]

        upload_files = list(self.upload_dir.glob(f"{file_id}.*"))
        for upload_file in upload_files:
            upload_file.unlink()
            logger.info(f"已删除原始文件: {upload_file.name}")

        result_file = self.processed_dir / f"{file_id}.json"
        if result_file.exists():
            result_file.unlink()
            logger.info(f"已删除处理结果: {result_file.name}")

        deleted_vectors = await self.document_service.delete_document(file_id)
        if deleted_vectors > 0:
            logger.info(f"已从向量索引中删除 {deleted_vectors} 个文档块")

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM uploads WHERE file_id = ?", (file_id,))
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"文件删除成功: {file_name}",
            "deleted_vectors": deleted_vectors,
        }
