"""
存储适配器抽象接口
Author: RAG Service Team
Date: 2026-01-10
Description: 定义存储适配器的统一接口，支持本地文件系统和阿里云OSS
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, IO
from datetime import datetime


class StorageAdapter(ABC):
    """
    存储适配器抽象基类
    定义统一的存储接口，支持多种存储后端（本地、OSS等）
    """

    @abstractmethod
    async def upload_file(
        self,
        file_path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        上传文件到存储

        Args:
            file_path: 文件路径（相对于存储根目录）
            content: 文件内容（二进制）
            metadata: 文件元数据（可选）

        Returns:
            包含以下键的字典：
            - key: 存储键/路径
            - url: 访问URL（如果可用）
            - size: 文件大小
        """
        pass

    @abstractmethod
    async def download_file(self, file_path: str) -> bytes:
        """
        下载文件内容

        Args:
            file_path: 文件路径（相对于存储根目录）

        Returns:
            文件内容（二进制）

        Raises:
            FileNotFoundError: 文件不存在
        """
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径（相对于存储根目录）

        Returns:
            是否成功删除
        """
        pass

    @abstractmethod
    async def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 文件路径（相对于存储根目录）

        Returns:
            文件是否存在
        """
        pass

    @abstractmethod
    def get_file_url(self, file_path: str, expires: int = 3600) -> Optional[str]:
        """
        获取文件访问URL

        Args:
            file_path: 文件路径（相对于存储根目录）
            expires: URL过期时间（秒），仅对OSS有效

        Returns:
            访问URL，如果不支持则返回None
        """
        pass

    @abstractmethod
    async def list_files(
        self, prefix: str = "", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        列出文件

        Args:
            prefix: 文件路径前缀
            limit: 最大返回数量

        Returns:
            文件列表，每个文件包含：
            - key: 文件键/路径
            - size: 文件大小
            - last_modified: 最后修改时间
            - url: 访问URL（如果可用）
        """
        pass

    @abstractmethod
    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            file_path: 文件路径（相对于存储根目录）

        Returns:
            文件元数据字典，包含：
            - size: 文件大小
            - last_modified: 最后修改时间
            - content_type: 内容类型（如果可用）
            - etag: 文件ETag（如果可用）

        Raises:
            FileNotFoundError: 文件不存在
        """
        pass
