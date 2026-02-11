from functools import lru_cache

from config import settings
from src.service.upload_service import UploadService
from src.service.document_service import DocumentService
from src.service.markdown_service import MarkdownService
from src.service.storage_service import StorageService


@lru_cache(maxsize=1)
def get_settings() -> settings:
    return settings


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    return StorageService(get_settings())


@lru_cache(maxsize=1)
def get_upload_service() -> UploadService:
    vector_service = get_vector_service()
    storage_service = get_storage_service()
    return UploadService(get_settings(), vector_service, storage_service)


@lru_cache(maxsize=1)
def get_document_service() -> DocumentService:
    return DocumentService(get_settings())


@lru_cache(maxsize=1)
def get_markdown_service() -> MarkdownService:
    storage_service = get_storage_service()
    return MarkdownService(get_settings(), storage_service)


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

    # 优先级: 分代索引 > 优化版FAISS > 传统FAISS
    if settings.enable_generational_index:
        # 方案1: 分代索引（Hot/Cold架构）
        from src.vector.generational_index_store import GenerationalIndexStore

        logger = __import__("logging").getLogger(__name__)
        logger.info("Using GenerationalIndexStore (Hot/Cold architecture)")
        return GenerationalIndexStore(settings, embedding_service)

    elif (settings.faiss_index_auto_select or
          settings.faiss_index_type != "flat"):
        # 方案2: 优化版FAISS（支持多种索引类型）
        from src.vector.optimized_faiss_store import OptimizedFAISSVectorStore

        logger = __import__("logging").getLogger(__name__)
        index_type = "auto" if settings.faiss_index_auto_select else settings.faiss_index_type
        logger.info(f"Using OptimizedFAISSVectorStore with index_type={index_type}")
        return OptimizedFAISSVectorStore(settings, embedding_service)

    else:
        # 方案3: 传统FAISS存储（向后兼容）
        from src.vector.vector_store import FAISSVectorStore

        logger = __import__("logging").getLogger(__name__)
        logger.info("Using traditional FAISSVectorStore with flat index")
        return FAISSVectorStore(settings, embedding_service)


@lru_cache(maxsize=1)
def get_retrieval_service():
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()

    # 检查是否启用增强检索服务
    use_enhanced = getattr(settings, "enable_enhanced_retrieval", False)

    if use_enhanced:
        from src.vector.enhanced_retrieval_service import EnhancedRetrievalService
        from src.retrieval.reranker import Reranker

        logger = __import__("logging").getLogger(__name__)
        logger.info("Using EnhancedRetrievalService with integrated Reranker")

        # 创建Reranker
        reranker = Reranker(
            model_name=settings.retrieval_strategy_config.get(
                "reranker_model", "BAAI/bge-reranker-large"
            )
        )

        return EnhancedRetrievalService(
            settings,
            vector_store,
            embedding_service,
            reranker
        )
    else:
        # 使用原有检索服务
        from src.vector.retrieval_service import RetrievalService

        logger = __import__("logging").getLogger(__name__)
        logger.info("Using traditional RetrievalService")

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


@lru_cache(maxsize=1)
def get_rbac_service():
    from src.service.rbac_service import RBACService

    return RBACService(get_settings())


@lru_cache(maxsize=1)
def get_memory_manager():
    from src.memory.memory_manager import MemoryManager

    config = get_settings()
    memory_config = {
        "enable_conversation_memory": getattr(config, "enable_conversation_memory", True),
        "conversation_max_messages": getattr(config, "conversation_max_messages", 100),
        "conversation_max_tokens": getattr(config, "conversation_max_tokens", 4000),
        "enable_summarization": getattr(config, "enable_summarization", True),
    }

    return MemoryManager(memory_config)
