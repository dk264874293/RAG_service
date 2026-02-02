"""
语义检索API路由
提供语义搜索和相似度匹配功能
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from src.api.dependencies import get_retrieval_strategy
from config import settings
from src.utils.input_validation import ValidatedSearchRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retrieval", tags=["语义检索"])


class SearchRequest(BaseModel, ValidatedSearchRequest):
    """搜索请求模型"""

    query: str = Field(..., description="搜索查询文本", min_length=1)
    k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(None, description="元数据过滤条件")
    strategy: Optional[str] = Field(
        None,
        description="检索策略（覆盖默认值：vector, hybrid, parent_child）",
    )


class SearchResult(BaseModel):
    """搜索结果模型"""

    doc_id: str = Field(..., description="文档ID")
    content: str = Field(..., description="文档内容预览")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="文档元数据")
    score: Optional[float] = Field(None, description="相似度分数")


class SearchResponse(BaseModel):
    """搜索响应模型"""

    query: str = Field(..., description="搜索查询")
    strategy: str = Field(..., description="使用的检索策略")
    total: int = Field(..., description="结果总数")
    results: List[SearchResult] = Field(..., description="搜索结果列表")


class StrategiesResponse(BaseModel):
    """策略列表响应模型"""

    strategies: List[str] = Field(..., description="可用策略列表")
    current: str = Field(..., description="当前默认策略")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    retrieval_strategy=Depends(get_retrieval_strategy),
):
    """
    语义搜索文档（可配置检索策略）

    支持通过请求参数覆盖检索策略：
    - vector: 基础向量搜索
    - hybrid: 向量搜索 + BM25，使用RRF融合
    - parent_child: 父子索引，提供更好的上下文
    """
    try:
        strategy_name = request.strategy or settings.retrieval_strategy

        logger.info(
            f"Received search request: query='{request.query}', k={request.k}, "
            f"strategy={strategy_name}"
        )

        documents = await retrieval_strategy.search(
            query=request.query, k=request.k, filter_dict=request.filters
        )

        results = []
        for doc in documents:
            results.append(
                SearchResult(
                    doc_id=doc.id_,
                    content=doc.page_content[:500],
                    metadata=doc.metadata,
                    score=None,
                )
            )

        return SearchResponse(
            query=request.query,
            strategy=strategy_name,
            total=len(results),
            results=results,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/strategies")
async def get_available_strategies():
    """获取可用的检索策略列表"""
    try:
        from src.retrieval.strategies.factory import RetrievalStrategyFactory

        strategies = RetrievalStrategyFactory.get_available_strategies()

        return StrategiesResponse(
            strategies=strategies, current=settings.retrieval_strategy
        )

    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
