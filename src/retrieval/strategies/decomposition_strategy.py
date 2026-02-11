"""
Decomposition检索策略实现
将复杂查询分解为多个子问题，分别检索后整合结果
"""

import logging
from typing import List, Dict, Any, Optional
import json

from .base import BaseRetrievalStrategy
from src.models.document import Document
from ...retrieval.reranker import Reranker

logger = logging.getLogger(__name__)


class DecompositionStrategy(BaseRetrievalStrategy):
    """
    Decomposition检索策略

    核心思想：
    1. 使用LLM将复杂查询分解为多个子问题
    2. 对每个子问题独立检索
    3. 整合所有子问题的结果
    4. 使用Reranker重新排序

    适用场景：
    - 复杂的多步骤问题
    - 比较分析类查询（"比较A和B的优缺点"）
    - 需要多角度检索的问题

    优势：
    - 处理复杂推理能力
    - 检索结果更全面
    - 减少单一检索的盲点

    劣势：
    - LLM调用增加延迟
    - 检索次数多，成本高
    - 结果整合可能复杂
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
                "temperature": config.get("temperature", 0.0),
            }
            self.llm_service = LLMService(llm_config)
        else:
            raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        # Decomposition配置
        self.max_sub_questions = config.get("max_sub_questions", 5)
        self.decomposition_prompt_template = config.get(
            "decomposition_prompt_template",
            "将以下复杂问题分解为{max}个子问题。"
            "每个子问题应该独立且可以从文档中找到答案。"
            "返回JSON格式: {{\"questions\": [\"问题1\", \"问题2\", ...]}}\n\n"
            "原始问题：{query}\n\n子问题："
        )

        # Reranker配置
        self.use_reranker = config.get("use_reranking", True)
        if self.use_reranker:
            self.reranker = Reranker(
                model_name=config.get("reranker_model", "BAAI/bge-reranker-large")
            )

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[Document]:
        """执行Decomposition检索"""
        try:
            # 1. 分解问题
            sub_questions = await self._decompose_query(query)

            if not sub_questions or len(sub_questions) <= 1:
                # 只有一个子问题，等同于原始查询
                logger.info("Query not decomposed, using direct search")
                return await self._vector_search(query, k, filter_dict)

            logger.info(f"Query decomposed into {len(sub_questions)} sub-questions")

            # 2. 对每个子问题检索
            all_results = []
            per_question_k = max(k // len(sub_questions), 2)  # 每个子问题的结果数

            for i, sub_q in enumerate(sub_questions):
                logger.info(f"Searching for sub-question {i+1}/{len(sub_questions)}: {sub_q}")
                results = await self._vector_search(sub_q, per_question_k, filter_dict)

                # 标记来源子问题
                for doc in results:
                    doc.metadata["source_sub_question"] = f"q{i+1}"
                    doc.metadata["sub_question"] = sub_q

                all_results.append(results)

            # 3. 整合结果（去重和排序）
            integrated_results = self._integrate_results(all_results, k)

            # 4. Rerank
            if self.use_reranker and self.reranker and self.reranker.is_available():
                integrated_results = await self._rerank(query, integrated_results, k)

            logger.info(f"Decomposition retrieval completed: {len(integrated_results)} results")
            return integrated_results

        except Exception as e:
            logger.error(f"Decomposition retrieval failed: {e}")
            # 降级到简单检索
            return await self._vector_search(query, k, filter_dict)

    async def search_with_scores(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict] = None,
        **kwargs
    ) -> List[tuple[Document, float]]:
        """执行Decomposition检索（带分数）"""
        results = await self.search(query, k, filter_dict)
        return [(doc, 1.0) for doc in results]

    async def _decompose_query(self, query: str) -> List[str]:
        """使用LLM分解查询"""
        try:
            prompt = self.decomposition_prompt_template.format(
                max=self.max_sub_questions,
                query=query
            )

            response = await self.llm_service.generate(prompt)

            # 解析JSON响应
            try:
                result = json.loads(response.strip())
                questions = result.get("questions", [])
            except json.JSONDecodeError:
                # 如果返回的不是有效JSON，尝试按行解析
                lines = response.strip().split('\n')
                questions = [line.strip().strip('"').strip("'") for line in lines if line.strip()]

            # 确保至少包含原始查询
            if query not in questions:
                questions.insert(0, query)

            # 限制数量
            questions = questions[:self.max_sub_questions]

            if not questions:
                logger.warning("Failed to decompose query, using original query")
                return [query]

            logger.debug(f"Decomposed questions: {questions}")
            return questions

        except Exception as e:
            logger.error(f"Failed to decompose query: {e}")
            return [query]

    async def _vector_search(
        self,
        query: str,
        k: int,
        filter_dict: Optional[Dict] = None,
    ) -> List[Document]:
        """向量搜索"""
        if not self.vector_store:
            return []

        try:
            if hasattr(self.vector_store, 'similarity_search'):
                results = await self.vector_store.similarity_search(
                    query, k=k, filter=filter_dict
                )
            else:
                # LangChain FAISS
                results = await self.vector_store.similarity_search(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _integrate_results(
        self,
        all_results: List[List[Document]],
        k: int,
    ) -> List[Document]:
        """
        整合多个子问题的结果

        策略：
        1. 去重（基于文档内容或ID）
        2. 根据在子问题中的出现次数加权
        3. 按加权分数排序
        """
        from collections import defaultdict

        # 使用内容哈希去重
        doc_scores = defaultdict(float)
        doc_objects = {}

        for question_results in all_results:
            for doc in question_results:
                # 使用内容哈希作为唯一标识
                content_hash = hash(doc.page_content)

                if content_hash not in doc_objects:
                    doc_objects[content_hash] = doc

                # 增加权重（被多个子问题检索到 = 更相关）
                doc_scores[content_hash] += 1.0

        # 按分数排序
        sorted_hashes = sorted(
            doc_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 返回top-k文档
        results = []
        for content_hash, score in sorted_hashes[:k]:
            doc = doc_objects[content_hash]
            # 添加元数据标记
            doc.metadata["decomposition_score"] = score
            doc.metadata["source_questions"] = doc.metadata.get("source_sub_question", [])
            results.append(doc)

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
            logger.info("DecompositionStrategy warmup completed")
        except Exception as e:
            logger.warning(f"DecompositionStrategy warmup failed: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        self.vector_store = None
        logger.info("DecompositionStrategy cleanup completed")
