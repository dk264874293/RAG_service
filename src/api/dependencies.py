from functools import lru_cache

from config import settings
from src.service.upload_service import UploadService
from src.service.document_service import DocumentService
from src.service.markdown_service import MarkdownService


@lru_cache(maxsize=1)
def get_settings() -> settings:
    """获取配置对象（使用 LRU 缓存，避免重复实例化）"""
    return settings


@lru_cache(maxsize=1)
def get_upload_service() -> UploadService:
    """
    获取上传服务实例（使用单例模式）

    使用 LRU 缓存确保整个应用生命周期内只有一个 UploadService 实例，
    避免每次请求都创建新实例的性能开销。
    """
    return UploadService(get_settings())


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
    """
    获取文档服务实例（使用单例模式）

    使用 LRU 缓存确保整个应用生命周期内只有一个 DocumentService 实例，
    避免每次请求都创建新实例的性能开销。
    """
    return DocumentService(get_settings())


@lru_cache(maxsize=1)
def get_markdown_service() -> MarkdownService:
    """
    获取 Markdown 服务实例（使用单例模式）

    使用 LRU 缓存确保整个应用生命周期内只有一个 MarkdownService 实例，
    避免每次请求都创建新实例的性能开销。
    """
    return MarkdownService(get_settings())


# Vector service dependencies
@lru_cache(maxsize=1)
def get_embedding_service() -> object:
    """Get embedding service instance (singleton pattern)"""
    from src.vector.embed_service import EmbeddingService

    return EmbeddingService(get_settings())


@lru_cache(maxsize=1)
def get_vector_store() -> object:
    """Get vector store instance (singleton pattern)"""
    embedding_service = get_embedding_service()
    from src.vector.vector_store import FAISSVectorStore

    return FAISSVectorStore(get_settings(), embedding_service)


@lru_cache(maxsize=1)
def get_retrieval_service() -> object:
    """Get retrieval service instance (singleton pattern)"""
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    from src.vector.retrieval_service import RetrievalService

    return RetrievalService(get_settings(), vector_store, embedding_service)
