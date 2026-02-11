"""
维护和监控API接口
用于分代索引的维护操作
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.api.dependencies import get_vector_store, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


class ArchiveResponse(BaseModel):
    """归档响应"""
    archived_count: int
    hot_size_before: int
    hot_size_after: int
    cold_size_before: int
    cold_size_after: int


class RebuildResponse(BaseModel):
    """重建响应"""
    success: bool
    reason: str = ""


class IndexStatsResponse(BaseModel):
    """索引统计响应"""
    hot_index: Dict[str, Any]
    cold_index: Dict[str, Any]
    routing_table: Dict[str, Any]
    total_documents: int
    needs_archive: bool
    needs_cold_rebuild: bool


@router.post("/index/archive", response_model=Dict[str, Any])
async def trigger_archive(
    force: bool = False,
    vector_store=Depends(get_vector_store)
):
    """
    手动触发归档任务

    参数：
    - force: 是否强制归档所有Hot文档（默认false）
    """
    # 检查是否支持分代索引
    if not hasattr(vector_store, 'archive_old_documents'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Generational index not enabled. Set enable_generational_index=true in config."
        )

    logger.info(f"Manual archive triggered (force={force})")
    result = await vector_store.archive_old_documents(force=force)

    return {
        "success": True,
        "message": f"Archived {result['archived_count']} documents",
        "data": result
    }


@router.post("/index/rebuild-cold", response_model=Dict[str, Any])
async def rebuild_cold_index(vector_store=Depends(get_vector_store)):
    """
    手动触发Cold Index重建
    移除软删除的文档，优化索引性能
    """
    if not hasattr(vector_store, 'rebuild_cold_index'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Generational index not enabled."
        )

    logger.info("Manual cold index rebuild triggered")

    # 检查是否需要重建
    needs_rebuild, reason = vector_store.cold_index.should_rebuild()

    if not needs_rebuild:
        return {
            "success": True,
            "message": "Rebuild not needed",
            "reason": reason
        }

    success = await vector_store.rebuild_cold_index()

    return {
        "success": success,
        "message": "Cold index rebuilt successfully" if success else "Rebuild failed",
        "reason": reason
    }


@router.get("/index/stats", response_model=Dict[str, Any])
async def get_index_stats(vector_store=Depends(get_vector_store)):
    """
    获取索引统计信息

    返回：
    - hot_index: Hot索引统计
    - cold_index: Cold索引统计
    - routing_table: 路由表统计
    - total_documents: 总文档数
    - needs_archive: 是否需要归档
    - needs_cold_rebuild: Cold索引是否需要重建
    """
    if not hasattr(vector_store, 'get_stats'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Generational index not enabled."
        )

    return vector_store.get_stats()


@router.get("/index/health", response_model=Dict[str, Any])
async def check_index_health(vector_store=Depends(get_vector_store)):
    """
    检查索引健康状态

    返回健康指标和建议操作
    """
    if not hasattr(vector_store, 'get_stats'):
        return {
            "status": "generational_index_not_enabled",
            "recommendations": ["Enable generational index for better performance"]
        }

    stats = vector_store.get_stats()
    health_status = "healthy"
    recommendations = []

    # 检查Hot Index容量
    hot_utilization = stats["hot_index"]["size"] / stats["hot_index"]["max_size"]
    if hot_utilization > 0.9:
        health_status = "warning"
        recommendations.append("Hot Index is >90% full, archive immediately")
    elif hot_utilization > 0.8:
        health_status = "warning"
        recommendations.append("Hot Index is >80% full, consider archiving")

    # 检查Cold Index删除率
    cold_deletion_rate = float(stats["cold_index"]["deletion_rate"].rstrip("%")) / 100
    if cold_deletion_rate > 0.3:
        health_status = "warning"
        recommendations.append("Cold Index deletion rate >30%, rebuild recommended")

    # 检查软删除文档数
    cold_deleted = stats["cold_index"]["deleted_count"]
    if cold_deleted > 10000:
        health_status = "warning"
        recommendations.append(f"Cold Index has {cold_deleted} deleted documents, rebuild recommended")

    if health_status == "healthy":
        recommendations.append("All systems operating normally")

    return {
        "status": health_status,
        "recommendations": recommendations,
        "stats": stats
    }


@router.post("/tasks/start")
async def start_maintenance_tasks(settings=Depends(get_settings)):
    """
    启动定时维护任务
    """
    from src.tasks.archive_task import init_archive_task_manager, get_archive_task_manager

    vector_store = get_vector_store()

    if not hasattr(vector_store, 'archive_old_documents'):
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Generational index not enabled."
        )

    # 初始化任务管理器
    manager = init_archive_task_manager(vector_store, settings)
    manager.start()

    return {
        "success": True,
        "message": "Maintenance tasks started",
        "schedule": {
            "archive": settings.archive_schedule,
            "rebuild": getattr(settings, "rebuild_schedule", "0 3 * * 0")
        }
    }


@router.get("/tasks/status")
async def get_tasks_status():
    """
    获取定时任务状态
    """
    from src.tasks.archive_task import get_archive_task_manager

    manager = get_archive_task_manager()

    if manager is None:
        return {
            "status": "not_initialized",
            "message": "Task manager not initialized. Call POST /tasks/start first."
        }

    return manager.get_status()


@router.post("/tasks/stop")
async def stop_maintenance_tasks():
    """
    停止定时维护任务
    """
    from src.tasks.archive_task import get_archive_task_manager

    manager = get_archive_task_manager()

    if manager is None:
        return {
            "success": True,
            "message": "Task manager not initialized"
        }

    manager.stop()

    return {
        "success": True,
        "message": "Maintenance tasks stopped"
    }
