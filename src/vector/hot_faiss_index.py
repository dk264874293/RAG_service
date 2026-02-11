"""
Hot FAISS Index: 活跃索引，支持物理删除
使用IDRemover实现高效的物理删除
"""

import os
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

import faiss
from langchain_community.vectorstores import FAISS
from langchain_community.docstore import InMemoryDocstore
from langchain_core.documents import Document as LangchainDocument

logger = logging.getLogger(__name__)


class HotFAISSIndex:
    """
    活跃索引：支持物理删除的FAISS索引

    特点：
    1. 使用IDRemover支持物理删除
    2. 使用IVF-PQ索引，平衡速度和准确性
    3. 自动管理容量，触发归档
    4. 增量保存，无需全量重建
    """

    def __init__(
        self,
        index_path: str,
        embedding_service,
        max_size: int = 1000000,
        index_type: str = "IVFPQ",
        nlist: int = 100,
        nprobe: int = 10,
        m: int = 64,
        nbits: int = 8
    ):
        self.index_path = index_path
        self.embedding = embedding_service
        self.max_size = max_size
        self.index_type = index_type

        # IVF-PQ 参数
        self.nlist = nlist
        self.nprobe = nprobe
        self.m = m
        self.nbits = nbits

        # 内部组件
        self.vector_store: Optional[FAISS] = None
        self.id_remover: Optional[faiss.IDRemover] = None
        self.is_trained = False

        # 统计
        self.total_added = 0
        self.total_removed = 0

        self._initialize()

    def _initialize(self):
        """初始化索引"""
        os.makedirs(self.index_path, exist_ok=True)

        if self._index_exists():
            self._load()
        else:
            self._create_new()

        logger.info(
            f"Hot FAISS Index initialized: type={self.index_type}, "
            f"path={self.index_path}, size={self.get_size()}"
        )

    def _index_exists(self) -> bool:
        """检查索引文件是否存在"""
        return os.path.exists(os.path.join(self.index_path, "index.faiss"))

    def _create_new(self):
        """创建新索引"""
        try:
            dimension = self.embedding.get_dimension()

            if self.index_type == "IVFPQ":
                # IVF-PQ: 倒排文件 + 乘积量化
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFPQ(
                    quantizer, dimension, self.nlist, self.m, self.nbits
                )
                index.nprobe = self.nprobe
                # 需要训练后才能使用
                self.is_trained = False

            elif self.index_type == "IVF":
                # IVF: 倒排文件
                quantizer = faiss.IndexFlatL2(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, self.nlist)
                index.nprobe = self.nprobe
                self.is_trained = False

            elif self.index_type == "HNSW":
                # HNSW: 分层导航小世界图
                index = faiss.IndexHNSWFlat(dimension, 32)
                index.efSearch = 64
                self.is_trained = True  # HNSW不需要训练

            else:
                # Fallback to Flat
                index = faiss.IndexFlatL2(dimension)
                self.is_trained = True

            # 尝试使用IDRemover（如果可用）
            if hasattr(faiss, 'IDRemover'):
                self.id_remover = faiss.IDRemover(index)
                logger.info("Using faiss.IDRemover for physical deletion")
                wrapper_index = self.id_remover
            else:
                # 如果IDRemover不可用，直接使用索引
                self.id_remover = None
                wrapper_index = index
                logger.warning("faiss.IDRemover not available, using soft deletion fallback")

            # 创建Langchain FAISS包装器
            self.vector_store = FAISS(
                embedding_function=self.embedding.embedding_model,
                index=wrapper_index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            self._save()

            logger.info(f"Created new hot index: type={self.index_type}, dim={dimension}")

        except Exception as e:
            logger.error(f"Failed to create new index: {e}")
            raise

    def _load(self):
        """加载已有索引"""
        try:
            # 加载FAISS索引
            index = faiss.read_index(os.path.join(self.index_path, "index.faiss"))

            # 尝试包装IDRemover
            if hasattr(faiss, 'IDRemover'):
                self.id_remover = faiss.IDRemover(index)
                wrapper_index = self.id_remover
            else:
                self.id_remover = None
                wrapper_index = index

            # 加载Langchain组件
            self.vector_store = FAISS(
                embedding_function=self.embedding.embedding_model,
                index=wrapper_index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            # 加载docstore和映射
            self.vector_store.docstore = self._load_docstore()
            self.vector_store.index_to_docstore_id = self._load_index_mapping()

            self.is_trained = True

            logger.info(f"Loaded hot index: {self.get_size()} vectors")

        except Exception as e:
            logger.error(f"Failed to load index: {e}, creating new one")
            self._create_new()

    def _save(self):
        """保存索引"""
        try:
            # 保存FAISS索引（处理 id_remover 为 None 的情况）
            if self.id_remover is not None:
                faiss.write_index(self.id_remover.index, os.path.join(self.index_path, "index.faiss"))
            elif self.vector_store is not None and self.vector_store.index is not None:
                faiss.write_index(self.vector_store.index, os.path.join(self.index_path, "index.faiss"))
            else:
                logger.warning("No index to save")
                return

            # 保存docstore
            if self.vector_store is not None:
                self._save_docstore()
                # 保存映射
                self._save_index_mapping()

            logger.debug(f"Saved hot index: {self.get_size()} vectors")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def _load_docstore(self) -> InMemoryDocstore:
        """加载docstore"""
        import pickle
        docstore_path = os.path.join(self.index_path, "docstore.pkl")
        if os.path.exists(docstore_path):
            with open(docstore_path, "rb") as f:
                return pickle.load(f)
        return InMemoryDocstore()

    def _save_docstore(self):
        """保存docstore"""
        import pickle
        docstore_path = os.path.join(self.index_path, "docstore.pkl")
        with open(docstore_path, "wb") as f:
            pickle.dump(self.vector_store.docstore, f)

    def _load_index_mapping(self) -> Dict[int, str]:
        """加载索引映射"""
        import pickle
        mapping_path = os.path.join(self.index_path, "index_mapping.pkl")
        if os.path.exists(mapping_path):
            with open(mapping_path, "rb") as f:
                return pickle.load(f)
        return {}

    def _save_index_mapping(self):
        """保存索引映射"""
        import pickle
        mapping_path = os.path.join(self.index_path, "index_mapping.pkl")
        with open(mapping_path, "wb") as f:
            pickle.dump(self.vector_store.index_to_docstore_id, f)

    async def add_documents(
        self,
        docs: List[LangchainDocument],
        doc_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        添加文档

        Args:
            docs: 文档列表
            doc_ids: 文档ID列表（可选，自动生成）

        Returns:
            文档ID列表
        """
        if not docs:
            return []

        # 检查容量
        current_size = self.get_size()
        if current_size + len(docs) > self.max_size:
            logger.warning(
                f"Hot index near capacity: {current_size + len(docs)}/{self.max_size}. "
                f"Consider archiving old documents."
            )

        # 生成文档ID
        if doc_ids is None:
            doc_ids = [f"hot_{uuid.uuid4().hex}" for _ in docs]

        # 添加metadata
        for doc, doc_id in zip(docs, doc_ids):
            doc.metadata["doc_id"] = doc_id
            doc.metadata["index_type"] = "hot"
            doc.metadata["created_at"] = datetime.now().isoformat()

        # 训练索引（如果需要）
        if not self.is_trained and self.index_type in ["IVF", "IVFPQ"]:
            await self._train_index(docs)

        # 添加到索引
        self.vector_store.add_documents(docs)
        self.total_added += len(docs)

        # 增量保存
        self._save()

        logger.info(f"Added {len(docs)} documents to hot index")
        return doc_ids

    async def _train_index(self, docs: List[LangchainDocument]):
        """训练索引（IVF/IVFPQ需要）"""
        try:
            logger.info(f"Training index with {len(docs)} documents...")

            # 生成embedding
            texts = [doc.page_content for doc in docs]
            embeddings = self.embedding.embedding_model.embed_documents(texts)

            # 训练
            self.id_remover.index.train(embeddings)
            self.is_trained = True

            logger.info("Index training completed")

        except Exception as e:
            logger.error(f"Failed to train index: {e}")
            # Fallback to Flat
            self.index_type = "Flat"
            self._create_new()

    async def remove_doc(self, doc_id: str) -> int:
        """
        物理删除文档

        Args:
            doc_id: 文档ID

        Returns:
            删除的文档数（0或1）
        """
        try:
            # 如果有IDRemover，使用物理删除
            if self.id_remover is not None:
                # 获取FAISS内部ID
                faiss_id = self._get_faiss_id(doc_id)
                if faiss_id is None:
                    logger.warning(f"Document not found: {doc_id}")
                    return 0

                # 使用IDRemover物理删除
                self.id_remover.remove_ids(faiss_id)

                # 从docstore删除
                if doc_id in self.vector_store.docstore._dict:
                    del self.vector_store.docstore._dict[doc_id]

                # 从映射中删除
                if faiss_id in self.vector_store.index_to_docstore_id:
                    del self.vector_store.index_to_docstore_id[faiss_id]

                self.total_removed += 1

                # 保存
                self._save()

                logger.info(f"Removed doc_id={doc_id} from hot index (physical)")
                return 1
            else:
                # 没有IDRemover，使用软删除
                # 添加到软删除集合
                if not hasattr(self, '_soft_deleted_ids'):
                    self._soft_deleted_ids = set()

                self._soft_deleted_ids.add(doc_id)

                # 从docstore删除（保持索引不变）
                if doc_id in self.vector_store.docstore._dict:
                    del self.vector_store.docstore._dict[doc_id]

                self.total_removed += 1

                # 保存软删除集合
                self._save_soft_deleted_ids()

                logger.info(f"Removed doc_id={doc_id} from hot index (soft deletion)")
                return 1

        except Exception as e:
            logger.error(f"Failed to remove doc_id={doc_id}: {e}")
            return 0

    def _save_soft_deleted_ids(self):
        """保存软删除ID集合"""
        import pickle
        try:
            deleted_path = os.path.join(self.index_path, "soft_deleted_ids.pkl")
            with open(deleted_path, "wb") as f:
                pickle.dump(getattr(self, '_soft_deleted_ids', set()), f)
        except Exception as e:
            logger.error(f"Failed to save soft deleted IDs: {e}")

    async def search(
        self,
        query: str,
        k: int = 10,
        filter_dict: Optional[Dict] = None
    ) -> List[LangchainDocument]:
        """
        搜索

        Args:
            query: 查询文本
            k: 返回结果数
            filter_dict: 元数据过滤

        Returns:
            文档列表
        """
        try:
            # 如果使用软删除，需要召回更多结果
            soft_deleted = getattr(self, '_soft_deleted_ids', set())
            search_k = k * 2 if soft_deleted else k

            if filter_dict:
                results = self.vector_store.similarity_search(
                    query, k=search_k, filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=search_k)

            # 过滤软删除的文档
            if soft_deleted:
                results = [doc for doc in results if doc.metadata.get("doc_id") not in soft_deleted][:k]

            return results

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
            results = self.vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            logger.error(f"Search with score failed: {e}")
            return []

    def _get_faiss_id(self, doc_id: str) -> Optional[int]:
        """获取FAISS内部ID"""
        for faiss_id, stored_id in self.vector_store.index_to_docstore_id.items():
            if stored_id == doc_id:
                return faiss_id
        return None

    def get_size(self) -> int:
        """获取索引大小"""
        if self.id_remover:
            return self.id_remover.index.ntotal
        return 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "index_type": "hot",
            "faiss_type": self.index_type,
            "size": self.get_size(),
            "max_size": self.max_size,
            "utilization": f"{self.get_size() / self.max_size:.1%}",
            "total_added": self.total_added,
            "total_removed": self.total_removed,
            "is_trained": self.is_trained,
        }

    async def clear(self):
        """清空索引"""
        self._create_new()
        logger.info("Cleared hot index")
