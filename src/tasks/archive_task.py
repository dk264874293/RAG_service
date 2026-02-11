"""
归档任务：定期执行Hot到Cold的文档迁移
"""

import asyncio
import logging
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


class ArchiveTaskManager:
    """
    归档任务管理器

    功能：
    1. 定时归档任务（每天凌晨执行）
    2. 手动触发归档
    3. 定时重建Cold Index
    4. 监控和告警
    """

    def __init__(self, generational_index_store, config):
        self.index_store = generational_index_store
        self.config = config

        # 调度器
        self.scheduler = AsyncIOScheduler()

        # 归档配置
        self.archive_schedule = getattr(config, "archive_schedule", "0 2 * * *")  # 默认每天凌晨2点
        self.rebuild_schedule = getattr(config, "rebuild_schedule", "0 3 * * 0")  # 默认每周日凌晨3点

        # 状态
        self.last_archive_result = None
        self.last_rebuild_result = None

    def start(self):
        """启动调度器"""
        # 解析cron表达式
        hour, minute = self.archive_schedule.split()[:2]
        hour = int(hour) if hour != "*" else 2
        minute = int(minute) if minute != "*" else 0

        # 添加归档任务
        self.scheduler.add_job(
            self._run_archive_task,
            'cron',
            hour=hour,
            minute=minute,
            id='archive_task',
            replace_existing=True
        )

        # 添加重建任务
        rebuild_hour, rebuild_minute = self.rebuild_schedule.split()[:2]
        rebuild_hour = int(rebuild_hour) if rebuild_hour != "*" else 3
        rebuild_minute = int(rebuild_minute) if rebuild_minute != "*" else 0

        self.scheduler.add_job(
            self._run_rebuild_task,
            'cron',
            hour=rebuild_hour,
            minute=rebuild_minute,
            day_of_week='sun',  # 每周日
            id='rebuild_task',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info(
            f"Archive task manager started: "
            f"archive at {hour:02d}:{minute:02d}, "
            f"rebuild at {rebuild_hour:02d}:{rebuild_minute:02d} on Sunday"
        )

    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("Archive task manager stopped")

    async def _run_archive_task(self):
        """执行归档任务"""
        try:
            logger.info("=" * 60)
            logger.info("Starting scheduled archive task...")
            logger.info("=" * 60)

            result = await self.index_store.archive_old_documents()
            self.last_archive_result = result

            logger.info(f"Archive task completed: {result}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Archive task failed: {e}", exc_info=True)

    async def _run_rebuild_task(self):
        """执行Cold Index重建任务"""
        try:
            logger.info("=" * 60)
            logger.info("Starting scheduled cold index rebuild task...")
            logger.info("=" * 60)

            # 检查是否需要重建
            needs_rebuild, reason = self.index_store.cold_index.should_rebuild()

            if needs_rebuild:
                logger.info(f"Rebuilding cold index: {reason}")
                success = await self.index_store.rebuild_cold_index()
                self.last_rebuild_result = {"success": success, "reason": reason}
            else:
                logger.info("Cold index rebuild not needed")
                self.last_rebuild_result = {"success": True, "reason": "Not needed"}

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Rebuild task failed: {e}", exc_info=True)

    async def trigger_archive_now(self, force: bool = False) -> dict:
        """
        手动触发归档

        Args:
            force: 是否强制归档所有Hot文档

        Returns:
            归档结果
        """
        logger.info(f"Manual archive triggered (force={force})")
        result = await self.index_store.archive_old_documents(force=force)
        self.last_archive_result = result
        return result

    async def trigger_rebuild_now(self) -> dict:
        """手动触发重建"""
        logger.info("Manual rebuild triggered")
        success = await self.index_store.rebuild_cold_index()
        self.last_rebuild_result = {"success": success}
        return self.last_rebuild_result

    def get_status(self) -> dict:
        """获取任务状态"""
        return {
            "scheduler_running": self.scheduler.running,
            "archive_schedule": self.archive_schedule,
            "rebuild_schedule": self.rebuild_schedule,
            "last_archive_result": self.last_archive_result,
            "last_rebuild_result": self.last_rebuild_result,
            "next_archive_time": self._get_next_run_time('archive_task'),
            "next_rebuild_time": self._get_next_run_time('rebuild_task'),
        }

    def _get_next_run_time(self, job_id: str) -> Optional[str]:
        """获取下次运行时间"""
        job = self.scheduler.get_job(job_id)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
        return None


# 单例
_archive_task_manager: Optional[ArchiveTaskManager] = None


def get_archive_task_manager() -> Optional[ArchiveTaskManager]:
    """获取归档任务管理器单例"""
    return _archive_task_manager


def init_archive_task_manager(generational_index_store, config):
    """初始化归档任务管理器"""
    global _archive_task_manager
    _archive_task_manager = ArchiveTaskManager(generational_index_store, config)
    return _archive_task_manager
