import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
import aiofiles
import pymysql

from fastapi import UploadFile

from src.service.document_service import DocumentService
from src.exceptions import ValidationError
from src.service.local_storage_adapter import LocalStorageAdapter

logger = logging.getLogger(__name__)


class UploadService:
    def __init__(self, settings_obj, vector_service=None, storage_service=None):
        self.settings = settings_obj
        self.upload_dir = Path(settings_obj.upload_dir)
        self.processed_dir = Path("./data/processed")
        self.document_service = DocumentService(settings_obj)
        self.vector_service = vector_service
        self.storage_service = storage_service

        self._init_db()

    def _get_db_connection(self):
        """获取 MySQL 数据库连接"""
        return pymysql.connect(
            host=self.settings.mysql_server_host,
            port=int(self.settings.mysql_server_port),
            user=self.settings.mysql_server_username,
            password=self.settings.mysql_server_password,
            database=self.settings.mysql_server_database,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _init_db(self):
        """初始化 MySQL 数据库表"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS uploads (
                        file_id VARCHAR(36) PRIMARY KEY,
                        file_name VARCHAR(255) NOT NULL,
                        file_size BIGINT NOT NULL,
                        file_type VARCHAR(50) NOT NULL,
                        uploaded_at DATETIME NOT NULL,
                        processing_status VARCHAR(20) NOT NULL,
                        process_message TEXT,
                        content_preview TEXT,
                        storage_type VARCHAR(20) DEFAULT 'local' COMMENT '存储类型：local或oss',
                        storage_key VARCHAR(500) DEFAULT NULL COMMENT 'OSS key或本地路径',
                        file_url TEXT DEFAULT NULL COMMENT '文件访问URL',
                        INDEX idx_uploaded_at (uploaded_at),
                        INDEX idx_storage_type (storage_type)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
            conn.commit()
            logger.info("MySQL 数据库初始化完成")
        finally:
            conn.close()

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

        # 读取文件内容
        content = await file.read()

        # 使用存储服务保存文件
        if self.storage_service:
            file_path = f"uploads/{saved_filename}"
            result = await self.storage_service.upload_file(
                file_path, content, metadata={"original_filename": file.filename}
            )
            # 修复：对于本地存储，返回绝对路径；对于OSS，返回相对路径（key）
            if isinstance(self.storage_service, LocalStorageAdapter):
                saved_path = self.storage_service._resolve_path(file_path)
            else:
                # OSS 存储返回的 key
                saved_path = Path(file_path)
        else:
            # 回退到本地文件系统
            saved_path = self.upload_dir / saved_filename
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(saved_path, "wb") as f:
                await f.write(content)

        return file_id, saved_path

    def _generate_markdown_pages(self, documents: list) -> List[Dict[str, Any]]:
        if not documents:
            return []

        markdown_pages = []
        for idx, doc in enumerate(documents, 1):
            page = {
                "page_number": idx,
                "title": f"第 {idx} 部分",
                "content": doc.page_content,
                "metadata": {
                    "doc_id": doc.id_ if hasattr(doc, "id_") else str(idx),
                    **(doc.metadata if hasattr(doc, "metadata") else {}),
                },
            }
            markdown_pages.append(page)

        return markdown_pages

    async def process_upload(self, file: UploadFile) -> dict:
        file_id, saved_path = await self.save_file(file)

        file_stat = Path(saved_path).stat()
        file_size = file_stat.st_size
        file_type = Path(file.filename).suffix.lower()

        success, process_msg, documents = await self.document_service.process_document(
            str(saved_path), file_id, file.filename
        )

        content_preview = None
        markdown_content = None
        storage_type = "local"
        storage_key = str(saved_path)
        file_url = None

        # 获取存储信息
        if self.storage_service:
            storage_type = self.storage_service.get_storage_type()
            storage_key = str(saved_path)
            file_url = self.storage_service.get_file_url(f"uploads/{saved_path.name}")

        if success and documents:
            content_preview = self.document_service.get_content_preview(
                documents[0].page_content
            )
            markdown_content = self._generate_markdown_pages(documents)

            if self.vector_service:
                try:
                    vector_success = await self.vector_service.vectorize_document(
                        file_id, documents
                    )
                    if vector_success:
                        logger.info(f"Document vectorized successfully: {file_id}")
                    else:
                        logger.warning(f"Document vectorization failed: {file_id}")
                except Exception as e:
                    logger.error(f"Vectorization error for {file_id}: {e}")

        self.add_to_history(
            file_id,
            file.filename,
            file_size,
            file_type,
            success,
            process_msg,
            content_preview,
            storage_type,
            storage_key,
            file_url,
        )

        return {
            "file_id": file_id,
            "saved_path": saved_path,
            "file_size": file_size,
            "file_type": file_type,
            "success": success,
            "process_msg": process_msg,
            "content_preview": content_preview,
            "markdown_content": markdown_content,
            "documents": documents,
            "storage_type": storage_type,
            "storage_key": storage_key,
            "file_url": file_url,
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
        storage_type: str = "local",
        storage_key: Optional[str] = None,
        file_url: Optional[str] = None,
    ):
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 构建SQL语句，尝试包含新字段（如果列不存在会失败，使用INSERT IGNORE）
                cursor.execute(
                    """
                    INSERT INTO uploads
                    (file_id, file_name, file_size, file_type, uploaded_at, processing_status, process_message, content_preview, storage_type, storage_key, file_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    file_name = VALUES(file_name),
                    file_size = VALUES(file_size),
                    file_type = VALUES(file_type),
                    uploaded_at = VALUES(uploaded_at),
                    processing_status = VALUES(processing_status),
                    process_message = VALUES(process_message),
                    content_preview = VALUES(content_preview),
                    storage_type = VALUES(storage_type),
                    storage_key = VALUES(storage_key),
                    file_url = VALUES(file_url)
                """,
                    (
                        file_id,
                        file_name,
                        file_size,
                        file_type,
                        datetime.now(),
                        "success" if success else "failed",
                        process_msg,
                        content_preview,
                        storage_type,
                        storage_key,
                        file_url,
                    ),
                )
            conn.commit()
            logger.debug(f"已添加到上传历史: {file_id}, storage_type: {storage_type}")
        except Exception as e:
            # 如果新字段不存在，回退到旧版本SQL
            logger.warning(f"Database schema does not support storage fields, using legacy SQL: {e}")
            conn.rollback()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO uploads
                        (file_id, file_name, file_size, file_type, uploaded_at, processing_status, process_message, content_preview)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                        file_name = VALUES(file_name),
                        file_size = VALUES(file_size),
                        file_type = VALUES(file_type),
                        uploaded_at = VALUES(uploaded_at),
                        processing_status = VALUES(processing_status),
                        process_message = VALUES(process_message),
                        content_preview = VALUES(content_preview)
                    """,
                        (
                            file_id,
                            file_name,
                            file_size,
                            file_type,
                            datetime.now(),
                            "success" if success else "failed",
                            process_msg,
                            content_preview,
                        ),
                    )
                conn.commit()
                logger.debug(f"已添加到上传历史: {file_id}")
            except Exception as e2:
                logger.error(f"Failed to add to history: {e2}")
                conn.rollback()
        finally:
            conn.close()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id, file_name, file_size, file_type, uploaded_at,
                           processing_status, process_message, content_preview
                    FROM uploads
                    ORDER BY uploaded_at DESC
                    LIMIT %s
                """,
                    (limit,),
                )
                rows = cursor.fetchall()
        finally:
            conn.close()

        items = []
        for row in rows:
            items.append(
                {
                    "file_id": row["file_id"],
                    "file_name": row["file_name"],
                    "file_size": row["file_size"],
                    "file_type": row["file_type"],
                    "uploaded_at": row["uploaded_at"].isoformat(),
                    "processing_status": row["processing_status"],
                    "process_message": row["process_message"],
                    "content_preview": row["content_preview"],
                }
            )
        return items

    def get_total_count(self) -> int:
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM uploads")
                result = cursor.fetchone()
                return result["count"]
        finally:
            conn.close()

    def get_file_status(self, file_id: str) -> Optional[Dict[str, Any]]:
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT file_id, file_name, file_size, file_type, uploaded_at,
                           processing_status, process_message, content_preview
                    FROM uploads
                    WHERE file_id = %s
                """,
                    (file_id,),
                )
                row = cursor.fetchone()
        finally:
            conn.close()

        if row:
            return {
                "file_id": row["file_id"],
                "file_name": row["file_name"],
                "file_size": row["file_size"],
                "file_type": row["file_type"],
                "uploaded_at": row["uploaded_at"].isoformat(),
                "processing_status": row["processing_status"],
                "process_message": row["process_message"],
                "content_preview": row["content_preview"],
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
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT file_name FROM uploads WHERE file_id = %s", (file_id,)
                )
                row = cursor.fetchone()
        finally:
            conn.close()

        if not row:
            raise ValueError(f"文件不存在: {file_id}")

        file_name = row["file_name"]

        # 使用存储服务删除文件
        if self.storage_service:
            # 尝试删除所有可能的文件扩展名
            for ext in [".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".pptx", ".xlsx"]:
                file_path = f"uploads/{file_id}{ext}"
                try:
                    await self.storage_service.delete_file(file_path)
                    logger.info(f"已从存储删除: {file_path}")
                except Exception as e:
                    logger.debug(f"删除文件失败（可能不存在）: {file_path}, {e}")
        else:
            # 回退到本地文件系统
            upload_files = list(self.upload_dir.glob(f"{file_id}.*"))
            for upload_file in upload_files:
                upload_file.unlink()
                logger.info(f"已删除原始文件: {upload_file.name}")

        # 删除处理结果
        result_file = self.processed_dir / f"{file_id}.json"
        if result_file.exists():
            result_file.unlink()
            logger.info(f"已删除处理结果: {result_file.name}")

        # 删除向量索引
        deleted_vectors = 0
        if self.vector_service:
            try:
                deleted_vectors = await self.vector_service.delete_vectors(file_id)
                if deleted_vectors > 0:
                    logger.info(f"已从向量索引中删除 {deleted_vectors} 个文档块")
            except Exception as e:
                logger.error(f"删除向量失败: {e}")

        # 从数据库删除记录
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM uploads WHERE file_id = %s", (file_id,))
            conn.commit()
        finally:
            conn.close()

        return {
            "status": "success",
            "message": f"文件删除成功: {file_name}",
            "deleted_vectors": deleted_vectors,
        }
