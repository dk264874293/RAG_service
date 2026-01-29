"""
Vector Services Module

Provides vector storage and retrieval capabilities for RAG system.
"""

from .types import VectorSearchResult, IndexStats

# Services will be imported when needed
# from .embed_service import EmbeddingService
# from .vector_store import FAISSVectorStore
# from .document_indexer import DocumentIndexer
# from .retrieval_service import RetrievalService

__all__ = [
    "VectorSearchResult",
    "IndexStats",
    "EmbeddingService",
    "FAISSVectorStore",
    "DocumentIndexer",
    "RetrievalService",
]
