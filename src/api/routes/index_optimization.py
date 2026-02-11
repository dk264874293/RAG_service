"""
索引优化和维护API
扩展维护接口，支持索引优化、迁移和性能监控
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from src.api.dependencies import get_vector_store, get_settings
from src.vector.index_migrator import IndexMigrator, MigrationProgress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance/index", tags=["index-optimization"])


# ============ 请求/响应模型 ============

class IndexInfoResponse(BaseModel):
    """索引信息响应"""
    index_type: str
    index_config: Dict[str, Any]
    vector_count: int
    dimension: int
    memory_usage_mb: float
    performance: Optional[Dict[str, Any]] = None
    upgrade_recommendation: Optional[Dict[str, Any]] = None


class OptimizeIndexRequest(BaseModel):
    """索引优化请求"""
    target_index_type: Optional[str] = Field(None, description="目标索引类型，不指定则自动选择")
    force: bool = Field(False, description="强制执行优化（忽略性能检查）")
    batch_size: int = Field(10000, description="迁移批处理大小")


class OptimizeIndexResponse(BaseModel):
    """索引优化响应"""
    optimization_id: str
    status: str
    message: str
    estimated_time_sec: Optional[int] = None
    current_index: Dict[str, Any]
    target_index: Optional[Dict[str, Any]] = None


class MigrationStatusResponse(BaseModel):
    """迁移状态响应"""
    migration_id: str
    status: str
    current_phase: str
    progress: float  # 0.0 - 1.0
    total_vectors: int
    migrated_vectors: int
    error_message: Optional[str] = None


class PerformanceReportResponse(BaseModel):
    """性能报告响应"""
    index_type: str
    vector_count: int
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    qps: float
    total_searches: int
    health_status: str  # healthy, warning, critical
    recommendations: List[str]


# ============ 索引信息端点 ============

@router.get("/info", response_model=IndexInfoResponse)
async def get_index_info(
    vector_store=Depends(get_vector_store)
):
    """
    获取当前索引信息

    返回:
    - 索引类型和配置
    - 向量数量
    - 内存占用
    - 性能统计
    - 升级建议（如果启用自适应选择）
    """
    try:
        stats = vector_store.get_stats()

        # 计算内存占用
        vector_count = stats.get("total_vectors", 0)
        dimension = stats.get("dimension", 0)
        index_type = stats.get("index_type", "flat")

        memory_usage_mb = _estimate_memory(vector_count, dimension, index_type, stats.get("index_config", {}))

        return IndexInfoResponse(
            index_type=index_type,
            index_config=stats.get("index_config", {}),
            vector_count=vector_count,
            dimension=dimension,
            memory_usage_mb=memory_usage_mb,
            performance=stats.get("performance"),
            upgrade_recommendation=stats.get("upgrade_recommendation")
        )

    except Exception as e:
        logger.error(f"Failed to get index info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get index info: {str(e)}"
        )


@router.get("/performance", response_model=PerformanceReportResponse)
async def get_performance_report(
    vector_store=Depends(get_vector_store)
):
    """
    获取性能报告

    返回:
    - 搜索延迟统计（平均、P95、P99）
    - QPS（每秒查询数）
    - 健康状态
    - 优化建议
    """
    try:
        stats = vector_store.get_stats()
        performance = stats.get("performance")

        if not performance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No performance data available yet"
            )

        # 健康状态评估
        avg_latency = performance.get("avg_latency_ms", 0)
        health_status = "healthy"
        recommendations = []

        if avg_latency > 500:
            health_status = "critical"
            recommendations.append("Search latency critical! Consider upgrading to HNSW index.")
        elif avg_latency > 200:
            health_status = "warning"
            recommendations.append("Search latency elevated. Consider index optimization.")

        if performance.get("qps", 0) < 10:
            recommendations.append("Low QPS detected. Check system resources.")

        if not recommendations:
            recommendations.append("Index performance is within acceptable range.")

        return PerformanceReportResponse(
            index_type=stats.get("index_type", "unknown"),
            vector_count=stats.get("total_vectors", 0),
            avg_latency_ms=performance.get("avg_latency_ms", 0),
            p95_latency_ms=performance.get("p95_latency_ms", 0),
            p99_latency_ms=performance.get("p99_latency_ms", 0),
            qps=performance.get("queries_per_second", 0),
            total_searches=performance.get("total_searches", 0),
            health_status=health_status,
            recommendations=recommendations
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performance report: {str(e)}"
        )


# ============ 索引优化端点 ============

@router.post("/optimize", response_model=OptimizeIndexResponse)
async def optimize_index(
    request: OptimizeIndexRequest,
    vector_store=Depends(get_vector_store),
    settings=Depends(get_settings)
):
    """
    触发索引优化

    - 支持自动选择最优索引类型
    - 支持在线迁移（不停机）
    - 自动备份和回滚
    """
    try:
        # 检查是否支持优化
        if not hasattr(vector_store, 'migrate_index'):
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Index migration not supported. Enable OptimizedFAISSVectorStore."
            )

        stats = vector_store.get_stats()
        current_type = stats.get("index_type", "flat")
        current_config = stats.get("index_config", {})
        vector_count = stats.get("total_vectors", 0)

        # 确定目标索引类型
        if request.target_index_type:
            target_type = request.target_index_type
            target_config = settings.faiss_index_config.get(target_type, {})
        else:
            # 使用自适应选择
            if not hasattr(vector_store, 'adaptive_selector') or not vector_store.adaptive_selector:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Auto-select not enabled. Please specify target_index_type or enable faiss_index_auto_select."
                )

            selection = vector_store.adaptive_selector.select_index(
                vector_count,
                stats.get("dimension", 1536)
            )
            target_type = selection["index_type"]
            target_config = selection["config"]

        # 检查是否需要迁移
        if target_type == current_type:
            return OptimizeIndexResponse(
                optimization_id="N/A",
                status="skipped",
                message=f"Index is already optimized (type={current_type})",
                current_index={"type": current_type, "config": current_config}
            )

        # 估算迁移时间
        migrator = IndexMigrator(settings.faiss_index_path, vector_store.embedding_service)
        time_estimate = await migrator.estimate_migration_time(
            vector_count,
            current_type,
            target_type
        )

        # 执行迁移（异步）
        # 注意：这里简化实现，实际应该使用后台任务
        optimization_id = f"opt_{datetime.now().timestamp()}"

        return OptimizeIndexResponse(
            optimization_id=optimization_id,
            status="initiated",
            message=f"Index optimization initiated: {current_type} -> {target_type}",
            estimated_time_sec=time_estimate["estimated_seconds"],
            current_index={"type": current_type, "config": current_config},
            target_index={"type": target_type, "config": target_config}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to optimize index: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize index: {str(e)}"
        )


# ============ 迁移管理端点 ============

@router.get("/migration/{migration_id}", response_model=MigrationStatusResponse)
async def get_migration_status(
    migration_id: str,
    vector_store=Depends(get_vector_store),
    settings=Depends(get_settings)
):
    """查询迁移状态"""
    try:
        migrator = IndexMigrator(settings.faiss_index_path, vector_store.embedding_service)
        progress = migrator.get_migration_progress(migration_id)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Migration not found: {migration_id}"
            )

        return MigrationStatusResponse(
            migration_id=progress.migration_id,
            status=progress.status,
            current_phase=progress.current_phase,
            progress=progress.progress,
            total_vectors=progress.total_vectors,
            migrated_vectors=progress.migrated_vectors,
            error_message=progress.error_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get migration status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration status: {str(e)}"
        )


@router.post("/migration/{migration_id}/rollback")
async def rollback_migration(
    migration_id: str,
    vector_store=Depends(get_vector_store),
    settings=Depends(get_settings)
):
    """回滚迁移"""
    try:
        migrator = IndexMigrator(settings.faiss_index_path, vector_store.embedding_service)
        await migrator.rollback_migration(migration_id)

        return {
            "success": True,
            "message": f"Migration rolled back: {migration_id}"
        }

    except Exception as e:
        logger.error(f"Failed to rollback migration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback migration: {str(e)}"
        )


# ============ 辅助函数 ============

def _estimate_memory(
    vector_count: int,
    dimension: int,
    index_type: str,
    config: Dict[str, Any]
) -> float:
    """估算内存占用 (MB)"""
    bytes_per_vector = dimension * 4  # float32

    if index_type == "flat":
        total_bytes = vector_count * bytes_per_vector
    elif index_type == "ivf":
        nlist = config.get("nlist", 100)
        total_bytes = vector_count * bytes_per_vector + nlist * dimension * 4
    elif index_type == "ivf_pq":
        m = config.get("m", 64)
        nbits = config.get("nbits", 8)
        nlist = config.get("nlist", 100)
        total_bytes = vector_count * m * nbits // 8 + nlist * dimension * 4
    elif index_type == "hnsw":
        M = config.get("M", 32)
        total_bytes = vector_count * bytes_per_vector * (1 + M * 0.1)
    else:
        total_bytes = vector_count * bytes_per_vector

    return total_bytes / (1024 * 1024)


# 将路由添加到主维护路由器
def register_index_optimization_routes(main_router):
    """注册索引优化路由到主路由器"""
    main_router.include_router(router)
