import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException

from config import settings


class MarkdownService:
    def __init__(self, settings_obj, storage_service=None):
        self.settings = settings_obj
        self.output_dir = Path(settings_obj.markdown_output_dir)
        self.storage_service = storage_service

    def validate_path(self, file_path: str) -> Path:
        # 使用已解析的 output_dir，避免重复解析导致路径不一致
        output_dir = self.output_dir
        full_path = (output_dir / file_path).resolve()

        if not str(full_path).startswith(str(output_dir)):
            raise HTTPException(status_code=403, detail="非法文件路径")

        return full_path

    def validate_file_size(self, file_size: int) -> None:
        if file_size > self.settings.markdown_max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大（{file_size} > {self.settings.markdown_max_file_size}）",
            )

    def list_files(self) -> List[dict]:
        if not self.output_dir.exists():
            return []

        files = []
        import logging
        logger = logging.getLogger(__name__)

        for root, dirs, filenames in os.walk(self.output_dir):
            for filename in filenames:
                if filename.endswith(".md"):
                    full_path = Path(root) / filename
                    rel_path = full_path.relative_to(self.output_dir)
                    folder_name = rel_path.parent.name if rel_path.parent else ""

                    stat = full_path.stat()
                    file_size = stat.st_size
                    modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()

                    # 生成OSS访问URL（如果配置了）
                    file_url = None
                    if self.storage_service:
                        file_url = self.storage_service.get_file_url(f"markdown/{rel_path}")

                    files.append(
                        {
                            "name": filename,
                            "path": str(rel_path),
                            "folder_name": folder_name,
                            "url": f"/api/markdown/file/{rel_path}",
                            "size": file_size,
                            "modified_time": modified_time,
                            "file_url": file_url,
                        }
                    )

        files.sort(key=lambda x: x["modified_time"], reverse=True)

        return files

    def get_file(self, file_path: str) -> dict:
        full_path = self.validate_path(file_path)

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"get_file called with: {repr(file_path)}")
        logger.info(f"Resolved full_path: {full_path}")
        logger.info(f"output_dir: {self.output_dir}")

        if not full_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        if not full_path.suffix == ".md":
            raise HTTPException(status_code=400, detail="只支持Markdown文件")

        file_size = full_path.stat().st_size
        self.validate_file_size(file_size)

        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()

        rel_path = full_path.relative_to(self.output_dir)
        folder_name = rel_path.parent.name if rel_path.parent else ""

        # 生成OSS访问URL（如果配置了）
        file_url = None
        if self.storage_service:
            file_url = self.storage_service.get_file_url(f"markdown/{file_path}")

        logger.info(f"Returning content for: {rel_path}")

        return {
            "content": content,
            "path": str(rel_path),
            "name": full_path.name,
            "folder_name": folder_name,
            "file_url": file_url,
        }

    def save_file(self, file_path: str, content: str) -> dict:
        full_path = self.validate_path(file_path)

        if not full_path.suffix == ".md":
            raise HTTPException(status_code=400, detail="只支持Markdown文件")

        if len(content) > self.settings.markdown_max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"内容过长（{len(content)} > {self.settings.markdown_max_file_size}）",
            )

        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        rel_path = full_path.relative_to(self.output_dir)

        # 同步到OSS（如果配置了）
        if self.storage_service:
            import asyncio
            import logging
            logger = logging.getLogger(__name__)
            try:
                # 在现有事件循环中运行异步任务
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循环正在运行，创建任务
                    asyncio.create_task(
                        self.storage_service.upload_file(
                            f"markdown/{file_path}",
                            content.encode("utf-8"),
                            metadata={"type": "markdown"}
                        )
                    )
                else:
                    # 如果事件循环未运行，直接运行
                    loop.run_until_complete(
                        self.storage_service.upload_file(
                            f"markdown/{file_path}",
                            content.encode("utf-8"),
                            metadata={"type": "markdown"}
                        )
                    )
                logger.info(f"Markdown file synced to storage: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to sync markdown to storage: {e}")

        return {
            "status": "success",
            "message": "文件保存成功",
            "path": str(rel_path),
        }
