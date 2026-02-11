"""
增强的检索服务
深度集成Reranker，提供统一的检索接口
"""

import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document as LangchainDocument

from ..models.document import Document
from ..vector.embed_service import EmbeddingService
from ..retrieval.bm25_index_manager import BM25IndexManager
from ..retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class EnhancedRetrievalService:
    """
    增强的检索服务

    核心改进：
    1. Reranker默认启用
    2. BM25索引自动管理
    3. 统一的检索接口
    4. 智能策略选择（可选）
    """

    def __init__(
        self,
        config,
        vector_store,
        embedding_service: EmbeddingService,
        reranker: Optional[Reranker] = None
    ):
        self.config = config
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.reranker = reranker

        # BM25索引管理器
        self.bm25_manager: Optional[BM25IndexManager] = None

        # Reranker配置
        self.enable_reranker_by_default = getattr(config, "enable_reranker_by_default", True)
        self.reranker_top_k = getattr(config, "reranker_top_k", 20)

        # 初始化BM25索引（如果启用）
        if getattr(config, "enable_bm25", True):
            self._init_bm25_index()

    def _init_bm25_index(self):
        """初始化BM25索引"""
        try:
            from config import settings
            import os

            bm25_path = os.path.join(settings.faiss_index_path, "bm25")

            self.bm25_manager = BM25IndexManager(
                index_path=bm25_path,
                vector_store=self.vector_store,
                k1=getattr(settings, "bm25_k1", 1.2),
                b=getattr(settings, "bm25_b", 0.75),
                auto_sync=getattr(settings, "bm25_auto_sync", True)
            )

            logger.info("BM25 index manager initialized")

        except Exception as e:
            logger.warning(f"Failed to initialize BM25 index manager: {e}")

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        use_rerank: Optional[bool] = None,
        strategy: str = "auto"
    ) -> List[Document]:
        """
        统一搜索接口

        核心改进：
        - Reranker默认启用
        - 支持BM25混合检索
        - 可配置的检索流程

        Args:
            query: 查询文本
            k: 返回结果数量
            filter_dict: 元数据过滤
            use_rerank: 是否使用Rerank（None表示使用默认配置）
            strategy: 检索策略（auto表示自动选择）

        Returns:
            文档列表
        """
        try:
            # 确定是否使用Reranker
            if use_rerank is None:
                use_rerank = self.enable_reranker_by_default

            # 执行检索
            if strategy == "auto":
                strategy = self._select_strategy(query)

            logger.info(
                f"Retrieval: query='{query[:50]}...', strategy={strategy}, "
                f"k={k}, use_rerank={use_rerank}"
            )

            # 根据策略执行检索
            if strategy == "vector":
                results = await self._vector_search(query, k, filter_dict)
            elif strategy == "hybrid":
                results = await self._hybrid_search(query, k, filter_dict)
            elif strategy == "hyde":
                results = await self._hyde_search(query, k, filter_dict)
            elif strategy == "query2doc":
                results = await self._query2doc_search(query, k, filter_dict)
            else:
                logger.warning(f"Unknown strategy: {strategy}, using vector")
                results = await self._vector_search(query, k, filter_dict)

            # Rerank
            if use_rerank and self.reranker and self.reranker.is_available():
                results = await self._rerank_results(query, results, k)

            logger.info(
                f"Retrieval completed: query='{query[:50]}..., "
                f"returned {len(results)} results, strategy={strategy}"
            )

            return results

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            return []

    async def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        use_rerank: Optional[bool] = None
    ) -> List[tuple[Document, float]]:
        """搜索并返回分数"""
        try:
            # 使用主检索获取结果
            results = await self.search(
                query, k=k, filter_dict=filter_dict, use_rerank=use_rerank
            )

            # 返回固定分数（实际分数在Rerank阶段计算）
            return [(doc, 1.0) for doc in results]

        except Exception as e:
            logger.error(f"Search with scores failed: {e}")
            return []

    async def _vector_search(
        self,
        query: str,
        k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """纯向量搜索"""
        try:
            langchain_docs = await self.vector_store.similarity_search(
                query, k=k, filter=filter_dict
            )

            # 转换为Document格式
            documents = []
            for lc_doc in langchain_docs:
                doc = Document(
                    page_content=lc_doc.page_content,
                    id_=lc_doc.metadata.get("doc_id", ""),
                    metadata=lc_doc.metadata,
                )
                documents.append(doc)

            return documents

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _hybrid_search(
        self,
        query: str,
        k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """混合检索（向量+BM25）"""
        try:
            if not self.bm25_manager:
                logger.warning("BM25 not available, falling back to vector search")
                return await self._vector_search(query, k, filter_dict)

            # 向量检索
            vector_results = await self._vector_search(query, k=k, filter_dict=filter_dict)

            # BM25检索
            from .bm25_index_manager import BM25IndexManager
            bm25_manager = BM25IndexManager(
                index_path=f"{self.config.faiss_index_path}/bm25",
                vector_store=self.vector_store
            )

            # 检查BM25索引是否就绪
            if bm25_manager.bm25_index is None:
                # 首次使用，需要构建索引
                logger.info("BM25 index not ready, building...")
                await bm25_manager.build_from_vector_store()

            # BM25搜索
            bm25_results = await bm25_manager.search(query, k=k)

            # RRF融合
            fused_results = self._reciprocal_rank_fusion(
                vector_results,
                bm25_results,
                k=k,
                alpha=self.config.hybrid_retrieval_config.get("alpha", 0.7)
            )

            return fused_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return await self._vector_search(query, k, filter_dict)

    async def _hyde_search(
        self,
        query: str,
        k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """HyDE检索"""
        try:
            from .strategies.hyde_strategy import HyDEStrategy

            config = {
                "vector_store": self.vector_store,
                "embedding_service": self.embedding_service,
                "llm_provider": "dashscope",
                "model": "qwen-plus",
                "temperature": 0.0,
                "use_reranking": False,  # HyDE本身就会使用LLM，不需要再次Rerank
            }

            strategy = HyDEStrategy(config)
            return await strategy.search(query, k=k, filter_dict=filter_dict)

        except Exception as e:
            logger.error(f"HyDE search failed: {e}")
            return await self._vector_search(query, k, filter_dict)

    async def _query2doc_search(
        self,
        query: str,
        k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """Query2Doc检索"""
        try:
            from .strategies.query2doc_strategy import Query2DocStrategy

            config = {
                "vector_store": self.vector_store,
                "llm_provider": "dashscope",
                "model": "qwen-plus",
                "temperature": 0.7,
                "num_expansions": 3,
                "use_reranking": False,  # Query2Doc已经使用RRF融合
            }

            strategy = Query2DocStrategy(config)
            return await strategy.search(query, k=k, filter_dict=filter_dict)

        except Exception as e:
            logger.error(f"Query2Doc search failed: {e}")
            return await self._vector_search(query, k, filter_dict)

    def _select_strategy(self, query: str) -> str:
        """
        根据查询特征自动选择最优策略

        简单规则：
        - 问号结尾 → HyDE
        - 包含"比较"、"差异"等词 → Decomposition
        - 短查询(<5词) → Multi-Query
        - 默认 → Hybrid
        """
        query_lower = query.lower()

        # 问号结尾 → HyDE
        if query_lower.endswith('?'):
            return "hyde"

        # 包含比较/差异 → Decomposition (如果实现)
        comparison_words = ["比较", "差异", "区别", "优缺点", "vs", "对比"]
        if any(word in query for word in comparison_words):
            # 暂时使用HyDE替代
            return "hyde"

        # 短查询 → Vector (或Multi-Query)
        word_count = len(query.split())
        if word_count <= 3:
            return "vector"

        # 默认混合检索
        return "hybrid"

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Document],
        bm25_results: List[tuple[Document, float]],
        k: int = 5,
        alpha: float = 0.7,
        k_constant: int = 60
    ) -> List[Document]:
        """RRF融合"""
        scores = {}

        # 向量结果（权重alpha）
        for rank, doc in enumerate(vector_results, start=1):
            doc_id = doc.metadata.get("doc_id") or id(doc)
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "vector_score": 0.0, "bm25_score": 0.0}

            scores[doc_id]["vector_score"] = alpha / (rank + k_constant)

        # BM25结果（权重1-alpha）
        for doc, bm25_score in bm25_results:
            doc_id = doc.metadata.get("doc_id") or id(doc)
            if doc_id not in scores:
                scores[doc_id] = {"doc": doc, "vector_score": 0.0, "bm25_score": 0.0}

            scores[doc_id]["bm25_score"] = (1 - alpha) * bm25_score

        # 排序
        sorted_docs = sorted(
            scores.items(),
            key=lambda x: x[1]["vector_score"] + x[1]["bm25_score"],
            reverse=True
        )

        return [item["doc"] for doc_id, item in sorted_docs[:k]]

    async def _rerank_results(
        self,
        query: str,
        documents: List[Document],
        k: int
    ) -> List[Document]:
        """使用Reranker重新排序"""
        if not self.reranker or not self.reranker.is_available():
            return documents[:k]

        try:
            reranked = self.reranker.rerank_documents(query, documents, top_k=k)
            return [doc for doc, score in reranked]

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return documents[:k]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "reranker_enabled": self.enable_reranker_by_default,
            "reranker_available": self.reranker.is_available() if self.reranker else False,
        }

        if self.bm25_manager:
            stats["bm25"] = self.bm25_manager.get_stats()

        return stats
