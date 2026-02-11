"""
统一存储服务
Author: RAG Service Team
Date: 2026-01-10
Description: 根据配置选择存储适配器，支持自动回退机制
"""

import logging
from typing import Optional, List, Dict, Any

from src.service.storage_adapter import StorageAdapter
from src.service.local_storage_adapter import LocalStorageAdapter

logger = logging.getLogger(__name__)

# 尝试导入OSS适配器（如果oss2可用）
try:
    from src.service.oss_storage_adapter import OSSStorageAdapter
    OSS_AVAILABLE = True
except ImportError:
    OSS_AVAILABLE = False
    logger.warning("oss2 not available, OSS storage disabled")


class StorageService:
    """
    统一存储服务

    根据 storage_type 配置选择适配器：
    - local: 本地文件系统
    - oss: 阿里云OSS

    支持自动回退机制：OSS失败时自动使用本地存储
    """

    def __init__(self, settings):
        """
        初始化存储服务

        Args:
            settings: 配置对象
        """
        self.settings = settings
        self.storage_type = settings.storage_type.lower()
        self.primary_adapter: Optional[StorageAdapter] = None
        self.fallback_adapter: Optional[StorageAdapter] = None
        self.using_fallback = False

        self._init_adapters()

    def _init_adapters(self):
        """
        初始化存储适配器

        根据配置选择主适配器和回退适配器
        """
        if self.storage_type == "oss":
            if not OSS_AVAILABLE:
                logger.warning("OSS requested but oss2 not available, falling back to local")
                self.primary_adapter = LocalStorageAdapter(self.settings)
                logger.info("Storage adapter initialized: Local (fallback)")
                return

            # 尝试初始化OSS适配器
            try:
                self.primary_adapter = OSSStorageAdapter(self.settings)
                logger.info("Storage adapter initialized: OSS")

                # 如果启用了回退，初始化本地适配器作为备用
                if self.settings.oss_fallback_to_local:
                    self.fallback_adapter = LocalStorageAdapter(self.settings)
                    logger.info("Fallback storage adapter initialized: Local")
            except Exception as e:
                logger.error(f"Failed to initialize OSS adapter: {e}")
                if self.settings.oss_fallback_to_local:
                    logger.warning("Falling back to local storage")
                    self.primary_adapter = LocalStorageAdapter(self.settings)
                    self.using_fallback = True
                else:
                    raise
        else:
            # 使用本地存储
            self.primary_adapter = LocalStorageAdapter(self.settings)
            logger.info("Storage adapter initialized: Local")

    async def _execute_with_fallback(self, method_name: str, *args, **kwargs):
        """
        执行操作，支持自动回退

        Args:
            method_name: 方法名
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            方法执行结果

        Raises:
            Exception: 主适配器和回退适配器都失败时抛出异常
        """
        # 尝试使用主适配器
        try:
            method = getattr(self.primary_adapter, method_name)
            return await method(*args, **kwargs)
        except Exception as e:
            logger.error(f"Primary adapter failed ({method_name}): {e}")

            # 如果有回退适配器，尝试使用回退
            if self.fallback_adapter:
                logger.warning(f"Attempting fallback to {type(self.fallback_adapter).__name__}")
                try:
                    self.using_fallback = True
                    method = getattr(self.fallback_adapter, method_name)
                    result = await method(*args, **kwargs)
                    logger.info(f"Fallback adapter succeeded ({method_name})")
                    return result
                except Exception as fallback_error:
                    logger.error(f"Fallback adapter also failed ({method_name}): {fallback_error}")
                    raise

            # 没有回退适配器，直接抛出原始异常
            raise

    async def upload_file(
        self,
        file_path: str,
        content: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        上传文件

        Args:
            file_path: 文件路径
            content: 文件内容
            metadata: 元数据

        Returns:
            上传结果，包含storage_type指示实际使用的存储
        """
        result = await self._execute_with_fallback(
            "upload_file", file_path, content, metadata
        )

        # 添加实际使用的存储类型
        result["storage_type"] = "local" if self.using_fallback else self.storage_type

        return result

    async def download_file(self, file_path: str) -> bytes:
        """
        下载文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容
        """
        return await self._execute_with_fallback("download_file", file_path)

    async def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        如果同时存在OSS和本地文件，会尝试删除两者

        Args:
            file_path: 文件路径

        Returns:
            是否成功删除
        """
        # 尝试从主适配器删除
        primary_success = await self._execute_with_fallback("delete_file", file_path)

        # 如果有回退适配器且不是当前使用的适配器，也尝试删除
        fallback_success = True
        if self.fallback_adapter and not self.using_fallback:
            try:
                fallback_success = await self.fallback_adapter.delete_file(file_path)
            except Exception as e:
                logger.warning(f"Failed to delete from fallback adapter: {e}")
                fallback_success = False

        return primary_success or fallback_success

    async def file_exists(self, file_path: str) -> bool:
        """
        检查文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            文件是否存在
        """
        return await self._execute_with_fallback("file_exists", file_path)

    def get_file_url(self, file_path: str, expires: int = 3600) -> Optional[str]:
        """
        获取文件访问URL

        Args:
            file_path: 文件路径
            expires: URL过期时间（秒）

        Returns:
            访问URL
        """
        # 同步方法，不需要异步处理
        if self.using_fallback and self.fallback_adapter:
            return self.fallback_adapter.get_file_url(file_path, expires)
        return self.primary_adapter.get_file_url(file_path, expires)

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
        return await self._execute_with_fallback("list_files", prefix, limit)

    async def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件元数据

        Args:
            file_path: 文件路径

        Returns:
            文件元数据
        """
        return await self._execute_with_fallback("get_file_metadata", file_path)

    def get_storage_type(self) -> str:
        """
        获取当前使用的存储类型

        Returns:
            存储类型（local或oss）
        """
        return "local" if self.using_fallback else self.storage_type

    def is_using_fallback(self) -> bool:
        """
        是否正在使用回退存储

        Returns:
            是否使用回退存储
        """
        return self.using_fallback
