"""
分代索引存储：统一管理Hot和Cold两个FAISS索引
解决软删除导致的内存泄漏和性能问题
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from langchain_core.documents import Document as LangchainDocument

from .hot_faiss_index import HotFAISSIndex
from .cold_faiss_index import ColdFAISSIndex
from .routing_table import RoutingTable
from .embed_service import EmbeddingService

logger = logging.getLogger(__name__)


class GenerationalIndexStore:
    """
    分代索引存储

    核心思想：
    - Hot Index: 活跃数据，支持物理删除，使用IVF-PQ
    - Cold Index: 归档数据，只读优化，使用HNSW
    - 自动归档：定期将旧文档从Hot迁移到Cold
    - 统一搜索：RRF融合两个索引的结果

    优势：
    1. 无内存泄漏：Hot Index支持物理删除
    2. 搜索性能稳定：双索引并行，RRF融合
    3. 无需全量重建：仅Cold Index需要定期重建
    4. 无限扩展：Cold Index可以无限增长
    """

    def __init__(
        self,
        config,
        embedding_service: EmbeddingService,
        routing_table: Optional[RoutingTable] = None
    ):
        self.config = config
        self.embedding = embedding_service

        # 路由表
        if routing_table:
            self.routing_table = routing_table
        else:
            routing_db_path = f"{config.faiss_index_path}/routing.db"
            self.routing_table = RoutingTable(routing_db_path)

        # Hot Index
        hot_config = {
            "max_size": getattr(config, "hot_index_max_size", 1000000),
            "index_type": getattr(config, "hot_index_type", "IVFPQ"),
            "nlist": getattr(config, "hot_index_nlist", 100),
            "nprobe": getattr(config, "hot_index_nprobe", 10),
        }
        self.hot_index = HotFAISSIndex(
            index_path=f"{config.faiss_index_path}/hot",
            embedding_service=embedding_service,
            **hot_config
        )

        # Cold Index
        cold_config = {
            "index_type": getattr(config, "cold_index_type", "HNSW"),
            "M": getattr(config, "cold_index_m", 32),
            "efSearch": getattr(config, "cold_index_ef_search", 64),
        }
        self.cold_index = ColdFAISSIndex(
            index_path=f"{config.faiss_index_path}/cold",
            embedding_service=embedding_service,
            **cold_config
        )

        # 归档管理器
        self.archive_age_days = getattr(config, "archive_age_days", 30)

        # 搜索权重
        self.hot_weight = getattr(config, "hot_search_weight", 0.7)
        self.cold_weight = getattr(config, "cold_search_weight", 0.3)

        logger.info("GenerationalIndexStore initialized")

    async def add_documents(
        self,
        docs: List[LangchainDocument],
        file_id: Optional[str] = None
    ) -> List[str]:
        """
        添加文档到活跃索引

        Args:
            docs: 文档列表
            file_id: 文件ID（可选）

        Returns:
            文档ID列表
        """
        if not docs:
            return []

        # 添加到Hot Index
        doc_ids = await self.hot_index.add_documents(docs)

        # 更新路由表
        for doc_id in doc_ids:
            self.routing_table.set_location(doc_id, "hot", file_id)

        logger.info(f"Added {len(docs)} documents to hot index")
        return doc_ids

    async def delete_documents(self, file_id: str) -> int:
        """
        删除文档（根据file_id）

        Args:
            file_id: 文件ID

        Returns:
            删除的文档数
        """
        # 查询该file_id的所有文档及位置
        locations = self.routing_table.get_by_file_id(file_id)

        if not locations:
            logger.warning(f"No documents found for file_id={file_id}")
            return 0

        deleted_count = 0

        for doc_id, index_type in locations:
            if index_type == "hot":
                # Hot Index: 物理删除
                deleted_count += await self.hot_index.remove_doc(doc_id)
            else:
                # Cold Index: 软删除
                deleted_count += await self.cold_index.soft_delete(doc_id)

            # 从路由表删除
            self.routing_table.delete(doc_id)

        logger.info(f"Deleted {deleted_count} documents for file_id={file_id}")
        return deleted_count

    async def delete_by_doc_ids(self, doc_ids: List[str]) -> int:
        """
        根据文档ID列表删除

        Args:
            doc_ids: 文档ID列表

        Returns:
            删除的文档数
        """
        deleted_count = 0

        for doc_id in doc_ids:
            index_type = self.routing_table.get_location(doc_id)

            if index_type == "hot":
                deleted_count += await self.hot_index.remove_doc(doc_id)
            elif index_type == "cold":
                deleted_count += await self.cold_index.soft_delete(doc_id)

            self.routing_table.delete(doc_id)

        return deleted_count

    async def search(
        self,
        query: str,
        k: int = 10,
        filter_dict: Optional[Dict] = None
    ) -> List[LangchainDocument]:
        """
        统一搜索接口

        Args:
            query: 查询文本
            k: 返回结果数
            filter_dict: 元数据过滤

        Returns:
            文档列表
        """
        # 计算每个索引的召回数量
        hot_k = int(k * 1.2)  # Hot Index召回1.2倍
        cold_k = int(k * 0.8)  # Cold Index召回0.8倍

        # 并行搜索两个索引
        hot_results, cold_results = await asyncio.gather(
            self.hot_index.search(query, k=hot_k, filter_dict=filter_dict),
            self.cold_index.search(query, k=cold_k, filter_dict=filter_dict)
        )

        # RRF融合
        fused_results = self._reciprocal_rank_fusion(
            hot_results=hot_results,
            cold_results=cold_results,
            k=k
        )

        return fused_results[:k]

    async def search_with_scores(
        self,
        query: str,
        k: int = 10
    ) -> List[tuple[LangchainDocument, float]]:
        """搜索并返回融合分数"""
        hot_k = int(k * 1.2)
        cold_k = int(k * 0.8)

        hot_results, cold_results = await asyncio.gather(
            self.hot_index.search_with_score(query, k=hot_k),
            self.cold_index.search_with_score(query, k=cold_k)
        )

        # 融合结果
        return self._fuse_with_scores(
            hot_results=hot_results,
            cold_results=cold_results,
            k=k
        )

    def _reciprocal_rank_fusion(
        self,
        hot_results: List[LangchainDocument],
        cold_results: List[LangchainDocument],
        k: int = 10,
        constant: int = 60
    ) -> List[LangchainDocument]:
        """
        RRF (Reciprocal Rank Fusion) 融合算法

        公式：score(d) = sum(weight / (rank + constant))
        """
        scores: Dict[str, tuple[LangchainDocument, float]] = {}

        # Hot Index结果
        for rank, doc in enumerate(hot_results):
            doc_id = doc.metadata.get("doc_id", str(id(doc)))
            score = self.hot_weight / (rank + constant)
            if doc_id in scores:
                scores[doc_id] = (doc, scores[doc_id][1] + score)
            else:
                scores[doc_id] = (doc, score)

        # Cold Index结果
        for rank, doc in enumerate(cold_results):
            doc_id = doc.metadata.get("doc_id", str(id(doc)))
            score = self.cold_weight / (rank + constant)
            if doc_id in scores:
                scores[doc_id] = (doc, scores[doc_id][1] + score)
            else:
                scores[doc_id] = (doc, score)

        # 按分数排序
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x[1],
            reverse=True
        )

        return [doc for doc, _ in sorted_results]

    def _fuse_with_scores(
        self,
        hot_results: List[tuple[LangchainDocument, float]],
        cold_results: List[tuple[LangchainDocument, float]],
        k: int
    ) -> List[tuple[LangchainDocument, float]]:
        """融合带分数的结果"""
        scores: Dict[str, tuple[LangchainDocument, float]] = {}

        # Hot Index结果（归一化分数）
        if hot_results:
            max_score = max(score for _, score in hot_results)
            for doc, score in hot_results:
                doc_id = doc.metadata.get("doc_id", str(id(doc)))
                normalized_score = (score / max_score) * self.hot_weight
                if doc_id in scores:
                    scores[doc_id] = (doc, scores[doc_id][1] + normalized_score)
                else:
                    scores[doc_id] = (doc, normalized_score)

        # Cold Index结果（归一化分数）
        if cold_results:
            max_score = max(score for _, score in cold_results)
            for doc, score in cold_results:
                doc_id = doc.metadata.get("doc_id", str(id(doc)))
                normalized_score = (score / max_score) * self.cold_weight
                if doc_id in scores:
                    scores[doc_id] = (doc, scores[doc_id][1] + normalized_score)
                else:
                    scores[doc_id] = (doc, normalized_score)

        # 按分数排序
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        return sorted_results

    async def archive_old_documents(self, force: bool = False) -> Dict[str, Any]:
        """
        归档旧文档

        Args:
            force: 是否强制归档（忽略时间限制）

        Returns:
            归档统计
        """
        logger.info("Starting archive task...")

        # 1. 找出需要归档的文档
        if force:
            # 强制归档：将所有Hot文档归档
            docs_to_archive = self.routing_table.get_all_by_type("hot")
        else:
            # 按时间归档
            docs_to_archive = self.routing_table.get_old_documents(
                index_type="hot",
                days=self.archive_age_days
            )

        if not docs_to_archive:
            logger.info("No documents to archive")
            return {
                "archived_count": 0,
                "hot_size_after": self.hot_index.get_size(),
                "cold_size_after": self.cold_index.get_size(),
            }

        logger.info(f"Found {len(docs_to_archive)} documents to archive")

        # 2. 从Hot Index读取文档
        docs_to_migrate = []
        for doc_id in docs_to_archive:
            doc = self.hot_index.vector_store.docstore.search(doc_id)
            if doc:
                docs_to_migrate.append(doc)

        if not docs_to_migrate:
            logger.warning("No valid documents to migrate")
            return {"archived_count": 0}

        # 3. 添加到Cold Index
        cold_doc_ids = await self.cold_index.add_documents(docs_to_migrate)

        # 4. 从Hot Index删除
        for doc_id in docs_to_archive:
            await self.hot_index.remove_doc(doc_id)

        # 5. 更新路由表
        self.routing_table.migrate_to_cold(docs_to_archive)

        logger.info(f"Archived {len(docs_to_archive)} documents")

        return {
            "archived_count": len(docs_to_archive),
            "hot_size_before": self.hot_index.get_size() + len(docs_to_archive),
            "hot_size_after": self.hot_index.get_size(),
            "cold_size_before": self.cold_index.get_size() - len(docs_to_archive),
            "cold_size_after": self.cold_index.get_size(),
        }

    async def rebuild_cold_index(self) -> bool:
        """重建Cold Index（移除软删除的文档）"""
        logger.info("Rebuilding cold index...")
        success = await self.cold_index.rebuild()
        if success:
            logger.info("Cold index rebuilt successfully")
        else:
            logger.error("Failed to rebuild cold index")
        return success

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        routing_stats = self.routing_table.get_stats()

        return {
            "hot_index": self.hot_index.get_stats(),
            "cold_index": self.cold_index.get_stats(),
            "routing_table": routing_stats,
            "archive_config": {
                "age_days": self.archive_age_days,
                "hot_weight": self.hot_weight,
                "cold_weight": self.cold_weight,
            },
            "total_documents": routing_stats["total"],
            "needs_archive": self.hot_index.get_size() > (
                self.hot_index.max_size * 0.8
            ),
            "needs_cold_rebuild": self.cold_index.should_rebuild()[0],
        }

    async def save_all(self):
        """保存所有索引"""
        self.hot_index._save()
        self.cold_index._save()
        logger.info("All indices saved")

    async def close(self):
        """关闭资源"""
        self.routing_table.close()
        logger.info("GenerationalIndexStore closed")
