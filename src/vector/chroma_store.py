"""
Chroma向量存储实现
基于ChromaDB的向量存储
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document as LangchainDocument

from .base import BaseVectorStore, VectorStoreBackend

logger = logging.getLogger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB向量存储实现

    优势:
    - 内置元数据过滤
    - 持久化存储
    - 分布式支持
    - 易于部署和扩展
    """

    def __init__(
        self,
        config: Any,
        index_name: str = "rag_service",
        embedding_dimension: int = 1536,
        metric: str = "L2",
        persist_directory: Optional[str] = None,
    ):
        super().__init__(config, index_name, embedding_dimension, metric)

        # Chroma配置
        self.persist_directory = persist_directory or config.chroma_persist_dir

        # 创建Chroma客户端
        self._client = chromadb.Client(
            settings=ChromaSettings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=self.persist_directory,
            )
        )

        # 创建或加载集合
        self._collection = self._client.get_or_create_collection(
            name=self.index_name,
            metadata={"hnsw:space": metric.lower()}
        )

        logger.info(f"ChromaDB initialized: {self.index_name} at {self.persist_directory}")

    async def add_documents(
        self,
        documents: List[LangchainDocument],
        ids: Optional[List[str]] = None,
        metadatas: Optional[List[Dict]] = None,
    ) -> List[str]:
        """添加文档"""
        try:
            # 准备文本和元数据
            texts = [doc.page_content for doc in documents]
            embeddings = await self._get_embeddings(texts)

            if ids is None:
                ids = [f"doc_{i}_{hash(texts[i])}" for i in range(len(texts))]

            if metadatas is None:
                metadatas = [doc.metadata for doc in documents]

            # 添加到Chroma
            self._collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            logger.info(f"Added {len(ids)} documents to ChromaDB")
            return ids

        except Exception as e:
            logger.error(f"Failed to add documents to ChromaDB: {e}")
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
            # 向量化查询
            query_embedding = await self._get_embedding(query)

            # 构建where子句
            where = filter_dict if filter_dict else None

            # 查询Chroma
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
            )

            # 转换结果
            documents = []
            for i, doc_id in enumerate(results['ids'][0]):
                doc = LangchainDocument(
                    page_content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i] if 'metadatas' in results else {}
                )
                documents.append(doc)

            logger.debug(f"ChromaDB search returned {len(documents)} results")
            return documents

        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
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
            where = filter_dict if filter_dict else None

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
            )

            # Chroma返回距离，需要转换为相似度分数
            documents_scores = []
            for i, doc_id in enumerate(results['ids'][0]):
                doc = LangchainDocument(
                    page_content=results['documents'][0][i],
                    metadata=results['metadatas'][0][i] if 'metadatas' in results else {}
                )
                # 距离转相似度（L2距离: 1/(1+distance)）
                if 'distances' in results:
                    distance = results['distances'][0][i]
                    score = 1.0 / (1.0 + distance)
                else:
                    score = 1.0
                documents_scores.append((doc, score))

            return documents_scores

        except Exception as e:
            logger.error(f"ChromaDB search with scores failed: {e}")
            return []

    async def delete_documents(self, ids: List[str], **kwargs) -> int:
        """删除文档"""
        try:
            self._collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from ChromaDB")
            return len(ids)
        except Exception as e:
            logger.error(f"Failed to delete documents from ChromaDB: {e}")
            return 0

    async def update_document(
        self,
        doc_id: str,
        document: LangchainDocument,
        **kwargs
    ) -> bool:
        """更新文档（先删后加）"""
        await self.delete_documents([doc_id])
        added_ids = await self.add_documents([document], ids=[doc_id])
        return doc_id in added_ids

    async def count_documents(self) -> int:
        """统计文档数量"""
        return self._collection.count()

    async def save_index(self) -> bool:
        """保存索引（Chroma自动持久化）"""
        # ChromaDB自动持久化，无需手动保存
        return True

    async def load_index(self) -> bool:
        """加载索引（Chroma启动时自动加载）"""
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "backend": VectorStoreBackend.CHROMA.value,
            "index_name": self.index_name,
            "total_vectors": self._collection.count(),
            "persist_directory": self.persist_directory,
            "metric": self.metric,
        }

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            self._collection.count()
            return True
        except Exception:
            return False

    async def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入"""
        from src.api.dependencies import get_embedding_service
        embedding_service = get_embedding_service()
        return await embedding_service.embed_text(text)

    async def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本嵌入"""
        from src.api.dependencies import get_embedding_service
        embedding_service = get_embedding_service()
        return await embedding_service.embed_documents(texts)
