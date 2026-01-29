"""
查询重写和扩展模块
提高检索召回率通过查询优化和扩展
"""

import re
from typing import List, Dict, Set
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class QueryRewriter:
    """
    查询重写器

    提供查询优化、扩展和重写功能，提高检索召回率
    """

    def __init__(self):
        self.stopwords: Set[str] = {
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一个",
            "上",
            "也",
            "很",
            "到",
            "说",
            "要",
            "去",
            "你",
            "会",
            "着",
            "没有",
            "看",
            "好",
            "自己",
            "这",
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
        }

        self.synonyms: Dict[str, List[str]] = {
            "人工智能": ["AI", "机器智能", "智能系统"],
            "机器学习": ["ML", "算法训练", "模型训练"],
            "深度学习": ["DL", "神经网络", "深层网络"],
            "数据": ["信息", "资料", "数据集"],
            "算法": ["方法", "模型", "计算方法"],
            "分析": ["研究", "评估", "检测"],
            "优化": ["改进", "提升", "增强"],
            "系统": ["平台", "架构", "框架"],
            "检索": ["搜索", "查询", "查找"],
            "模型": ["算法", "网络", "架构"],
        }

    def rewrite_query(self, query: str) -> str:
        """
        重写查询：清理、标准化

        Args:
            query: 原始查询

        Returns:
            str: 重写后的查询
        """
        cleaned = query.strip()

        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned

    def expand_query(self, query: str, max_variants: int = 3) -> List[str]:
        """
        扩展查询：生成多个查询变体

        Args:
            query: 原始查询
            max_variants: 最大变体数量

        Returns:
            List[str]: 查询变体列表
        """
        variants = [query]

        synonyms_variants = self._expand_with_synonyms(query)
        variants.extend(synonyms_variants)

        keywords = self._extract_keywords(query)
        if len(keywords) > 1:
            keyword_variant = " ".join(keywords)
            if keyword_variant != query:
                variants.append(keyword_variant)

        unique_variants = []
        seen = set()
        for variant in variants:
            if variant not in seen and variant.strip():
                unique_variants.append(variant)
                seen.add(variant)
                if len(unique_variants) >= max_variants:
                    break

        return unique_variants

    def _expand_with_synonyms(self, query: str) -> List[str]:
        """
        使用同义词扩展查询

        Args:
            query: 原始查询

        Returns:
            List[str]: 同义词扩展的查询列表
        """
        variants = []

        for term, synonyms in self.synonyms.items():
            if term in query:
                for synonym in synonyms:
                    variant = query.replace(term, synonym, 1)
                    if variant != query:
                        variants.append(variant)

        return variants

    def _extract_keywords(self, query: str) -> List[str]:
        """
        提取关键词：移除停用词

        Args:
            query: 原始查询

        Returns:
            List[str]: 关键词列表
        """
        words = query.split()

        keywords = [
            word for word in words if word not in self.stopwords and len(word) > 1
        ]

        return keywords

    def enhance_query(self, query: str) -> Dict[str, any]:
        """
        增强查询：返回重写和扩展的查询集合

        Args:
            query: 原始查询

        Returns:
            Dict[str, any]: 包含原始查询、重写查询和扩展查询的字典
        """
        rewritten = self.rewrite_query(query)
        expanded = self.expand_query(query)

        return {
            "original": query,
            "rewritten": rewritten,
            "expanded": expanded,
            "count": len(expanded),
        }

    def merge_search_results(
        self, all_results: List[List[tuple]], k: int = 5
    ) -> List[tuple]:
        """
        合并多个查询的搜索结果

        使用倒数排名融合（Reciprocal Rank Fusion）算法

        Args:
            all_results: 所有查询的搜索结果列表
            k: 返回的top-k结果数量

        Returns:
            List[tuple]: 合并后的结果列表
        """
        scores = {}

        for results in all_results:
            for rank, (doc, score) in enumerate(results, start=1):
                doc_id = doc.metadata.get("doc_id", doc.id_)

                if doc_id not in scores:
                    scores[doc_id] = {"doc": doc, "score": 0.0}

                scores[doc_id]["score"] += 1.0 / (rank + 60)

        sorted_results = sorted(
            scores.items(), key=lambda x: x[1]["score"], reverse=True
        )

        merged_results = [
            (item["doc"], item["score"]) for doc_id, item in sorted_results[:k]
        ]

        return merged_results
