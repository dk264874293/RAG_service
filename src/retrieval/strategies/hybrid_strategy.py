"""Hybrid retrieval strategy
Combines vector search and BM25 keyword search using RRF fusion
"""

import logging
from typing import List, Dict, Any, Optional

from rank_bm25 import BM25Okapi

from .base import BaseRetrievalStrategy
from ..reranker import Reranker
from src.models.document import Document

logger = logging.getLogger(__name__)


class HybridRetrievalStrategy(BaseRetrievalStrategy):
    """Hybrid retrieval combining vector and BM25"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vector_store = config.get("vector_store")
        self.embedding_service = config.get("embedding_service")
        self.bm25_index = config.get("bm25_index")

        self.alpha = config.get("alpha", 0.7)
        self.bm25_k1 = config.get("bm25_k1", 1.2)
        self.bm25_b = config.get("bm25_b", 0.75)

        self.use_reranking = config.get("use_reranking", False)
        if self.use_reranking:
            self.reranker = Reranker(
                model_name=config.get("reranker_model", "BAAI/bge-reranker-large")
            )
        else:
            self.reranker = None

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Execute hybrid search without scores"""
        results_with_scores = await self.search_with_scores(
            query, k=k, filter_dict=filter_dict, **kwargs
        )
        return [doc for doc, score in results_with_scores]

    async def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs,
    ) -> List[tuple[Document, float]]:
        """Execute hybrid search with RRF fusion"""
        vector_results = await self._vector_search(query, k=k, filter_dict=filter_dict)

        bm25_results = await self._bm25_search(query, k=k)

        merged = self._reciprocal_rank_fusion(
            vector_results, bm25_results, k=k, alpha=self.alpha
        )

        if self.use_reranking and self.reranker.is_available():
            merged = self._rerank_results(query, merged, k=k)

        return merged

    async def _vector_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[tuple[Document, float]]:
        """Perform vector search"""
        if not self.vector_store:
            raise ValueError("vector_store not configured")

        search_k = k * 3 if self.use_reranking else k
        results = await self.vector_store.similarity_search_with_score(
            query, k=search_k, filter_dict=filter_dict
        )

        return results

    async def _bm25_search(
        self,
        query: str,
        k: int = 5,
    ) -> List[tuple[Document, float]]:
        """Perform BM25 search"""
        if not self.bm25_index:
            logger.warning("BM25 index not configured, returning empty results")
            return []

        tokenized_query = query.split()
        results = self.bm25_index.get_top_n(tokenized_query, n=k)

        bm25_results = []
        for doc, score in results:
            bm25_results.append(
                (
                    Document(
                        page_content=doc.metadata.get("content", ""),
                        metadata=doc.metadata,
                    ),
                    score,
                )
            )

        return bm25_results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[tuple[Document, float]],
        bm25_results: List[tuple[Document, float]],
        k: int = 5,
        alpha: float = 0.7,
        k_constant: int = 60,
    ) -> List[tuple[Document, float]]:
        """
        Reciprocal Rank Fusion (RRF)

        Combines results from multiple retrieval methods.
        """
        scores = {}

        def _add_score(results, weight):
            for rank, (doc, score) in enumerate(results, start=1):
                doc_id = doc.metadata.get("doc_id", id(doc))

                if doc_id not in scores:
                    scores[doc_id] = {
                        "doc": doc,
                        "vector_score": 0.0,
                        "bm25_score": 0.0,
                    }

                if weight > 0:
                    scores[doc_id]["vector_score"] = weight * (
                        1.0 / (rank + k_constant)
                    )
                else:
                    scores[doc_id]["bm25_score"] = (1.0 - weight) * (
                        1.0 / (rank + k_constant)
                    )

        _add_score(vector_results, alpha)
        _add_score(bm25_results, 0.0)

        fused = sorted(
            scores.items(),
            key=lambda x: x[1]["vector_score"] + x[1]["bm25_score"],
            reverse=True,
        )

        final_results = []
        for doc_id, item in fused[:k]:
            final_score = item["vector_score"] + item["bm25_score"]
            final_results.append((item["doc"], final_score))

        return final_results

    def _rerank_results(
        self,
        query: str,
        results: List[tuple[Document, float]],
        k: int = 5,
    ) -> List[tuple[Document, float]]:
        """Rerank results using cross-encoder"""
        if not results:
            return []

        docs_only = [doc for doc, score in results]
        reranked = self.reranker.rerank_documents(query, docs_only, top_k=k)

        return reranked

    async def warmup(self) -> None:
        """Warmup by performing test searches"""
        try:
            await self._vector_search("warmup query", k=1)
            if self.bm25_index:
                self.bm25_index.get_top_n(["warmup"], n=1)
            logger.info("HybridRetrievalStrategy warmup completed")
        except Exception as e:
            logger.warning(f"HybridRetrievalStrategy warmup failed: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.vector_store = None
        self.embedding_service = None
        self.bm25_index = None
        logger.info("HybridRetrievalStrategy cleanup completed")
