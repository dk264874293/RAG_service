"""
Vector service type definitions
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VectorSearchResult(BaseModel):
    """Vector search result with document and score"""

    doc_id: str = Field(..., description="Document ID")
    content: str = Field(..., description="Document content preview")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    score: Optional[float] = Field(None, description="Similarity score")


class IndexStats(BaseModel):
    """Vector index statistics"""

    total_vectors: int = Field(..., description="Total number of vectors in index")
    index_path: str = Field(..., description="Path to FAISS index")
    dimension: int = Field(..., description="Vector dimension")
