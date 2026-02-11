"""
本地存储适配器
Author: RAG Service Team
Date: 2026-01-10
Description: 实现本地文件系统存储，保持与现有代码的路径兼容
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import aiofiles

from src.service.storage_adapter import StorageAdapter

logger = logging.getLogger(__name__)


class LocalStorageAdapter(StorageAdapter):
    """
    本地文件系统存储适配器

    根据路径前缀自动选择存储目录：
    - uploads/ -> 用户上传文件
    - processed/ -> 处理结果文件
    - markdown/ -> Markdown编辑文件
    """

    # 路径前缀到目录的映射
    PATH_PREFIX_MAP = {
        "uploads": "upload_dir",
        "processed": "processed_dir",
        "markdown": "markdown_output_dir",
    }

    def __init__(self, settings):
        """
        初始化本地存储适配器

        Args:
            settings: 配置对象
        """
        self.settings = settings

    def _resolve_path(self, file_path: str) -> Path:
        """
        将相对路径解析为绝对路径

        根据路径前缀自动选择存储目录

        Args:
            file_path: 相对路径

        Returns:
            绝对路径
        """
        # 获取路径的第一部分作为前缀
        parts = Path(file_path).parts
        if parts and parts[0] in self.PATH_PREFIX_MAP:
            prefix = parts[0]
            attr_name = self.PATH_PREFIX_MAP[prefix]
            base_dir = Path(getattr(self.settings, attr_name))
            # 去掉前缀后的相对路径
            relative_path = str(Path(*parts[1:])) if len(parts) > 1 else ""
            return base_dir / relative_path if relative_path else base_dir

        # 默认使用上传目录
        return Path(self.settings.upload_dir) / file_path

    async def upload_file(
        self,
        file_path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        上传文件到本地存储

        Args:
            file_path: 文件路径
            content: 文件内容
            metadata: 元数据（本地存储忽略）

        Returns:
            上传结果
        """
        full_path = self._resolve_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)

        logger.info(f"File saved to local storage: {full_path}")

        return {
            "key": file_path,
            "url": None,  # 本地存储不提供URL
            "size": len(content),
        }

    async def download_file(self, file_path: str) -> bytes:
        """
        从本地存储下载文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容

        Raises:
            FileNotFoundError: 文件不存在
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, "rb") as f:
            content = await f.read()

        return content

    async def delete_file(self, file_path: str) -> bool:
        """
        从本地存储删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否成功删除
        """
        full_path = self._resolve_path(file_path)

        if full_path.exists():
            full_path.unlink()
            logger.info(f"File deleted from local storage: {full_path}")
            return True

        return False

    async def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            文件是否存在
        """
        full_path = self._resolve_path(file_path)
        return full_path.exists()

    def get_file_url(self, file_path: str, expires: int = 3600) -> Optional[str]:
        """
        获取文件访问URL

        本地存储不提供URL，返回None

        Args:
            file_path: 文件路径
            expires: 过期时间（本地存储忽略）

        Returns:
            None
        """
        return None

    async def list_files(
        self, prefix: str = "", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出文件

        Args:
            prefix: 路径前缀
            limit: 最大返回数量

        Returns:
            文件列表
        """
        base_path = self._resolve_path(prefix) if prefix else Path(self.settings.upload_dir)

        if not base_path.exists():
            return []

        files = []
        for file_path in base_path.rglob("*"):
            if file_path.is_file():
                if len(files) >= limit:
                    break

                stat = file_path.stat()
                relative_path = file_path.relative_to(base_path)

                files.append(
                    {
                        "key": str(relative_path),
                        "size": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "url": None,
                    }
                )

        return files

    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            file_path: 文件路径

        Returns:
            文件元数据

        Raises:
            FileNotFoundError: 文件不存在
        """
        full_path = self._resolve_path(file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = full_path.stat()

        return {
            "size": stat.st_size,
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "content_type": None,  # 本地存储不存储内容类型
            "etag": None,  # 本地存储不提供ETag
        }
