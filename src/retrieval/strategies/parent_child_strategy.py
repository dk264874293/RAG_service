"""Parent-child retrieval strategy
Retrieves child chunks but returns parent chunks for better context
"""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .base import BaseRetrievalStrategy
from src.models.document import Document

logger = logging.getLogger(__name__)


class ParentChildRetrievalStrategy(BaseRetrievalStrategy):
    """Parent-child retrieval strategy

    Indexes small child chunks for precision, but returns
    larger parent chunks for better context.
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.vector_store = config.get("vector_store")
        self.embedding_service = config.get("embedding_service")

        self.parent_chunk_size = config.get("parent_chunk_size", 2000)
        self.child_chunk_size = config.get("child_chunk_size", 400)
        self.chunk_overlap = config.get("chunk_overlap", 50)

        self.parent_children_map = defaultdict(list)

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs,
    ) -> List[Document]:
        """Execute parent-child search without scores"""
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
        """Execute parent-child search with scores"""
        if not self.vector_store:
            raise ValueError("vector_store not configured")

        search_k = k * 3
        results = await self.vector_store.similarity_search_with_score(
            query, k=search_k, filter_dict=filter_dict
        )

        return self._return_parent_chunks(results, k=k)

    def _return_parent_chunks(
        self,
        child_results: List[tuple[Document, float]],
        k: int = 5,
    ) -> List[tuple[Document, float]]:
        """
        Return parent chunks for child results

        Deduplicates by parent_id and preserves the highest score.
        """
        parent_scores = {}

        for doc, score in child_results:
            parent_id = doc.metadata.get("parent_id")

            if not parent_id:
                continue

            if parent_id not in parent_scores:
                parent_scores[parent_id] = {
                    "parent_id": parent_id,
                    "score": score,
                }
            else:
                if score > parent_scores[parent_id]["score"]:
                    parent_scores[parent_id]["score"] = score

        sorted_parents = sorted(
            parent_scores.values(), key=lambda x: x["score"], reverse=True
        )

        return [(doc, item["score"]) for doc, item in sorted_parents[:k]]

    async def index_document(self, file_id: str, text: str, metadata: Dict) -> bool:
        """Index document with parent-child chunks"""
        try:
            parent_chunks = self._split_parent_chunks(text)
            child_chunks_list = []

            for parent in parent_chunks:
                child_chunks = self._split_child_chunks(parent["content"])
                child_chunks_list.extend(child_chunks)

            logger.info(
                f"Parent-child indexing: {len(parent_chunks)} parent chunks, "
                f"{len(child_chunks_list)} child chunks"
            )

            return True

        except Exception as e:
            logger.error(f"Parent-child indexing failed: {e}")
            return False

    def _split_parent_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Split text into parent chunks"""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.parent_chunk_size
            chunk_text = text[start:end]
            chunks.append({"content": chunk_text, "parent_id": f"parent_{len(chunks)}"})
            start = end - self.chunk_overlap

        return chunks

    def _split_child_chunks(self, parent_text: str) -> List[Dict[str, Any]]:
        """Split parent text into child chunks"""
        chunks = []
        start = 0

        while start < len(parent_text):
            end = start + self.child_chunk_size
            chunk_text = parent_text[start:end]
            chunks.append({"content": chunk_text})
            start = end - (self.chunk_overlap // 4)

        return chunks

    async def warmup(self) -> None:
        """Warmup by performing a test search"""
        try:
            await self.search("warmup query", k=1)
            logger.info("ParentChildRetrievalStrategy warmup completed")
        except Exception as e:
            logger.warning(f"ParentChildRetrievalStrategy warmup failed: {e}")

    async def cleanup(self) -> None:
        """Cleanup resources"""
        self.vector_store = None
        self.embedding_service = None
        self.parent_children_map.clear()
        logger.info("ParentChildRetrievalStrategy cleanup completed")
