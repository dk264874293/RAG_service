"""
Query2Doc 检索策略
使用LLM扩展查询，生成多个相关查询进行检索
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional

from .base import BaseRetrievalStrategy
from src.models.document import Document
from ...retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class Query2DocStrategy(BaseRetrievalStrategy):
    """
    Query2Doc检索策略

    核心思想：
    1. 使用LLM将用户查询扩展为多个相关查询
    2. 对每个查询进行检索
    3. 使用RRF（倒数排名融合）合并结果

    适用场景：
    - 用户查询不明确
    - 需要多角度检索
    - 专业领域查询
    - 复杂概念理解

    优势：
    - 能够理解查询意图，生成相关查询
    - 多角度检索提高召回率
    - 对模糊或不完整查询效果好

    劣势：
    - 需要多次LLM调用
    - 延迟较高
    - 成本较高
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        self.vector_store = config.get("vector_store")

        # LLM配置
        llm_provider = config.get("llm_provider", "dashscope")
        if llm_provider == "dashscope":
            from src.service.llm_service import LLMService
            llm_config = {
                "provider": "dashscope",
                "model": config.get("model", "qwen-plus"),
                "temperature": config.get("temperature", 0.7),
            }
            self.llm_service = LLMService(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # 查询扩展配置
        self.num_expansions = config.get("num_expansions", 3)
        self.expansion_prompt_template = config.get(
            "expansion_prompt_template",
            "请为以下查询生成 {num} 个相关的查询变体。"
            "这些查询应该从不同角度或使用不同的表达方式来获取相关信息。"
            "每行一个查询，不要添加任何解释。\n\n原始查询：{query}\n\n相关查询："
        )

        # 是否使用Reranker
        self.use_reranker = config.get("use_reranking", True)
        if self.use_reranker:
            self.reranker = Reranker(
                model_name=config.get("reranker_model", "BAAI/bge-reranker-large")
            )

        # RRF参数
        self.rrf_k = config.get("rrf_k", 60)

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """执行Query2Doc检索"""
        try:
            # 1. 生成扩展查询
            expanded_queries = await self._expand_query(query)

            logger.info(f"Generated {len(expanded_queries)} expanded queries for: {query[:50]}...")

            # 2. 对每个查询进行检索
            all_results = []
            for i, expanded_query in enumerate(expanded_queries):
                results = await self._vector_search(
                    expanded_query,
                    k=k,
                    filter_dict=filter_dict
                )

                # 标记来源查询
                for doc in results:
                    doc.metadata["source_query"] = f"query_{i}"

                all_results.append(results)

            # 3. RRF融合
            fused_results = self._reciprocal_rank_fusion(
                all_results,
                k=k,
                rrf_k=self.rrf_k
            )

            # 4. 如果启用Reranker，重新排序
            if self.use_reranker and self.reranker and self.reranker.is_available():
                fused_results = await self._rerank(query, fused_results, k=k)

            logger.info(f"Query2Doc retrieval completed: {len(fused_results)} results")
            return fused_results

        except Exception as e:
            logger.error(f"Query2Doc retrieval failed: {e}")
            # 降级到原始查询
            logger.warning("Falling back to original query")
            return await self._vector_search(query, k=k, filter_dict=filter_dict)

    async def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """执行Query2Doc检索（带分数）"""
        results = await self.search(query, k=k, filter_dict=filter_dict)
        # 返回固定分数
        return [(doc, 1.0) for doc in results]

    async def _expand_query(self, query: str) -> List[str]:
        """使用LLM扩展查询"""
        try:
            prompt = self.expansion_prompt_template.format(
                num=self.num_expansions,
                query=query
            )

            # 调用LLM
            response = await self.llm_service.generate(prompt)

            # 解析响应
            lines = response.strip().split('\n')
            expanded_queries = []

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):  # 跳过注释
                    # 移除可能的编号前缀
                    line = line.lstrip('0123456789.-.')
                    line = line.strip()
                    if line:
                        expanded_queries.append(line)

            # 确保至少包含原始查询
            if query not in expanded_queries:
                expanded_queries.insert(0, query)

            # 限制数量
            expanded_queries = expanded_queries[:self.num_expansions + 1]

            if not expanded_queries:
                # 如果LLM失败，返回原始查询
                logger.warning("Failed to expand query, using original query")
                return [query]

            logger.debug(f"Expanded queries: {expanded_queries}")
            return expanded_queries

        except Exception as e:
            logger.error(f"Failed to expand query: {e}")
            return [query]

    async def _vector_search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None
    ) -> List[Document]:
        """向量搜索"""
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

    def _reciprocal_rank_fusion(
        self,
        all_results: List[List[Document]],
        k: int = 5,
        rrf_k: int = 60
    ) -> List[Document]:
        """
        倒数排名融合 (RRF)

        Args:
            all_results: 来自多个查询的结果列表
            k: 返回结果数量
            rrf_k: RRF常数
        """
        scores = {}

        # 为每个文档ID累加RRF分数
        for query_results in all_results:
            for rank, doc in enumerate(query_results, start=1):
                doc_id = doc.metadata.get("doc_id") or id(doc)

                if doc_id not in scores:
                    scores[doc_id] = {"doc": doc, "score": 0.0}

                # RRF公式: 1 / (rank + k)
                scores[doc_id]["score"] += 1.0 / (rank + rrf_k)

        # 按分数排序
        sorted_docs = sorted(
            scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )

        # 提取文档
        results = []
        for doc_id, item in sorted_docs[:k]:
            results.append(item["doc"])

        return results

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
            await self._vector_search("warmup query", k=1)
            logger.info("Query2DocStrategy warmup completed")
        except Exception as e:
            logger.warning(f"Query2DocStrategy warmup failed: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        self.vector_store = None
        logger.info("Query2DocStrategy cleanup completed")
