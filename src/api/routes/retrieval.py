"""
Retrieval API routes
Provides semantic search and similarity matching functionality
"""

import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.dependencies import get_retrieval_service
from src.vector.retrieval_service import RetrievalService
from src.models.document import Document
from src.utils.input_validation import ValidatedSearchRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retrieval", tags=["Retrieval Service"])


class SearchRequest(BaseModel, ValidatedSearchRequest):
    """Search request model with validation"""

    query: str = Field(..., description="Search query", min_length=1)
    k: int = Field(default=5, description="Number of results to return", ge=1, le=20)
    filters: Optional[Dict[str, Any]] = Field(
        None, description="Metadata filter conditions"
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
    total: int = Field(..., description="Total results")
    results: List[SearchResult] = Field(..., description="Search results list")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """
    Semantic search documents

    Search for relevant documents using vector similarity.
    """
    try:
        logger.info(f"Received search request: query='{request.query}', k={request.k}")

        documents = await retrieval_service.search(
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

        logger.info(f"Search completed: returned {len(results)} results")

        return SearchResponse(query=request.query, total=len(results), results=results)

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search-with-scores")
async def search_documents_with_scores(
    query: str = Query(..., description="Search query", min_length=1),
    k: int = Query(default=5, description="Number of results to return", ge=1, le=20),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """
    Search documents with similarity scores

    Returns relevant documents with their similarity scores.
    """
    try:
        logger.info(f"Received search request (with scores): query='{query}', k={k}")

        documents_with_scores = await retrieval_service.search_with_scores(
            query=query, k=k
        )

        results = []
        for doc, score in documents_with_scores:
            results.append(
                SearchResult(
                    doc_id=doc.id_,
                    content=doc.page_content[:500],
                    metadata=doc.metadata,
                    score=score,
                )
            )

        logger.info(f"Search completed: returned {len(results)} results")

        return {"query": query, "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"Search with scores failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/stats")
async def get_index_stats(
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """
    Get vector index statistics

    Returns FAISS index status and statistics.
    """
    try:
        stats = retrieval_service.vector_store.get_stats()
        return {"status": "success", "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.post("/search-expanded")
async def search_documents_expanded(
    request: SearchRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """
    Semantic search with query expansion

    Uses query rewriting and expansion to improve recall.
    Returns documents along with query expansion information.
    """
    try:
        logger.info(
            f"Received expanded search request: query='{request.query}', k={request.k}"
        )

        result = await retrieval_service.search_with_expansion(
            query=request.query, k=request.k, filter_dict=request.filters
        )

        results = []
        for doc in result["results"]:
            results.append(
                SearchResult(
                    doc_id=doc.id_,
                    content=doc.page_content[:500],
                    metadata=doc.metadata,
                    score=None,
                )
            )

        logger.info(
            f"Expanded search completed: returned {len(results)} results, "
            f"expansion_used={result['expansion_used']}"
        )

        return {
            "query": request.query,
            "total": len(results),
            "results": results,
            "query_info": result["query_info"],
            "expansion_used": result["expansion_used"],
        }

    except Exception as e:
        logger.error(f"Expanded search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search-reranked")
async def search_documents_reranked(
    request: SearchRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
):
    """
    Semantic search with reranking

    Uses cross-encoder model to rerank results for better accuracy.
    Returns documents with reranking scores.
    """
    try:
        logger.info(
            f"Received reranked search request: query='{request.query}', k={request.k}"
        )

        result = await retrieval_service.search_with_reranking(
            query=request.query, k=request.k, filter_dict=request.filters
        )

        results = []
        for idx, doc in enumerate(result["results"]):
            score = (
                result["reranking_scores"][idx] if result["reranking_used"] else None
            )
            results.append(
                SearchResult(
                    doc_id=doc.id_,
                    content=doc.page_content[:500],
                    metadata=doc.metadata,
                    score=score,
                )
            )

        logger.info(
            f"Reranked search completed: returned {len(results)} results, "
            f"reranking_used={result['reranking_used']}"
        )

        return {
            "query": request.query,
            "total": len(results),
            "results": results,
            "reranking_used": result["reranking_used"],
            "reranking_scores": result["reranking_scores"],
        }

    except Exception as e:
        logger.error(f"Reranked search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
