"""
路由表：维护文档ID到索引类型的映射
使用SQLite持久化，支持高效查询
"""

import sqlite3
import logging
from typing import Optional, List, Tuple, Dict
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)


class RoutingTable:
    """
    文档路由表

    职责：
    1. 维护 doc_id → index_type (hot/cold) 的映射
    2. 维护 file_id → doc_ids 的映射（用于批量删除）
    3. 提供高效的查询接口
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with self._get_conn() as conn:
            # 主表：文档路由
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_routing (
                    doc_id TEXT PRIMARY KEY,
                    index_type TEXT NOT NULL CHECK(index_type IN ('hot', 'cold')),
                    file_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 索引：按file_id查询
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_id
                ON document_routing(file_id)
            """)

            # 索引：按index_type查询
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_index_type
                ON document_routing(index_type)
            """)

            # 触发器：更新updated_at
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS update_timestamp
                AFTER UPDATE ON document_routing
                FOR EACH ROW
                BEGIN
                    UPDATE document_routing SET updated_at = CURRENT_TIMESTAMP
                    WHERE doc_id = NEW.doc_id;
                END
            """)

            conn.commit()

        logger.info(f"Routing table initialized at {self.db_path}")

    def set_location(
        self,
        doc_id: str,
        index_type: str,
        file_id: Optional[str] = None
    ) -> bool:
        """
        设置文档位置

        Args:
            doc_id: 文档ID
            index_type: 索引类型 (hot/cold)
            file_id: 文件ID（可选）

        Returns:
            是否成功
        """
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT INTO document_routing (doc_id, index_type, file_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(doc_id) DO UPDATE SET
                        index_type = excluded.index_type,
                        file_id = excluded.file_id,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (doc_id, index_type, file_id)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to set location for doc_id={doc_id}: {e}")
            return False

    def get_location(self, doc_id: str) -> Optional[str]:
        """
        获取文档所在索引类型

        Args:
            doc_id: 文档ID

        Returns:
            索引类型 (hot/cold) 或 None
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT index_type FROM document_routing WHERE doc_id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            return row["index_type"] if row else None

    def get_by_file_id(self, file_id: str) -> List[Tuple[str, str]]:
        """
        获取文件的所有文档及其位置

        Args:
            file_id: 文件ID

        Returns:
            [(doc_id, index_type), ...]
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT doc_id, index_type
                FROM document_routing
                WHERE file_id = ?
                """,
                (file_id,)
            )
            return [(row["doc_id"], row["index_type"]) for row in cursor.fetchall()]

    def get_all_by_type(self, index_type: str, limit: Optional[int] = None) -> List[str]:
        """
        获取指定索引类型的所有文档ID

        Args:
            index_type: 索引类型 (hot/cold)
            limit: 限制返回数量

        Returns:
            [doc_id, ...]
        """
        with self._get_conn() as conn:
            if limit:
                cursor = conn.execute(
                    """
                    SELECT doc_id FROM document_routing
                    WHERE index_type = ?
                    LIMIT ?
                    """,
                    (index_type, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT doc_id FROM document_routing WHERE index_type = ?",
                    (index_type,)
                )
            return [row["doc_id"] for row in cursor.fetchall()]

    def delete(self, doc_id: str) -> bool:
        """
        删除路由记录

        Args:
            doc_id: 文档ID

        Returns:
            是否成功
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM document_routing WHERE doc_id = ?",
                    (doc_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete routing for doc_id={doc_id}: {e}")
            return False

    def delete_by_file_id(self, file_id: str) -> int:
        """
        删除文件的所有路由记录

        Args:
            file_id: 文件ID

        Returns:
            删除的记录数
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM document_routing WHERE file_id = ?",
                    (file_id,)
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to delete routing for file_id={file_id}: {e}")
            return 0

    def batch_set_location(
        self,
        records: List[Tuple[str, str, Optional[str]]]
    ) -> int:
        """
        批量设置文档位置

        Args:
            records: [(doc_id, index_type, file_id), ...]

        Returns:
            成功插入的记录数
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.executemany(
                    """
                    INSERT INTO document_routing (doc_id, index_type, file_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(doc_id) DO UPDATE SET
                        index_type = excluded.index_type,
                        file_id = excluded.file_id
                    """,
                    records
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to batch set locations: {e}")
            return 0

    def get_stats(self) -> Dict[str, int]:
        """
        获取统计信息

        Returns:
            {
                "total": 总文档数,
                "hot": Hot索引文档数,
                "cold": Cold索引文档数,
                "files": 文件数
            }
        """
        with self._get_conn() as conn:
            # 总文档数
            cursor = conn.execute("SELECT COUNT(*) as count FROM document_routing")
            total = cursor.fetchone()["count"]

            # 按索引类型统计
            cursor = conn.execute("""
                SELECT index_type, COUNT(*) as count
                FROM document_routing
                GROUP BY index_type
            """)
            type_stats = {row["index_type"]: row["count"] for row in cursor.fetchall()}

            # 文件数
            cursor = conn.execute("SELECT COUNT(DISTINCT file_id) as count FROM document_routing")
            files = cursor.fetchone()["count"]

            return {
                "total": total,
                "hot": type_stats.get("hot", 0),
                "cold": type_stats.get("cold", 0),
                "files": files,
            }

    def get_old_documents(
        self,
        index_type: str,
        days: int
    ) -> List[str]:
        """
        获取指定天数前的文档ID

        Args:
            index_type: 索引类型 (hot/cold)
            days: 天数

        Returns:
            [doc_id, ...]
        """
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                SELECT doc_id FROM document_routing
                WHERE index_type = ?
                AND created_at < datetime('now', '-' || ? || ' days')
                """,
                (index_type, days)
            )
            return [row["doc_id"] for row in cursor.fetchall()]

    def migrate_to_cold(self, doc_ids: List[str]) -> int:
        """
        将文档从hot迁移到cold

        Args:
            doc_ids: 文档ID列表

        Returns:
            迁移的文档数
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.executemany(
                    """
                    UPDATE document_routing
                    SET index_type = 'cold', updated_at = CURRENT_TIMESTAMP
                    WHERE doc_id = ? AND index_type = 'hot'
                    """,
                    [(doc_id,) for doc_id in doc_ids]
                )
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to migrate documents to cold: {e}")
            return 0

    def close(self):
        """关闭数据库连接（如需要）"""
        pass
