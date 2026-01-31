"""Vector retrieval strategy
Basic vector-based retrieval using FAISS
"""

import logging
from typing import List, Dict, Any, Optional

from .base import BaseRetrievalStrategy
from ..reranker import Reranker
from src.models.document import Document

logger = logging.getLogger(__name__)


class VectorRetrievalStrategy(BaseRetrievalStrategy):
    """Vector retrieval strategy using FAISS vector store"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vector_store = config.get("vector_store")
        self.embedding_service = config.get("embedding_service")
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
        """Execute vector search without scores"""
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
        """Execute vector search with scores"""
        if not self.vector_store:
            raise ValueError("vector_store not configured")

        if self.use_reranking and self.reranker.is_available():
            return await self._search_with_reranking(
                query, k=k, filter_dict=filter_dict
            )
        else:
            return await self._search_basic(query, k=k, filter_dict=filter_dict)

    async def _search_basic(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[tuple[Document, float]]:
        """Basic vector search without reranking"""
        results = await self.vector_store.similarity_search_with_score(
            query, k=k * 3 if self.use_reranking else k, filter_dict=filter_dict
        )

        return results[:k]

    async def _search_with_reranking(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
    ) -> List[tuple[Document, float]]:
        """Vector search with reranking"""
        results = await self.vector_store.similarity_search_with_score(
            query, k=k * 3, filter_dict=filter_dict
        )

        reranked = self.reranker.rerank_documents(query, results, top_k=k)

        return reranked

    async def warmup(self) -> None:
        """Warmup by performing a test search"""
        try:
            await self._search_basic("warmup query", k=1)
            logger.info("VectorRetrievalStrategy warmup completed")
        except Exception as e:
            logger.warning(f"VectorRetrievalStrategy warmup failed: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.vector_store = None
        self.embedding_service = None
        logger.info("VectorRetrievalStrategy cleanup completed")
