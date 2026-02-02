import logging

from fastapi import APIRouter, Depends, HTTPException

from pydantic import BaseModel, Field

from src.api.dependencies import get_vector_service, get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vector", tags=["Vector Management"])


class IndexStatsResponse(BaseModel):
    index_path: str = Field(..., description="向量索引文件路径")
    total_vectors: int = Field(..., description="总向量数")
    active_vectors: int = Field(..., description="活跃向量数")
    deleted_vectors: int = Field(..., description="已删除向量数")
    dimension: int = Field(..., description="向量维度")


class RebuildResponse(BaseModel):
    status: str = Field(..., description="重建状态")
    message: str = Field(..., description="详细信息")
    active_vectors: int = Field(..., description="活跃向量数")


@router.get("/stats", response_model=IndexStatsResponse)
async def get_index_stats(vector_store=Depends(get_vector_store)):
    """
    获取向量索引统计信息

    返回向量索引的详细统计，包括总向量数、活跃向量数、已删除向量数和维度信息。
    """
    try:
        stats = vector_store.get_stats()
        return IndexStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Failed to get index stats: {e}")
        raise HTTPException(status_code=500, detail=f"获取索引统计失败: {str(e)}")


@router.post("/rebuild", response_model=RebuildResponse)
async def rebuild_index(vector_store=Depends(get_vector_store)):
    """
    重建向量索引

    清除软删除的文档，重建索引以提高检索性能。
    建议定期执行此操作，特别是在大量删除文档后。
    """
    try:
        success = await vector_store.rebuild_index()

        if success:
            stats = vector_store.get_stats()
            return RebuildResponse(
                status="success",
                message=f"索引重建成功，活跃向量数: {stats['active_vectors']}",
                active_vectors=stats["active_vectors"],
            )
        else:
            raise HTTPException(status_code=500, detail="索引重建失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rebuild index: {e}")
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")


@router.delete("/clear")
async def clear_all_vectors(vector_service=Depends(get_vector_service)):
    """
    清空所有向量索引

    删除所有向量数据，用于完全重置向量索引。
    警告：此操作不可逆，将删除所有已索引的文档。
    """
    try:
        from src.vector.vector_store import FAISSVectorStore
        from src.api.dependencies import get_settings

        settings = get_settings()
        vector_store = FAISSVectorStore(settings, vector_service.embedding_service)

        success = await vector_store.rebuild_index()
        vector_store.vector_store.save_local(vector_store.index_path)

        if success:
            return {"status": "success", "message": "所有向量已清空"}
        else:
            raise HTTPException(status_code=500, detail="清空向量失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear vectors: {e}")
        raise HTTPException(status_code=500, detail=f"清空向量失败: {str(e)}")
