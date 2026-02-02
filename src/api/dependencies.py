from functools import lru_cache

from config import settings
from src.service.upload_service import UploadService
from src.service.document_service import DocumentService
from src.service.markdown_service import MarkdownService


@lru_cache(maxsize=1)
def get_settings() -> settings:
    return settings


@lru_cache(maxsize=1)
def get_upload_service() -> UploadService:
    vector_service = get_vector_service()
    return UploadService(get_settings(), vector_service)


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
    return DocumentService(get_settings())


@lru_cache(maxsize=1)
def get_markdown_service() -> MarkdownService:
    return MarkdownService(get_settings())


@lru_cache(maxsize=1)
def get_vector_service():
    from src.service.vector_service import VectorService

    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    return VectorService(get_settings(), vector_store, embedding_service)


@lru_cache(maxsize=1)
def get_embedding_service():
    from src.vector.embed_service import EmbeddingService

    return EmbeddingService(get_settings())


@lru_cache(maxsize=1)
def get_vector_store():
    embedding_service = get_embedding_service()
    from src.vector.vector_store import FAISSVectorStore

    return FAISSVectorStore(get_settings(), embedding_service)


@lru_cache(maxsize=1)
def get_retrieval_service():
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    from src.vector.retrieval_service import RetrievalService

    return RetrievalService(get_settings(), vector_store, embedding_service)


@lru_cache(maxsize=1)
def get_retrieval_strategy():
    from src.retrieval.strategies.factory import RetrievalStrategyFactory

    embedding_service = get_embedding_service()
    vector_store = get_vector_store()

    dependencies = {
        "vector_store": vector_store,
        "embedding_service": embedding_service,
        "use_reranking": settings.retrieval_strategy_config.get("use_reranking", True),
        "reranker_model": settings.retrieval_strategy_config.get(
            "reranker_model", "BAAI/bge-reranker-large"
        ),
        "bm25_index": None,
        "alpha": settings.hybrid_retrieval_config.get("alpha", 0.7),
        "bm25_k1": settings.hybrid_retrieval_config.get("bm25_k1", 1.2),
        "bm25_b": settings.hybrid_retrieval_config.get("bm25_b", 0.75),
        "parent_chunk_size": settings.parent_child_config.get(
            "parent_chunk_size", 2000
        ),
        "child_chunk_size": settings.parent_child_config.get("child_chunk_size", 400),
        "chunk_overlap": settings.parent_child_config.get("chunk_overlap", 50),
    }

    strategy = RetrievalStrategyFactory.create(
        settings.retrieval_strategy,
        settings.retrieval_strategy_config,
        dependencies,
    )

    return strategy
