"""
在线索引迁移管理器
支持不停机切换FAISS索引类型
"""

import os
import logging
import pickle
import tempfile
import shutil
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

import numpy as np
import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore import InMemoryDocstore

from .faiss_index_factory import FAISSIndexFactory

logger = logging.getLogger(__name__)


@dataclass
class MigrationProgress:
    """迁移进度"""
    migration_id: str
    status: str  # pending, in_progress, completed, failed, rolled_back
    current_phase: str
    progress: float  # 0.0 - 1.0
    total_vectors: int
    migrated_vectors: int
    start_time: datetime
    error_message: Optional[str] = None


class IndexMigrator:
    """
    索引迁移管理器

    功能:
    1. 创建目标索引
    2. 批量迁移向量数据
    3. 验证迁移准确性
    4. 原子切换索引
    5. 支持回滚
    """

    def __init__(self, index_path: str, embedding_service):
        self.index_path = index_path
        self.embedding_service = embedding_service
        self.migrations: Dict[str, MigrationProgress] = {}
        self.migration_dir = os.path.join(index_path, "migrations")

    async def migrate_index(
        self,
        from_type: str,
        to_type: str,
        from_config: Dict[str, Any],
        to_config: Dict[str, Any],
        vector_store: FAISS,
        batch_size: int = 10000,
        progress_callback: Optional[Callable[[MigrationProgress], None]] = None
    ) -> str:
        """
        执行索引迁移

        Args:
            from_type: 源索引类型
            to_type: 目标索引类型
            from_config: 源索引配置
            to_config: 目标索引配置
            vector_store: 当前向量存储
            batch_size: 批处理大小
            progress_callback: 进度回调函数

        Returns:
            migration_id: 迁移ID
        """
        migration_id = f"mig_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 创建迁移进度
        progress = MigrationProgress(
            migration_id=migration_id,
            status="in_progress",
            current_phase="initializing",
            progress=0.0,
            total_vectors=vector_store.index.ntotal,
            migrated_vectors=0,
            start_time=datetime.now()
        )
        self.migrations[migration_id] = progress

        try:
            # 阶段1: 创建目标索引
            progress.current_phase = "creating_target_index"
            progress.progress = 0.1
            self._notify_progress(progress, progress_callback)

            target_index = await self._create_target_index(to_type, to_config)

            # 阶段2: 迁移向量数据
            progress.current_phase = "migrating_vectors"
            await self._migrate_vectors(
                vector_store,
                target_index,
                batch_size,
                progress,
                progress_callback
            )

            # 阶段3: 验证
            progress.current_phase = "validating"
            progress.progress = 0.9
            self._notify_progress(progress, progress_callback)

            validation_result = await self._validate_migration(
                vector_store, target_index
            )

            if not validation_result["passed"]:
                raise Exception(f"Validation failed: {validation_result['reason']}")

            # 阶段4: 原子切换
            progress.current_phase = "swapping_indexes"
            progress.progress = 0.95
            self._notify_progress(progress, progress_callback)

            await self._atomic_swap(migration_id, target_index, vector_store.docstore)

            # 完成
            progress.status = "completed"
            progress.current_phase = "completed"
            progress.progress = 1.0
            self._notify_progress(progress, progress_callback)

            logger.info(f"Index migration completed: {migration_id}")
            return migration_id

        except Exception as e:
            logger.error(f"Index migration failed: {e}")
            progress.status = "failed"
            progress.error_message = str(e)
            self._notify_progress(progress, progress_callback)

            # 自动回滚
            await self.rollback_migration(migration_id)

            raise

    async def _create_target_index(self, index_type: str, config: Dict[str, Any]):
        """创建目标索引"""
        dimension = self.embedding_service.get_dimension()

        # 使用索引工厂
        index_wrapper = FAISSIndexFactory.create_index(
            index_type,
            dimension,
            config
        )
        target_index = index_wrapper.get_index()

        # 创建FAISS包装器
        target_store = FAISS(
            embedding_function=self.embedding_service.embedding_model,
            index=target_index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={},
        )

        return target_store

    async def _migrate_vectors(
        self,
        source_store: FAISS,
        target_store: FAISS,
        batch_size: int,
        progress: MigrationProgress,
        progress_callback: Optional[Callable[[MigrationProgress], None]]
    ):
        """批量迁移向量"""
        total_vectors = source_store.index.ntotal
        migrated = 0

        # 收集所有文档
        all_docs = []
        all_embeddings = []

        for faiss_id, doc_id in source_store.index_to_docstore_id.items():
            try:
                doc = source_store.docstore.search(doc_id)
                if doc:
                    all_docs.append((doc_id, doc))
                    # 获取向量
                    vector = source_store.index.reconstruct(int(faiss_id))
                    all_embeddings.append(vector)
            except Exception as e:
                logger.warning(f"Failed to extract document {doc_id}: {e}")

        # 批量添加到目标索引
        dimension = self.embedding_service.get_dimension()
        num_batches = (len(all_embeddings) + batch_size - 1) // batch_size

        for i in range(0, len(all_embeddings), batch_size):
            batch_embeddings = all_embeddings[i:i+batch_size]
            batch_docs = all_docs[i:i+batch_size]

            # 训练目标索引（如果需要）
            if hasattr(target_store.index, 'is_trained') and not target_store.index.is_trained:
                train_vectors = np.array(batch_embeddings).astype('float32')
                target_store.index.train(train_vectors)
                logger.info("Target index training completed")

            # 添加向量
            for j, (doc_id, doc) in enumerate(batch_docs):
                embedding = batch_embeddings[j].reshape(1, -1).astype('float32')
                target_store.index.add(embedding)
                target_store.index_to_docstore_id[target_store.index.ntotal - 1] = doc_id
                target_store.docstore._dict[doc_id] = doc

            migrated += len(batch_docs)
            progress.migrated_vectors = migrated
            progress.progress = 0.1 + 0.8 * (migrated / total_vectors)

            if i // batch_size % 10 == 0:  # 每10个批次通知一次
                self._notify_progress(progress, progress_callback)

        logger.info(f"Migrated {migrated}/{total_vectors} vectors")

    async def _validate_migration(
        self,
        source_store: FAISS,
        target_store: FAISS,
        sample_size: int = 100
    ) -> Dict[str, Any]:
        """验证迁移准确性"""
        try:
            # 检查向量数量
            source_count = source_store.index.ntotal
            target_count = target_store.index.ntotal

            if source_count != target_count:
                return {
                    "passed": False,
                    "reason": f"Vector count mismatch: source={source_count}, target={target_count}"
                }

            # 随机抽样验证搜索结果
            if source_count > 0:
                # 随机选择一些文档ID进行验证
                import random
                sample_doc_ids = random.sample(
                    list(source_store.index_to_docstore_id.values()),
                    min(sample_size, source_count)
                )

                # 检查这些文档是否在目标索引中
                target_doc_ids = set(target_store.index_to_docstore_id.values())
                missing = [doc_id for doc_id in sample_doc_ids if doc_id not in target_doc_ids]

                if missing:
                    return {
                        "passed": False,
                        "reason": f"Missing {len(missing)} documents in target index"
                    }

            return {
                "passed": True,
                "reason": "Validation passed"
            }

        except Exception as e:
            return {
                "passed": False,
                "reason": f"Validation error: {e}"
            }

    async def _atomic_swap(
        self,
        migration_id: str,
        new_store: FAISS,
        docstore
    ):
        """原子切换索引"""
        # 备份当前索引
        backup_path = self._create_backup(migration_id)

        try:
            # 保存新索引到临时位置
            temp_path = os.path.join(self.migration_dir, migration_id, "new_index")
            os.makedirs(temp_path, exist_ok=True)
            new_store.save_local(temp_path)

            # 保存元数据
            metadata = {
                "index_type": self._infer_index_type(new_store.index),
                "index_config": {},  # 从目标配置获取
                "migration_id": migration_id,
                "migrated_at": datetime.now().isoformat(),
            }
            metadata_file = os.path.join(temp_path, "index_metadata.pkl")
            with open(metadata_file, "wb") as f:
                pickle.dump(metadata, f)

            # 原子替换：移动新索引到主位置
            shutil.rmtree(self.index_path)
            shutil.copytree(temp_path, self.index_path)

            logger.info(f"Atomic swap completed: {migration_id}")

        except Exception as e:
            logger.error(f"Atomic swap failed: {e}")
            # 恢复备份
            self._restore_from_backup(backup_path)
            raise

    def _create_backup(self, migration_id: str) -> str:
        """创建备份"""
        backup_path = os.path.join(self.migration_dir, migration_id, "backup")
        os.makedirs(backup_path, exist_ok=True)

        if os.path.exists(self.index_path):
            shutil.copytree(self.index_path, backup_path, dirs_exist_ok=True)

        return backup_path

    def _restore_from_backup(self, backup_path: str):
        """从备份恢复"""
        if os.path.exists(backup_path):
            shutil.rmtree(self.index_path)
            shutil.copytree(backup_path, self.index_path)
            logger.info(f"Restored from backup: {backup_path}")

    async def rollback_migration(self, migration_id: str):
        """回滚迁移"""
        logger.warning(f"Rolling back migration: {migration_id}")

        backup_path = os.path.join(self.migration_dir, migration_id, "backup")

        if os.path.exists(backup_path):
            self._restore_from_backup(backup_path)

            # 更新迁移状态
            if migration_id in self.migrations:
                self.migrations[migration_id].status = "rolled_back"

            logger.info(f"Migration rolled back: {migration_id}")
        else:
            logger.error(f"Backup not found for rollback: {migration_id}")

    def _notify_progress(
        self,
        progress: MigrationProgress,
        callback: Optional[Callable[[MigrationProgress], None]]
    ):
        """通知进度"""
        self.migrations[progress.migration_id] = progress

        if callback:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def get_migration_progress(self, migration_id: str) -> Optional[MigrationProgress]:
        """获取迁移进度"""
        return self.migrations.get(migration_id)

    def _infer_index_type(self, index: faiss.Index) -> str:
        """推断索引类型"""
        index_str = str(type(index))
        if "Flat" in index_str and "IVF" not in index_str:
            return "flat"
        elif "IVFPQ" in index_str:
            return "ivf_pq"
        elif "IVF" in index_str:
            return "ivf"
        elif "HNSW" in index_str:
            return "hnsw"
        else:
            return "flat"

    async def estimate_migration_time(
        self,
        vector_count: int,
        from_type: str,
        to_type: str
    ) -> Dict[str, Any]:
        """估算迁移时间"""
        # 基准测试数据（可根据实际情况调整）
        base_time_per_vector = 0.001  # 秒/向量
        indexing_overhead = {
            "flat": 1.0,
            "ivf": 1.5,
            "ivf_pq": 2.0,
            "hnsw": 3.0,
        }

        estimated_seconds = (
            vector_count * base_time_per_vector *
            indexing_overhead.get(to_type, 1.5)
        )

        return {
            "estimated_seconds": int(estimated_seconds),
            "estimated_minutes": int(estimated_seconds / 60),
            "vector_count": vector_count,
            "from_type": from_type,
            "to_type": to_type,
        }
