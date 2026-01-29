"""
结果重排序（Reranking）模块
使用交叉编码器提升检索结果的排序准确性
"""

from typing import List, Tuple, Dict, Any
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Reranker:
    """
    结果重排序器

    使用交叉编码器模型对检索结果进行重新排序，提高相关性
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-large"):
        """
        初始化重排序器

        Args:
            model_name: 重排序模型名称
        """
        self.model_name = model_name
        self.model = None
        self._lazy_init()

    def _lazy_init(self):
        """
        延迟初始化模型

        仅在首次使用时加载模型，避免启动时的性能开销
        """
        if self.model is None:
            try:
                from sentence_transformers import CrossEncoder

                logger.info(f"Loading reranker model: {self.model_name}")
                self.model = CrossEncoder(self.model_name)
                logger.info("Reranker model loaded successfully")
            except ImportError:
                logger.warning(
                    "sentence_transformers not installed. Reranking will be disabled. "
                    "Install with: pip install sentence-transformers"
                )
                self.model = None
            except Exception as e:
                logger.error(f"Failed to load reranker model: {e}")
                self.model = None

    def rerank(
        self, query: str, documents: List[Tuple[str, Any]], top_k: int = None
    ) -> List[Tuple[str, Any, float]]:
        """
        重新排序文档列表

        Args:
            query: 查询文本
            documents: 文档列表，格式为[(content, metadata), ...]
            top_k: 返回的top-k文档数量

        Returns:
            List[Tuple[str, Any, float]]: 重排序后的文档列表，包含相关性分数
        """
        if self.model is None:
            logger.warning("Reranker model not available, returning original order")
            return [(doc, meta, 0.0) for doc, meta in documents]

        if not documents:
            return []

        try:
            doc_texts = [doc for doc, _ in documents]

            pairs = [[query, doc_text] for doc_text in doc_texts]

            scores = self.model.predict(pairs)

            scored_docs = list(zip(documents, scores))

            scored_docs.sort(key=lambda x: x[1], reverse=True)

            if top_k:
                scored_docs = scored_docs[:top_k]

            reranked_results = [
                (doc, meta, float(score)) for (doc, meta), score in scored_docs
            ]

            logger.info(
                f"Reranking completed: {len(documents)} documents -> {len(reranked_results)} results"
            )

            return reranked_results

        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return [(doc, meta, 0.0) for doc, meta in documents]

    def rerank_documents(
        self, query: str, documents: List[Any], top_k: int = None
    ) -> List[Tuple[Any, float]]:
        """
        重新排序Langchain Document对象列表

        Args:
            query: 查询文本
            documents: Langchain Document对象列表
            top_k: 返回的top-k文档数量

        Returns:
            List[Tuple[Any, float]]: 重排序后的文档列表，包含相关性分数
        """
        if self.model is None:
            logger.warning("Reranker model not available, returning original order")
            return [(doc, 0.0) for doc in documents]

        if not documents:
            return []

        try:
            doc_texts = [doc.page_content for doc in documents]

            pairs = [[query, doc_text] for doc_text in doc_texts]

            scores = self.model.predict(pairs)

            scored_docs = list(zip(documents, scores))

            scored_docs.sort(key=lambda x: x[1], reverse=True)

            if top_k:
                scored_docs = scored_docs[:top_k]

            reranked_results = [(doc, float(score)) for doc, score in scored_docs]

            logger.info(
                f"Document reranking completed: {len(documents)} -> {len(reranked_results)} results"
            )

            return reranked_results

        except Exception as e:
            logger.error(f"Document reranking failed: {e}")
            return [(doc, 0.0) for doc in documents]

    def is_available(self) -> bool:
        """
        检查重排序模型是否可用

        Returns:
            bool: 模型是否可用
        """
        return self.model is not None
