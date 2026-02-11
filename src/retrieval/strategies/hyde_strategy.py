"""
HyDE (Hypothetical Document Embeddings) 检索策略
生成假设文档来提升检索质量
"""

import logging
from typing import List, Dict, Any, Optional

from .base import BaseRetrievalStrategy
from src.models.document import Document
from ...retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class HyDEStrategy(BaseRetrievalStrategy):
    """
    HyDE检索策略

    核心思想：
    1. 使用LLM生成假设的答案文档
    2. 对假设文档进行向量化
    3. 使用假设向量进行检索
    4. 返回最相关的原始文档

    适用场景：
    - 问答类查询（"什么是...?"）
    - 概念性问题（"...的原理是什么?"）
    - 需要理解查询意图的场景

    优势：
    - 能够理解查询意图，而不只是关键词匹配
    - 对于模糊查询效果更好
    - 能够发现语义相关但关键词不匹配的文档

    劣势：
    - 需要LLM调用，延迟较高
    - 对LLM质量敏感
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.vector_store = config.get("vector_store")
        self.embedding_service = config.get("embedding_service")

        # LLM配置
        llm_provider = config.get("llm_provider", "dashscope")
        if llm_provider == "dashscope":
            from src.service.llm_service import LLMService
            llm_config = {
                "provider": "dashscope",
                "model": config.get("model", "qwen-plus"),
                "temperature": config.get("temperature", 0.0),
            }
            self.llm_service = LLMService(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # HyDE提示词模板
        self.hyde_prompt_template = config.get(
            "hyde_prompt_template",
            "请基于以下问题生成一个详细的假设性答案文档。"
            "不需要准确回答，只需要涵盖问题的关键概念和术语。\n\n问题：{query}\n\n答案："
        )

        # 是否使用Reranker
        self.use_reranker = config.get("use_reranking", True)
        if self.use_reranker:
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
        **kwargs
    ) -> List[Document]:
        """执行HyDE检索"""
        try:
            # 1. 生成假设文档
            hypothetical_doc = await self._generate_hypothetical(query)

            logger.info(f"Generated hypothetical document for query: {query[:50]}...")

            # 2. 向量化假设文档
            hypothetical_embedding = await self.embedding_service.embed_text(hypothetical_doc)

            # 3. 使用假设向量检索
            results = await self._search_by_embedding(
                hypothetical_embedding,
                k=k * 2,  # 召回更多，后续过滤
                filter_dict=filter_dict
            )

            # 4. 如果启用Reranker，重新排序
            if self.use_reranker and self.reranker and self.reranker.is_available():
                results = await self._rerank(query, results, k=k)
            else:
                results = results[:k]

            logger.info(f"HyDE retrieval completed: {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"HyDE retrieval failed: {e}")
            # 降级到普通向量检索
            logger.warning("Falling back to vector search")
            return await self._vector_search(query, k=k, filter_dict=filter_dict)

    async def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """执行HyDE检索（带分数）"""
        results = await self.search(query, k=k, filter_dict=filter_dict)
        # 返回固定分数（HyDE本身不提供分数）
        return [(doc, 1.0) for doc in results]

    async def _generate_hypothetical(self, query: str) -> str:
        """生成假设文档"""
        try:
            prompt = self.hyde_prompt_template.format(query=query)

            # 调用LLM
            response = await self.llm_service.generate(prompt)

            # 清理响应
            hypothetical_doc = response.strip()

            if not hypothetical_doc:
                raise ValueError("Empty response from LLM")

            return hypothetical_doc

        except Exception as e:
            logger.error(f"Failed to generate hypothetical document: {e}")
            raise

    async def _search_by_embedding(
        self,
        embedding: List[float],
        k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """使用嵌入向量搜索"""
        try:
            # 将嵌入向量转换为numpy数组
            import numpy as np
            embedding_array = np.array([embedding]).astype('float32')

            # 在向量存储中搜索
            if hasattr(self.vector_store, 'index'):
                # 使用FAISS直接搜索
                faiss_index = self.vector_store.index
                dimension = faiss_index.d

                # 执行搜索
                distances, indices = faiss_index.search(embedding_array, k)

                # 转换结果
                results = []
                for score, idx in zip(distances[0], indices[0]):
                    if idx < 0 or idx >= len(self.vector_store.index_to_docstore_id):
                        continue

                    doc_id = self.vector_store.index_to_docstore_id.get(idx)
                    if doc_id:
                        doc = self.vector_store.docstore.search(doc_id)
                        if doc:
                            # 转换为Document
                            document = Document(
                                page_content=doc.page_content,
                                id_=doc_id,
                                metadata=doc.metadata
                            )
                            results.append(document)

                return results
            else:
                # 降级使用向量存储的API
                return await self._vector_search_by_embedding(
                    embedding, k=k, filter_dict=filter_dict
                )

        except Exception as e:
            logger.error(f"Failed to search by embedding: {e}")
            return []

    async def _vector_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """降级：普通向量搜索"""
        if not self.vector_store:
            return []

        try:
            # 检查vector_store是否有similarity_search方法
            if hasattr(self.vector_store, 'similarity_search'):
                results = await self.vector_store.similarity_search(
                    query, k=k, filter_dict=filter_dict
                )
            else:
                # 如果是LangChain的FAISS，直接调用
                results = await self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    async def _vector_search_by_embedding(
        self,
        embedding: List[float],
        k: int,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """降级：使用嵌入向量的向量搜索"""
        # 这种情况比较复杂，暂时返回空
        return []

    async def _rerank(
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

    async def warmup(self) -> None:
        """预热"""
        try:
            # 生成测试假设文档
            test_hypothetical = "这是一个测试文档，用于预热HyDE策略。"
            # 不实际调用LLM，避免开销
            logger.info("HyDEStrategy warmup completed")
        except Exception as e:
            logger.warning(f"HyDEStrategy warmup failed: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        self.vector_store = None
        self.embedding_service = None
        logger.info("HyDEStrategy cleanup completed")
