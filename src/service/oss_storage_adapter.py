"""
阿里云OSS存储适配器
Author: RAG Service Team
Date: 2026-01-10
Description: 实现阿里云OSS对象存储，支持元数据、预签名URL和批量操作
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import oss2

from src.service.storage_adapter import StorageAdapter

logger = logging.getLogger(__name__)


class OSSStorageAdapter(StorageAdapter):
    """
    阿里云OSS存储适配器

    使用oss2 SDK实现对象存储操作
    """

    def __init__(self, settings):
        """
        初始化OSS存储适配器

        Args:
            settings: 配置对象，需包含：
                - oss_access_key_id
                - oss_access_key_secret
                - oss_endpoint
                - oss_bucket_name
                - oss_prefix
                - oss_timeout
                - oss_presign_url_expire
        """
        self.settings = settings
        self.prefix = settings.oss_prefix.rstrip("/")

        # 创建OSS认证对象
        auth = oss2.Auth(
            settings.oss_access_key_id, settings.oss_access_key_secret
        )

        # 创建Bucket对象
        self.bucket = oss2.Bucket(
            auth,
            settings.oss_endpoint,
            settings.oss_bucket_name,
            connect_timeout=settings.oss_timeout,
        )

        # 验证连接
        try:
            self.bucket.get_bucket_info()
            logger.info(f"OSS storage initialized: {settings.oss_bucket_name}")
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS connection failed: {e}")
            raise

    def _normalize_key(self, file_path: str) -> str:
        """
        标准化文件键，添加前缀

        Args:
            file_path: 原始文件路径

        Returns:
            带前缀的OSS键
        """
        # 去掉开头的斜杠
        key = file_path.lstrip("/")

        # 添加前缀
        if self.prefix:
            key = f"{self.prefix}/{key}"

        return key

    async def upload_file(
        self,
        file_path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        上传文件到OSS

        Args:
            file_path: 文件路径
            content: 文件内容
            metadata: 文件元数据

        Returns:
            上传结果
        """
        key = self._normalize_key(file_path)

        # 准备OSS headers
        headers = {}
        if metadata:
            # 将自定义元数据添加到headers
            for k, v in metadata.items():
                headers[f"x-oss-meta-{k}"] = str(v)

        try:
            result = self.bucket.put_object(key, content, headers=headers)
            logger.info(f"File uploaded to OSS: {key}")

            return {
                "key": key,
                "url": f"https://{self.settings.oss_bucket_name}.{self.settings.oss_endpoint.replace('https://', '')}/{key}",
                "size": len(content),
            }
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS upload failed for {key}: {e}")
            raise

    async def download_file(self, file_path: str) -> bytes:
        """
        从OSS下载文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容

        Raises:
            FileNotFoundError: 文件不存在
        """
        key = self._normalize_key(file_path)

        try:
            result = self.bucket.get_object(key)
            content = result.read()
            logger.info(f"File downloaded from OSS: {key}")
            return content
        except oss2.exceptions.NoSuchKey:
            raise FileNotFoundError(f"File not found in OSS: {file_path}")
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS download failed for {key}: {e}")
            raise

    async def delete_file(self, file_path: str) -> bool:
        """
        从OSS删除文件

        Args:
            file_path: 文件路径

        Returns:
            是否成功删除
        """
        key = self._normalize_key(file_path)

        try:
            self.bucket.delete_object(key)
            logger.info(f"File deleted from OSS: {key}")
            return True
        except oss2.exceptions.NoSuchKey:
            logger.warning(f"File not found in OSS (already deleted?): {key}")
            return False
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS delete failed for {key}: {e}")
            raise

    async def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            文件是否存在
        """
        key = self._normalize_key(file_path)

        try:
            self.bucket.head_object(key)
            return True
        except oss2.exceptions.NoSuchKey:
            return False
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS head_object failed for {key}: {e}")
            return False

    def get_file_url(self, file_path: str, expires: int = 3600) -> Optional[str]:
        """
        获取文件预签名URL

        Args:
            file_path: 文件路径
            expires: URL过期时间（秒）

        Returns:
            预签名URL
        """
        key = self._normalize_key(file_path)

        try:
            url = self.bucket.sign_url("GET", key, expires)
            return url
        except oss2.exceptions.OssError as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
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
        oss_prefix = self._normalize_key(prefix) if prefix else self.prefix + "/"

        try:
            files = []
            for obj in oss2.ObjectIterator(self.bucket, prefix=oss_prefix, max_keys=limit):
                if obj.is_dir():
                    continue

                files.append(
                    {
                        "key": obj.key,
                        "size": obj.size,
                        "last_modified": obj.last_modified.isoformat(),
                        "url": f"https://{self.settings.oss_bucket_name}.{self.settings.oss_endpoint.replace('https://', '')}/{obj.key}",
                    }
                )

            return files
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS list failed for prefix {oss_prefix}: {e}")
            raise

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
        key = self._normalize_key(file_path)

        try:
            result = self.bucket.head_object(key)

            # 提取自定义元数据
            custom_metadata = {}
            for k, v in result.headers.items():
                if k.startswith("x-oss-meta-"):
                    meta_key = k.replace("x-oss-meta-", "")
                    custom_metadata[meta_key] = v

            return {
                "size": result.content_length,
                "last_modified": datetime.fromtimestamp(
                    result.last_modified
                ).isoformat(),
                "content_type": result.content_type,
                "etag": result.etag,
                "metadata": custom_metadata,
            }
        except oss2.exceptions.NoSuchKey:
            raise FileNotFoundError(f"File not found in OSS: {file_path}")
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS get metadata failed for {key}: {e}")
            raise

    async def batch_delete_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """
        批量删除文件

        Args:
            file_paths: 文件路径列表

        Returns:
            删除结果，包含success和failed列表
        """
        keys = [self._normalize_key(path) for path in file_paths]

        try:
            result = self.bucket.batch_delete_objects(keys)
            logger.info(f"Batch delete from OSS: {len(keys)} files")

            return {
                "success": [k for k in keys if k not in result.failed_keys],
                "failed": result.failed_keys,
            }
        except oss2.exceptions.OssError as e:
            logger.error(f"OSS batch delete failed: {e}")
            raise
