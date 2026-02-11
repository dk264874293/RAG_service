"""
Cold FAISS Index: 归档索引，只读优化
使用HNSW索引，高召回率，支持软删除
"""

import os
import logging
import pickle
from typing import List, Optional, Set, Dict, Any

import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore import InMemoryDocstore
from langchain_core.documents import Document as LangchainDocument

logger = logging.getLogger(__name__)


class ColdFAISSIndex:
    """
    归档索引：只读优化，使用HNSW高召回率

    特点：
    1. 使用HNSW索引，高召回率
    2. 软删除机制（避免频繁重建）
    3. 只读优化，不频繁修改
    4. 支持批量重建
    """

    def __init__(
        self,
        index_path: str,
        embedding_service,
        index_type: str = "HNSW",
        M: int = 32,
        efSearch: int = 64
    ):
        self.index_path = index_path
        self.embedding = embedding_service
        self.index_type = index_type
        self.M = M
        self.efSearch = efSearch

        # 内部组件
        self.vector_store: Optional[FAISS] = None

        # 软删除管理
        self.soft_deleted_ids: Set[str] = set()
        self.deleted_ids_file = os.path.join(
            os.path.dirname(index_path), "cold_deleted_ids.pkl"
        )

        # 统计
        self.total_added = 0

        self._initialize()

    def _initialize(self):
        """初始化索引"""
        os.makedirs(self.index_path, exist_ok=True)

        if self._index_exists():
            self._load()
        else:
            self._create_new()

        self._load_deleted_ids()

        logger.info(
            f"Cold FAISS Index initialized: type={self.index_type}, "
            f"path={self.index_path}, size={self.get_size()}, "
            f"deleted={len(self.soft_deleted_ids)}"
        )

    def _index_exists(self) -> bool:
        """检查索引文件是否存在"""
        return os.path.exists(os.path.join(self.index_path, "index.faiss"))

    def _create_new(self):
        """创建新索引"""
        try:
            dimension = self.embedding.get_dimension()

            if self.index_type == "HNSW":
                # HNSW: 分层导航小世界图，高召回率
                index = faiss.IndexHNSWFlat(dimension, self.M)
                # 使用正确的方式设置 HNSW 参数
                try:
                    index.hnsw.efSearch = self.efSearch
                except AttributeError:
                    # 某些版本的 FAISS 可能使用不同的属性名
                    pass
                try:
                    index.hnsw.efConstruction = 128  # 构建时参数，影响质量
                except AttributeError:
                    pass

            elif self.index_type == "Flat":
                # Flat: 精确搜索
                index = faiss.IndexFlatL2(dimension)

            else:
                # Fallback
                index = faiss.IndexFlatL2(dimension)

            # 创建Langchain FAISS包装器
            self.vector_store = FAISS(
                embedding_function=self.embedding.embedding_model,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            self._save()

            logger.info(f"Created new cold index: type={self.index_type}, dim={dimension}")

        except Exception as e:
            logger.error(f"Failed to create new index: {e}")
            raise

    def _load(self):
        """加载已有索引"""
        try:
            # 加载FAISS索引
            index = faiss.read_index(os.path.join(self.index_path, "index.faiss"))

            # 加载Langchain组件
            self.vector_store = FAISS(
                embedding_function=self.embedding.embedding_model,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            # 加载docstore和映射
            self.vector_store.docstore = self._load_docstore()
            self.vector_store.index_to_docstore_id = self._load_index_mapping()

            logger.info(f"Loaded cold index: {self.get_size()} vectors")

        except Exception as e:
            logger.error(f"Failed to load index: {e}, creating new one")
            self._create_new()

    def _save(self):
        """保存索引"""
        try:
            # 保存FAISS索引
            faiss.write_index(
                self.vector_store.index,
                os.path.join(self.index_path, "index.faiss")
            )

            # 保存docstore
            self._save_docstore()

            # 保存映射
            self._save_index_mapping()

            logger.debug(f"Saved cold index: {self.get_size()} vectors")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def _load_docstore(self) -> InMemoryDocstore:
        """加载docstore"""
        docstore_path = os.path.join(self.index_path, "docstore.pkl")
        if os.path.exists(docstore_path):
            with open(docstore_path, "rb") as f:
                return pickle.load(f)
        return InMemoryDocstore()

    def _save_docstore(self):
        """保存docstore"""
        docstore_path = os.path.join(self.index_path, "docstore.pkl")
        with open(docstore_path, "wb") as f:
            pickle.dump(self.vector_store.docstore, f)

    def _load_index_mapping(self) -> Dict[int, str]:
        """加载索引映射"""
        mapping_path = os.path.join(self.index_path, "index_mapping.pkl")
        if os.path.exists(mapping_path):
            with open(mapping_path, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_index_mapping(self):
        """保存索引映射"""
        mapping_path = os.path.join(self.index_path, "index_mapping.pkl")
        with open(mapping_path, "wb") as f:
            pickle.dump(self.vector_store.index_to_docstore_id, f)

    def _load_deleted_ids(self):
        """加载软删除ID集合"""
        try:
            if os.path.exists(self.deleted_ids_file):
                with open(self.deleted_ids_file, "rb") as f:
                    self.soft_deleted_ids = pickle.load(f)
                logger.info(f"Loaded {len(self.soft_deleted_ids)} deleted IDs")
        except Exception as e:
            logger.error(f"Failed to load deleted IDs: {e}")
            self.soft_deleted_ids = set()

    def _save_deleted_ids(self):
        """保存软删除ID集合"""
        try:
            with open(self.deleted_ids_file, "wb") as f:
                pickle.dump(self.soft_deleted_ids, f)
        except Exception as e:
            logger.error(f"Failed to save deleted IDs: {e}")

    async def add_documents(
        self,
        docs: List[LangchainDocument],
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档（通常从Hot Index迁移过来）

        Args:
            docs: 文档列表
            doc_ids: 文档ID列表

        Returns:
            文档ID列表
        """
        if not docs:
            return []

        # 生成文档ID
        if doc_ids is None:
            import uuid
            doc_ids = [f"cold_{uuid.uuid4().hex}" for _ in docs]

        # 添加metadata
        from datetime import datetime
        for doc, doc_id in zip(docs, doc_ids):
            doc.metadata["doc_id"] = doc_id
            doc.metadata["index_type"] = "cold"
            doc.metadata["archived_at"] = datetime.now().isoformat()

        # 添加到索引
        self.vector_store.add_documents(docs)
        self.total_added += len(docs)

        # 保存
        self._save()

        logger.info(f"Added {len(docs)} documents to cold index")
        return doc_ids

    async def soft_delete(self, doc_id: str) -> int:
        """
        软删除文档

        Args:
            doc_id: 文档ID

        Returns:
            删除的文档数（0或1）
        """
        if doc_id in self.soft_deleted_ids:
            return 0

        self.soft_deleted_ids.add(doc_id)
        self._save_deleted_ids()
        return 1

    async def batch_soft_delete(self, doc_ids: List[str]) -> int:
        """批量软删除"""
        count = 0
        for doc_id in doc_ids:
            if doc_id not in self.soft_deleted_ids:
                self.soft_deleted_ids.add(doc_id)
                count += 1
        self._save_deleted_ids()
        return count

    async def search(
        self,
        query: str,
        k: int = 10,
        filter_dict: Optional[Dict] = None
    ) -> List[LangchainDocument]:
        """
        搜索，自动过滤软删除

        Args:
            query: 查询文本
            k: 返回结果数
            filter_dict: 元数据过滤

        Returns:
            文档列表
        """
        try:
            # 动态计算召回倍数
            deletion_rate = self.get_deletion_rate()
            if deletion_rate > 0.3:
                search_k = k * 3
            elif deletion_rate > 0.1:
                search_k = k * 2
            else:
                search_k = int(k * 1.5)

            # 搜索
            if filter_dict:
                results = self.vector_store.similarity_search(
                    query, k=search_k, filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=search_k)

            # 过滤软删除
            filtered = [
                doc for doc in results
                if doc.metadata.get("doc_id") not in self.soft_deleted_ids
            ][:k]

            return filtered

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def search_with_score(
        self,
        query: str,
        k: int = 10
    ) -> List[tuple[LangchainDocument, float]]:
        """搜索并返回分数"""
        try:
            deletion_rate = self.get_deletion_rate()
            search_k = int(k * (1 + deletion_rate * 2))

            all_results = self.vector_store.similarity_search_with_score(
                query, k=search_k
            )

            # 过滤软删除
            filtered = [
                (doc, score)
                for doc, score in all_results
                if doc.metadata.get("doc_id") not in self.soft_deleted_ids
            ][:k]

            return filtered

        except Exception as e:
            logger.error(f"Search with score failed: {e}")
            return []

    def get_deletion_rate(self) -> float:
        """获取删除率"""
        total = self.get_size()
        if total == 0:
            return 0.0
        return len(self.soft_deleted_ids) / total

    def get_size(self) -> int:
        """获取索引大小"""
        if self.vector_store and self.vector_store.index:
            return self.vector_store.index.ntotal
        return 0

    async def rebuild(self) -> bool:
        """
        重建索引，移除软删除的文档

        Returns:
            是否成功
        """
        try:
            logger.info("Rebuilding cold index...")

            # 收集活跃文档
            active_docs = []
            active_ids = []

            for doc_id in self.vector_store.index_to_docstore_id.values():
                if doc_id not in self.soft_deleted_ids:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc:
                        active_docs.append(doc)
                        active_ids.append(doc_id)

            logger.info(
                f"Rebuilding: {len(active_docs)} active docs, "
                f"{len(self.soft_deleted_ids)} deleted docs"
            )

            # 重建索引
            self._create_new()

            # 重新添加活跃文档
            if active_docs:
                await self.add_documents(active_docs, active_ids)

            # 清空软删除集合
            self.soft_deleted_ids.clear()
            self._save_deleted_ids()

            logger.info(f"Cold index rebuilt successfully: {self.get_size()} docs")
            return True

        except Exception as e:
            logger.error(f"Failed to rebuild cold index: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        deletion_rate = self.get_deletion_rate()

        # 判断是否需要重建
        needs_rebuild = deletion_rate > 0.3 or len(self.soft_deleted_ids) > 10000

        return {
            "index_type": "cold",
            "faiss_type": self.index_type,
            "size": self.get_size(),
            "deleted_count": len(self.soft_deleted_ids),
            "deletion_rate": f"{deletion_rate:.2%}",
            "needs_rebuild": needs_rebuild,
            "total_added": self.total_added,
        }

    def should_rebuild(self) -> tuple[bool, str]:
        """判断是否需要重建"""
        deletion_rate = self.get_deletion_rate()

        if deletion_rate > 0.3:
            return True, f"Deletion rate {deletion_rate:.2%} exceeds 30%"

        if len(self.soft_deleted_ids) > 10000:
            return True, f"Too many deleted documents: {len(self.soft_deleted_ids)}"

        return False, ""

    async def clear(self):
        """清空索引"""
        self.soft_deleted_ids.clear()
        self._save_deleted_ids()
        self._create_new()
        logger.info("Cleared cold index")
