"""
向量存储统一接口定义
提供标准化的向量存储抽象，支持多种向量数据库
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple, Union
from enum import Enum

from langchain_core.documents import Document as LangchainDocument
from src.models.document import Document


class VectorStoreBackend(str, Enum):
    """向量存储后端类型"""
    FAISS = "faiss"
    CHROMA = "chroma"
    MILVUS = "milvus"
    PINECONE = "pinecone"
    WEVIATE = "weaviate"
    QDRANT = "qdrant"


class IndexType(str, Enum):
    """索引类型"""
    FLAT = "flat"
    IVF = "ivf"
    IVF_PQ = "ivf_pq"
    HNSW = "hnsw"
    AUTO = "auto"


class BaseVectorStore(ABC):
    """
    向量存储统一接口

    所有向量存储实现必须继承此接口
    """

    def __init__(
        self,
        config: Any,
        index_name: str = "default",
        embedding_dimension: int = 1536,
        metric: str = "L2",
    ):
        """
        初始化向量存储

        Args:
            config: 配置对象
            index_name: 索引名称
            embedding_dimension: 嵌入向量维度
            metric: 距离度量 (L2, IP, COSINE)
        """
        self.config = config
        self.index_name = index_name
        self.embedding_dimension = embedding_dimension
        self.metric = metric

    @abstractmethod
    async def add_documents(
        self,
        documents: List[LangchainDocument],
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: 文档列表
            ids: 文档ID列表（可选）
            metadatas: 元数据列表（可选）

        Returns:
            添加的文档ID列表
        """
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[LangchainDocument]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            相关文档列表
        """
        pass

    @abstractmethod
    async def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[Tuple[LangchainDocument, float]]:
        """
        相似度搜索（带分数）

        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 元数据过滤条件
            **kwargs: 其他参数

        Returns:
            [(文档, 分数), ...] 列表
        """
        pass

    @abstractmethod
    async def delete_documents(
        self,
        ids: List[str],
        **kwargs
    ) -> int:
        """
        删除文档

        Args:
            ids: 要删除的文档ID列表

        Returns:
            删除的文档数量
        """
        pass

    @abstractmethod
    async def update_document(
        self,
        doc_id: str,
        document: LangchainDocument,
        **kwargs
    ) -> bool:
        """
        更新文档

        Args:
            doc_id: 文档ID
            document: 新的文档内容

        Returns:
            是否更新成功
        """
        pass

    @abstractmethod
    async def count_documents(self) -> int:
        """
        统计文档数量

        Returns:
            文档总数
        """
        pass

    @abstractmethod
    async def save_index(self) -> bool:
        """
        保存索引到磁盘

        Returns:
            是否保存成功
        """
        pass

    @abstractmethod
    async def load_index(self) -> bool:
        """
        从磁盘加载索引

        Returns:
            是否加载成功
        """
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        pass


class VectorStoreFactory:
    """
    向量存储工厂

    支持多种向量存储后端的热切换
    """

    _stores: Dict[VectorStoreBackend, type] = {}

    @classmethod
    def register_store(
        cls,
        backend: VectorStoreBackend,
        store_class: type,
    ) -> None:
        """注册向量存储实现"""
        cls._stores[backend] = store_class

    @classmethod
    def create_store(
        cls,
        backend: VectorStoreBackend,
        config: Any,
        **kwargs
    ) -> BaseVectorStore:
        """
        创建向量存储实例

        Args:
            backend: 后端类型
            config: 配置对象
            **kwargs: 其他参数

        Returns:
            向量存储实例

        Raises:
            ValueError: 不支持的后端类型
        """
        store_class = cls._stores.get(backend)
        if not store_class:
            raise ValueError(
                f"Unsupported vector store backend: {backend}. "
                f"Available backends: {list(cls._stores.keys())}"
            )

        logger.info(f"Creating vector store: {backend}")
        return store_class(config, **kwargs)

    @classmethod
    def get_available_backends(cls) -> List[VectorStoreBackend]:
        """获取可用的后端类型"""
        return list(cls._stores.keys())


class VectorStoreAdapter:
    """
    向量存储适配器

    将现有的FAISSVectorStore等适配到统一接口
    """

    def __init__(self, vector_store):
        self._vector_store = vector_store
        self._backend = self._detect_backend(vector_store)

    def _detect_backend(self, vector_store) -> VectorStoreBackend:
        """检测后端类型"""
        module_name = vector_store.__class__.__module__
        if "faiss" in module_name.lower():
            return VectorStoreBackend.FAISS
        elif "chroma" in module_name.lower():
            return VectorStoreBackend.CHROMA
        elif "milvus" in module_name.lower():
            return VectorStoreBackend.MILVUS
        else:
            return VectorStoreBackend.FAISS  # 默认

    async def add_documents(
        self,
        documents: List[LangchainDocument],
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[str]:
        """适配add_documents方法"""
        return await self._vector_store.add_documents(documents)

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[LangchainDocument]:
        """适配search方法"""
        return await self._vector_store.similarity_search(
            query, k=k, filter=filter_dict
        )

    async def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[Tuple[LangchainDocument, float]]:
        """适配search_with_score方法"""
        return await self._vector_store.similarity_search_with_score(
            query, k=k
        )

    async def delete_documents(self, ids: List[str], **kwargs) -> int:
        """适配delete_documents方法"""
        return await self._vector_store.delete_documents(ids)

    async def update_document(
        self,
        doc_id: str,
        document: LangchainDocument,
        **kwargs
    ) -> bool:
        """适配update_document方法（先删后加）"""
        await self.delete_documents([doc_id])
        added_ids = await self.add_documents([document], ids=[doc_id])
        return doc_id in added_ids

    async def count_documents(self) -> int:
        """适配count_documents方法"""
        stats = self._vector_store.get_stats()
        return stats.get("total_vectors", 0)

    async def save_index(self) -> bool:
        """适配save_index方法"""
        return await self._vector_store.save_index()

    async def load_index(self) -> bool:
        """适配load_index方法"""
        # FAISSVectorStore在__init__时自动加载
        return True

    def get_stats(self) -> Dict[str, Any]:
        """适配get_stats方法"""
        return self._vector_store.get_stats()

    async def health_check(self) -> bool:
        """适配health_check方法"""
        try:
            stats = self.get_stats()
            return stats.get("total_vectors", 0) >= 0
        except Exception:
            return False

    @property
    def backend(self) -> VectorStoreBackend:
        """获取后端类型"""
        return self._backend
