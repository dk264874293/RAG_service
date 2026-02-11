"""
Milvus向量存储实现
基于Milvus的分布式向量存储
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)
from langchain_core.documents import Document as LangchainDocument

from .base import BaseVectorStore, VectorStoreBackend

logger = logging.getLogger(__name__)


class MilvusVectorStore(BaseVectorStore):
    """
    Milvus向量存储实现

    优势:
    - 分布式架构
    - 水平扩展能力
    - 高性能索引
    - 支持多种索引类型
    """

    def __init__(
        self,
        config: Any,
        index_name: str = "rag_service",
        embedding_dimension: int = 1536,
        metric: str = "L2",
        host: str = "localhost",
        port: int = 19530,
    ):
        super().__init__(config, index_name, embedding_dimension, metric)

        self.host = host
        self.port = port

        # 连接Milvus
        self._connect()

        # 创建或获取集合
        self._ensure_collection()

        logger.info(f"Milvus initialized: {self.index_name} at {host}:{port}")

    def _connect(self) -> None:
        """连接Milvus服务器"""
        connections.connect(
            alias="default",
            host=self.host,
            port=self.port,
        )
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")

    def _ensure_collection(self) -> None:
        """确保集合存在"""
        if utility.has_collection(self.index_name):
            self._collection = Collection(self.index_name)
            logger.info(f"Loaded existing collection: {self.index_name}")
        else:
            self._create_collection()
            logger.info(f"Created new collection: {self.index_name}")

    def _create_collection(self) -> None:
        """创建新集合"""
        # 定义字段
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dimension),
        ]

        # 创建schema
        schema = CollectionSchema(
            fields=fields,
            description="RAG service documents",
            enable_dynamic_field=True
        )

        # 创建集合
        self._collection = Collection(
            name=self.index_name,
            schema=schema
        )

        # 创建索引
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": self.metric,
            "params": {"nlist": 128}
        }
        self._collection.create_index(
            field_name="embedding",
            index_params=index_params
        )

    async def add_documents(
        self,
        documents: List[LangchainDocument],
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[str]:
        """添加文档"""
        try:
            # 准备数据
            if ids is None:
                ids = [f"doc_{i}_{hash(doc.page_content)}" for i, doc in enumerate(documents)]

            data = [
                {
                    "id": ids[i],
                    "content": doc.page_content,
                    "embedding": await self._get_embedding(doc.page_content),
                    **(metadatas[i] if metadatas else {})
                }
                for i, doc in enumerate(documents)
            ]

            # 插入数据
            self._collection.insert(data)

            logger.info(f"Added {len(ids)} documents to Milvus")
            return ids

        except Exception as e:
            logger.error(f"Failed to add documents to Milvus: {e}")
            raise

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[LangchainDocument]:
        """搜索"""
        try:
            query_embedding = await self._get_embedding(query)

            # 构建表达式（用于过滤）
            expr = self._build_filter_expression(filter_dict)

            # 搜索
            results = self._collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param={"metric_type": self.metric, "params": {"nprobe": 10}},
                limit=k,
                expr=expr,
                output_fields=["content", "id"],
            )

            # 转换结果
            documents = []
            for result in results[0]:
                doc = LangchainDocument(
                    page_content=result.entity.get("content", ""),
                    metadata={"doc_id": result.id, **result.entity}
                )
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Milvus search failed: {e}")
            return []

    async def search_with_score(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[Tuple[LangchainDocument, float]]:
        """搜索（带分数）"""
        try:
            query_embedding = await self._get_embedding(query)
            expr = self._build_filter_expression(filter_dict)

            results = self._collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param={"metric_type": self.metric, "params": {"nprobe": 10}},
                limit=k,
                expr=expr,
                output_fields=["content", "id"],
            )

            documents_scores = []
            for result in results[0]:
                doc = LangchainDocument(
                    page_content=result.entity.get("content", ""),
                    metadata={"doc_id": result.id, **result.entity}
                )
                score = 1.0 - result.distance  # 距离转相似度
                documents_scores.append((doc, score))

            return documents_scores

        except Exception as e:
            logger.error(f"Milvus search with scores failed: {e}")
            return []

    async def delete_documents(self, ids: List[str], **kwargs) -> int:
        """删除文档"""
        try:
            self._collection.delete(ids)
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to delete documents from Milvus: {e}")
            return 0

    async def update_document(
        self,
        doc_id: str,
        document: LangchainDocument,
        **kwargs
    ) -> bool:
        """更新文档"""
        await self.delete_documents([doc_id])
        added_ids = await self.add_documents([document], ids=[doc_id])
        return doc_id in added_ids

    async def count_documents(self) -> int:
        """统计文档数量"""
        return self._collection.num_entities

    async def save_index(self) -> bool:
        """保存索引（Milvus自动持久化）"""
        return True

    async def load_index(self) -> bool:
        """加载索引"""
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "backend": VectorStoreBackend.MILVUS.value,
            "index_name": self.index_name,
            "total_vectors": self._collection.num_entities,
            "metric": self.metric,
        }

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            connections.get_connection_addr("default")
            return True
        except Exception:
            return False

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        from src.api.dependencies import get_embedding_service
        embedding_service = get_embedding_service()
        return await embedding_service.embed_text(text)

    def _build_filter_expression(self, filter_dict: Optional[Dict]) -> Optional[str]:
        """构建Milvus过滤表达式"""
        if not filter_dict:
            return None

        expressions = []
        for key, value in filter_dict.items():
            if isinstance(value, str):
                expressions.append(f'{key} == "{value}"')
            elif isinstance(value, (int, float)):
                expressions.append(f'{key} == {value}')
            elif isinstance(value, bool):
                expressions.append(f'{key} == {str(value).lower()}')

        return " and ".join(expressions) if expressions else None
