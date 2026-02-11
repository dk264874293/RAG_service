"""
优化的 FAISS Vector Store
支持自适应索引选择、性能监控和在线迁移
"""

import os
import logging
import pickle
import time
import numpy as np
from typing import List, Tuple, Dict, Any, Optional, Set
from collections import deque
from datetime import datetime, timedelta

import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore import InMemoryDocstore
from langchain_core.documents import Document as LangchainDocument

from .faiss_index_factory import FAISSIndexFactory
from .adaptive_index_selector import AdaptiveIndexSelector

logger = logging.getLogger(__name__)


class OptimizedFAISSVectorStore:
    """
    优化的 FAISS 向量存储

    核心改进:
    1. 使用索引工厂支持多种索引类型
    2. 自适应索引选择
    3. 性能监控和自动优化建议
    4. 配置驱动的索引管理
    """

    def __init__(self, config_obj, embedding_service):
        self.config = config_obj
        self.embedding_service = embedding_service

        # 路径配置
        self.index_path = config_obj.faiss_index_path
        self.deleted_ids_file = os.path.join(
            os.path.dirname(self.index_path), "deleted_ids.pkl"
        )

        # 核心组件
        self.vector_store: Optional[FAISS] = None
        self.index_type: Optional[str] = None
        self.index_config: Dict[str, Any] = {}

        # 软删除管理
        self.deleted_ids: Set[str] = set()

        # 性能监控
        self.performance_monitor = IndexPerformanceMonitor()

        # 自适应选择器
        auto_select = getattr(config_obj, "faiss_index_auto_select", False)
        self.adaptive_selector = AdaptiveIndexSelector(
            config={
                "memory_limit_mb": getattr(config_obj, "faiss_index_memory_limit_mb", 4096),
                "target_latency_ms": getattr(config_obj, "faiss_index_target_latency_ms", 100),
                "prefer_accuracy": True,
            }
        ) if auto_select else None

        self._initialize()

    def _initialize(self):
        """初始化或加载索引"""
        try:
            if os.path.exists(self.index_path):
                self._load_existing_index()
            else:
                self._create_new_index()
            self._load_deleted_ids()

            # 记录索引类型
            logger.info(
                f"FAISS index initialized: type={self.index_type}, "
                f"vectors={self.get_vector_count()}, "
                f"dimension={self.embedding_service.get_dimension()}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize FAISS store: {e}")
            self._create_new_index()

    def _create_new_index(self):
        """创建新索引"""
        try:
            dimension = self.embedding_service.get_dimension()
            vector_count = 0  # 新索引，无向量

            # 确定索引类型
            if self.adaptive_selector:
                # 自适应选择
                selection = self.adaptive_selector.select_index(vector_count, dimension)
                self.index_type = selection["index_type"]
                self.index_config = selection["config"]
                logger.info(f"Adaptive selection: {self.index_type} - {selection['reason']}")
            else:
                # 使用配置
                self.index_type = getattr(self.config, "faiss_index_type", "flat")
                self.index_config = getattr(self.config, "faiss_index_config", {})

            # 使用索引工厂创建
            index_wrapper = FAISSIndexFactory.create_index(
                self.index_type,
                dimension,
                self.index_config
            )
            faiss_index = index_wrapper.get_index()

            self.vector_store = FAISS(
                embedding_function=self.embedding_service.embedding_model,
                index=faiss_index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            self._save_index()

            logger.info(
                f"Created new FAISS index: type={self.index_type}, "
                f"config={self.index_config}"
            )

        except Exception as e:
            logger.error(f"Failed to create new index: {e}")
            # 降级到 Flat 索引
            logger.warning("Falling back to Flat index")
            dimension = self.embedding_service.get_dimension()
            faiss_index = faiss.IndexFlatL2(dimension)
            self.vector_store = FAISS(
                embedding_function=self.embedding_service.embedding_model,
                index=faiss_index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
            self.index_type = "flat"
            self.index_config = {}

    def _load_existing_index(self):
        """加载已有索引"""
        try:
            self.vector_store = FAISS.load_local(
                self.index_path,
                self.embedding_service.embedding_model,
                allow_dangerous_deserialization=True,
            )

            # 尝试加载索引元数据
            metadata_file = os.path.join(self.index_path, "index_metadata.pkl")
            if os.path.exists(metadata_file):
                with open(metadata_file, "rb") as f:
                    metadata = pickle.load(f)
                    self.index_type = metadata.get("index_type", "flat")
                    self.index_config = metadata.get("index_config", {})
            else:
                # 无元数据，尝试推断
                index = self.vector_store.index
                self.index_type = self._infer_index_type(index)
                self.index_config = {}

            vector_count = self.vector_store.index.ntotal
            logger.info(
                f"Loaded FAISS index: type={self.index_type}, "
                f"vectors={vector_count}"
            )

        except Exception as e:
            logger.error(f"Failed to load index: {e}, creating new one")
            raise e

    def _infer_index_type(self, index: faiss.Index) -> str:
        """推断索引类型"""
        index_str = str(type(index))
        if "Flat" in index_str and "IVF" not in index_str:
            return "flat"
        elif "IVFPQ" in index_str:
            return "ivf_pq"
        elif "IVF" in index_str:
            return "ivf"
        elif "HNSW" in index_str:
            return "hnsw"
        else:
            return "flat"  # 默认

    def _save_index(self):
        """保存索引和元数据"""
        try:
            self.vector_store.save_local(self.index_path)

            # 保存元数据
            metadata = {
                "index_type": self.index_type,
                "index_config": self.index_config,
                "created_at": datetime.now().isoformat(),
                "vector_count": self.get_vector_count(),
            }
            metadata_file = os.path.join(self.index_path, "index_metadata.pkl")
            with open(metadata_file, "wb") as f:
                pickle.dump(metadata, f)

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    async def add_documents(self, documents: List[LangchainDocument]) -> bool:
        """添加文档"""
        try:
            # 检查是否需要训练（IVF/IVF-PQ）
            if self.index_type in ["ivf", "ivf_pq"] and not self.vector_store.index.is_trained:
                await self._train_index(documents)

            self.vector_store.add_documents(documents)
            self._save_index()

            # 检查是否需要升级索引
            await self._check_index_upgrade()

            logger.info(f"Added {len(documents)} documents to {self.index_type} index")
            return True

        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False

    async def _train_index(self, documents: List[LangchainDocument]):
        """训练索引（IVF/IVF-PQ需要）"""
        try:
            logger.info(f"Training {self.index_type} index...")

            # 生成嵌入向量
            texts = [doc.page_content for doc in documents]
            embeddings = await self.embedding_service.embedding_model.aembed_documents(texts)

            # 训练
            index_wrapper = FAISSIndexFactory.create_index(
                self.index_type,
                self.embedding_service.get_dimension(),
                self.index_config
            )
            import numpy as np
            train_vectors = np.array(embeddings).astype("float32")
            index_wrapper.train_index(train_vectors)

            # 更新索引
            self.vector_store.index = index_wrapper.get_index()

            logger.info(f"{self.index_type} index training completed")

        except Exception as e:
            logger.error(f"Failed to train index: {e}")
            # 降级到 Flat
            logger.warning("Falling back to Flat index due to training failure")
            self._fallback_to_flat()

    def _fallback_to_flat(self):
        """降级到 Flat 索引"""
        dimension = self.embedding_service.get_dimension()
        faiss_index = faiss.IndexFlatL2(dimension)

        # 迁移现有向量（如果有）
        # ...

        self.vector_store.index = faiss_index
        self.index_type = "flat"
        self.index_config = {}

    async def _check_index_upgrade(self):
        """检查是否需要升级索引"""
        if not self.adaptive_selector:
            return

        vector_count = self.get_vector_count()
        dimension = self.embedding_service.get_dimension()

        # 获取性能统计
        perf_stats = self.performance_monitor.get_stats()
        actual_latency = perf_stats.get("avg_latency_ms") if perf_stats else None

        # 检查是否需要升级
        upgrade_decision = self.adaptive_selector.should_upgrade(
            self.index_type,
            self.index_config,
            vector_count,
            dimension,
            actual_latency
        )

        if upgrade_decision["should_upgrade"]:
            logger.warning(
                f"Index upgrade recommended: {self.index_type} -> "
                f"{upgrade_decision['recommended_index']}. "
                f"Reason: {upgrade_decision['reason']}"
            )
            # 可以在这里触发自动迁移，或者仅记录警告

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[LangchainDocument]:
        """相似度搜索（带性能监控）"""
        start_time = time.time()

        try:
            search_k = k * 3  # 召回3倍（过滤软删除）

            if filter_dict:
                results = self.vector_store.similarity_search(
                    query, k=search_k, filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=search_k)

            # 过滤软删除
            filtered_results = [
                doc for doc in results
                if doc.metadata.get("doc_id") not in self.deleted_ids
            ][:k]

            # 记录性能
            latency_ms = (time.time() - start_time) * 1000
            self.performance_monitor.record_search(latency_ms, k, len(filtered_results))

            return filtered_results

        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    async def similarity_search_with_score(
        self,
        query: str,
        k: int = 5
    ) -> List[Tuple[LangchainDocument, float]]:
        """相似度搜索（带分数）"""
        start_time = time.time()

        try:
            search_k = k * 3
            all_results = self.vector_store.similarity_search_with_score(
                query, k=search_k
            )

            filtered_results = [
                (doc, score)
                for doc, score in all_results
                if doc.metadata.get("doc_id") not in self.deleted_ids
            ][:k]

            # 记录性能
            latency_ms = (time.time() - start_time) * 1000
            self.performance_monitor.record_search(latency_ms, k, len(filtered_results))

            return filtered_results

        except Exception as e:
            logger.error(f"Similarity search with scores failed: {e}")
            return []

    def get_vector_count(self) -> int:
        """获取向量数量"""
        if self.vector_store and self.vector_store.index:
            return self.vector_store.index.ntotal
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_vectors = self.get_vector_count()

        return {
            "index_type": self.index_type,
            "index_config": self.index_config,
            "total_vectors": total_vectors,
            "active_vectors": total_vectors - len(self.deleted_ids),
            "deleted_vectors": len(self.deleted_ids),
            "dimension": self.embedding_service.get_dimension(),
            "performance": self.performance_monitor.get_stats(),
            "upgrade_recommendation": self._get_upgrade_recommendation() if self.adaptive_selector else None,
        }

    def _get_upgrade_recommendation(self) -> Optional[Dict[str, Any]]:
        """获取升级建议"""
        if not self.adaptive_selector:
            return None

        vector_count = self.get_vector_count()
        dimension = self.embedding_service.get_dimension()
        perf_stats = self.performance_monitor.get_stats()
        actual_latency = perf_stats.get("avg_latency_ms") if perf_stats else None

        return self.adaptive_selector.should_upgrade(
            self.index_type,
            self.index_config,
            vector_count,
            dimension,
            actual_latency
        )

    async def rebuild_index(self) -> bool:
        """重建索引（移除软删除）"""
        try:
            all_docs = []
            for doc_id in self.vector_store.index_to_docstore_id.values():
                try:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc and doc.metadata.get("doc_id") not in self.deleted_ids:
                        all_docs.append(doc)
                except Exception:
                    continue

            self._create_new_index()

            if all_docs:
                self.vector_store.add_documents(all_docs)

            self.deleted_ids.clear()
            self._save_deleted_ids()
            self._save_index()

            logger.info(f"Rebuilt index with {len(all_docs)} active documents")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return False

    # 软删除管理
    def _load_deleted_ids(self):
        """加载软删除ID"""
        try:
            if os.path.exists(self.deleted_ids_file):
                with open(self.deleted_ids_file, "rb") as f:
                    self.deleted_ids = pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load deleted IDs: {e}")
            self.deleted_ids = set()

    def _save_deleted_ids(self):
        """保存软删除ID"""
        try:
            with open(self.deleted_ids_file, "wb") as f:
                pickle.dump(self.deleted_ids, f)
        except Exception as e:
            logger.error(f"Failed to save deleted IDs: {e}")

    async def delete_documents(self, file_id: str) -> int:
        """删除文档"""
        try:
            deleted_count = 0
            for doc_id in list(self.vector_store.index_to_docstore_id.keys()):
                try:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc and doc.metadata.get("file_id") == file_id:
                        self.deleted_ids.add(doc_id)
                        deleted_count += 1
                except Exception:
                    continue

            if deleted_count > 0:
                self._save_deleted_ids()
                logger.info(f"Marked {deleted_count} documents as deleted")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0


class IndexPerformanceMonitor:
    """索引性能监控器"""

    def __init__(self, window_size: int = 1000):
        self.window_size = window_size
        self.search_latencies = deque(maxlen=window_size)
        self.search_counts = deque(maxlen=window_size)
        self.result_counts = deque(maxlen=window_size)

    def record_search(self, latency_ms: float, k: int, result_count: int):
        """记录搜索性能"""
        self.search_latencies.append(latency_ms)
        self.search_counts.append(k)
        self.result_counts.append(result_count)

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """获取性能统计"""
        if not self.search_latencies:
            return None

        latencies = list(self.search_latencies)
        latencies.sort()

        return {
            "avg_latency_ms": np.mean(latencies),
            "p50_latency_ms": np.percentile(latencies, 50),
            "p95_latency_ms": np.percentile(latencies, 95),
            "p99_latency_ms": np.percentile(latencies, 99),
            "min_latency_ms": np.min(latencies),
            "max_latency_ms": np.max(latencies),
            "total_searches": len(latencies),
            "avg_results": np.mean(list(self.result_counts)) if self.result_counts else 0,
            "queries_per_second": self._calculate_qps(),
        }

    def _calculate_qps(self) -> float:
        """计算QPS（基于最近1分钟的数据）"""
        if not self.search_latencies:
            return 0.0
        # 简化计算：基于平均延迟
        avg_latency_sec = np.mean(list(self.search_latencies)) / 1000
        if avg_latency_sec > 0:
            return 1.0 / avg_latency_sec
        return 0.0

    def reset(self):
        """重置统计"""
        self.search_latencies.clear()
        self.search_counts.clear()
        self.result_counts.clear()
