import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import HTTPException

from config import settings


class MarkdownService:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.output_dir = Path(settings_obj.markdown_output_dir)

    def validate_path(self, file_path: str) -> Path:
        output_dir = self.output_dir.resolve()
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

        for root, dirs, filenames in os.walk(self.output_dir):
            for filename in filenames:
                if filename.endswith(".md"):
                    full_path = Path(root) / filename
                    rel_path = full_path.relative_to(self.output_dir)
                    folder_name = rel_path.parent.name if rel_path.parent else ""

                    stat = full_path.stat()
                    file_size = stat.st_size
                    modified_time = datetime.fromtimestamp(stat.st_mtime).isoformat()

                    files.append(
                        {
                            "name": filename,
                            "path": str(rel_path),
                            "folder_name": folder_name,
                            "url": f"/api/markdown/file/{rel_path}",
                            "size": file_size,
                            "modified_time": modified_time,
                        }
                    )

        files.sort(key=lambda x: x["modified_time"], reverse=True)

        return files

    def get_file(self, file_path: str) -> dict:
        full_path = self.validate_path(file_path)

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

        return {
            "content": content,
            "path": str(rel_path),
            "name": full_path.name,
            "folder_name": folder_name,
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

        return {
            "status": "success",
            "message": "文件保存成功",
            "path": str(rel_path),
        }
