"""
Retrieval API routes
Provides semantic search and similarity matching functionality
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from pydantic import BaseModel, Field

from src.api.dependencies import get_settings, get_retrieval_strategy
from config import settings
from src.utils.input_validation import ValidatedSearchRequest
from src.models.document import Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retrieval", tags=["Retrieval Service"])


class SearchRequest(BaseModel, ValidatedSearchRequest):
    """Search request model with validation"""

    query: str = Field(..., description="Search query", min_length=1)
    k: int = Field(default=5, description="Number of results to return", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Metadata filter conditions"
    )
    strategy: Optional[str] = Field(
        None,
        description="Retrieval strategy to override default (vector, hybrid, parent_child)",
    )


class SearchResult(BaseModel):
    """Search result model"""

    doc_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content preview")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    score: Optional[float] = Field(None, description="Similarity score")


class SearchResponse(BaseModel):
    """Search response model"""

    query: str = Field(..., description="Search query")
    strategy: str = Field(..., description="Retrieval strategy used")
    total: int = Field(..., description="Total results")
    results: List[SearchResult] = Field(..., description="Search results list")


class StrategiesResponse(BaseModel):
    """Strategies response model"""

    strategies: List[str] = Field(..., description="Available strategies")
    current: str = Field(..., description="Current default strategy")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    retrieval_strategy=Depends(get_retrieval_strategy),
):
    """
    Semantic search documents with configurable strategy

    Supports strategy override via request parameter:
    - vector: Basic vector search
    - hybrid: Vector + BM25 with RRF fusion
    - parent_child: Parent-child indexing for better context
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
    """Get list of available retrieval strategies"""
    try:
        from src.retrieval.strategies.factory import RetrievalStrategyFactory

        strategies = RetrievalStrategyFactory.get_available_strategies()

        return StrategiesResponse(
            strategies=strategies, current=settings.retrieval_strategy
        )

    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))
