"""
BM25索引管理器
提供从向量存储构建、同步和管理BM25倒排索引的功能
"""

import os
import pickle
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

from rank_bm25 import BM25Okapi
import jieba

from src.models.document import Document

logger = logging.getLogger(__name__)


class BM25IndexManager:
    """
    BM25倒排索引管理器

    功能：
    1. 从向量存储的文档构建BM25索引
    2. 支持增量更新新文档
    3. 持久化索引到磁盘
    4. 自动分词（使用jieba）

    使用场景：
    - 关键词精确匹配
    - 专业术语检索
    - 与向量检索混合使用（Hybrid Strategy）
    """

    def __init__(
        self,
        index_path: str,
        vector_store,
        k1: float = 1.2,
        b: float = 0.75,
        auto_sync: bool = True
    ):
        """
        初始化BM25索引管理器

        Args:
            index_path: 索引保存路径
            vector_store: 向量存储实例（用于获取文档）
            k1: BM25 k1参数（控制词频饱和度）
            b: BM25 b参数（控制文档长度归一化）
            auto_sync: 是否自动同步向量存储的变化
        """
        self.index_path = index_path
        self.vector_store = vector_store
        self.k1 = k1
        self.b = b
        self.auto_sync = auto_sync

        # BM25索引
        self.bm25_index: Optional[BM25Okapi] = None

        # 元数据：doc_id → Document
        self.documents: Dict[str, Document] = {}

        # 语料库：按顺序存储的分词文档列表（用于BM25搜索）
        self.corpus: List[List[str]] = []
        self.doc_id_order: List[str] = []  # 保持doc_id的顺序

        # 同步状态
        self.last_sync_vector_count = 0
        self.last_sync_time: Optional[datetime] = None
        self.sync_file = os.path.join(index_path, "sync_state.pkl")

        # 确保目录存在
        os.makedirs(index_path, exist_ok=True)

        # 尝试加载已有索引
        self._load_or_create_index()

    def _load_or_create_index(self):
        """加载已有索引或创建新索引"""
        index_file = os.path.join(self.index_path, "bm25_index.pkl")

        if os.path.exists(index_file):
            try:
                with open(index_file, "rb") as f:
                    saved_data = pickle.load(f)
                    self.bm25_index = saved_data["index"]
                    self.documents = saved_data["documents"]
                    self.last_sync_vector_count = saved_data.get("vector_count", 0)
                    self.last_sync_time = saved_data.get("sync_time")

                logger.info(
                    f"Loaded BM25 index: {len(self.documents)} documents, "
                    f"last_sync={self.last_sync_time}"
                )
            except Exception as e:
                logger.error(f"Failed to load BM25 index: {e}, creating new one")
                self._create_empty_index()
        else:
            logger.info("BM25 index not found, creating new one")
            self._create_empty_index()

    def _create_empty_index(self):
        """创建空索引"""
        self.bm25_index = None
        self.documents = {}
        self.corpus = []
        self.doc_id_order = []
        self.last_sync_vector_count = 0
        self.last_sync_time = None

    async def build_from_vector_store(self) -> int:
        """
        从向量存储构建BM25索引

        Returns:
            构建的文档数量
        """
        try:
            logger.info("Building BM25 index from vector store...")

            # 从向量存储获取所有文档
            all_docs = []
            # 支持两种向量存储结构：直接FAISS和包装的FAISSVectorStore
            target_store = self.vector_store

            # 如果是FAISSVectorStore包装类，获取内部的LangChain FAISS
            if hasattr(target_store, 'vector_store'):
                target_store = target_store.vector_store

            # 检查是否有index_to_docstore_id属性
            if hasattr(target_store, 'index_to_docstore_id'):
                for doc_id in target_store.index_to_docstore_id.values():
                    try:
                        doc = target_store.docstore.search(doc_id)
                        if doc:
                            # 转换为Document格式（如果需要）
                            document = Document(
                                page_content=doc.page_content,
                                id_=doc_id,
                                metadata=doc.metadata
                            )
                            all_docs.append((doc_id, document))
                    except Exception as e:
                        logger.warning(f"Failed to extract document {doc_id}: {e}")
                        continue
            else:
                logger.warning("Vector store does not have index_to_docstore_id attribute")
                return 0

            if not all_docs:
                logger.warning("No documents found in vector store")
                return 0

            # 分词并构建语料库
            corpus = []
            doc_id_order = []
            for doc_id, document in all_docs:
                # 使用jieba分词
                tokens = list(jieba.cut(document.page_content))
                corpus.append(tokens)
                doc_id_order.append(doc_id)
                self.documents[doc_id] = document

            # 创建BM25索引
            self.bm25_index = BM25Okapi(corpus, k1=self.k1, b=self.b, epsilon=0.25)

            # 保存语料库和顺序
            self.corpus = corpus
            self.doc_id_order = doc_id_order

            # 更新同步状态
            self.last_sync_vector_count = len(all_docs)
            self.last_sync_time = datetime.now()

            # 保存索引
            self._save()

            logger.info(
                f"BM25 index built successfully: {len(all_docs)} documents, "
                f"k1={self.k1}, b={self.b}"
            )

            return len(all_docs)

        except Exception as e:
            logger.error(f"Failed to build BM25 index: {e}")
            return 0

    async def sync_incremental(self) -> int:
        """
        增量同步：添加新文档到索引

        Returns:
            新增的文档数量
        """
        try:
            # 检查向量存储是否有新文档
            # 支持两种向量存储结构
            target_store = self.vector_store
            if hasattr(target_store, 'vector_store'):
                target_store = target_store.vector_store

            # 获取当前向量数量
            if hasattr(target_store, 'index'):
                current_vector_count = target_store.index.ntotal
            else:
                return 0

            if current_vector_count <= self.last_sync_vector_count:
                return 0  # 没有新文档

            # 获取新文档
            new_docs = []
            if hasattr(target_store, 'index_to_docstore_id'):
                for doc_id, faiss_id in target_store.index_to_docstore_id.items():
                    if doc_id not in self.documents:
                        try:
                            doc = target_store.docstore.search(doc_id)
                            if doc:
                                document = Document(
                                    page_content=doc.page_content,
                                    id_=doc_id,
                                    metadata=doc.metadata
                                )
                                new_docs.append((doc_id, document))
                        except Exception as e:
                            logger.warning(f"Failed to extract document {doc_id}: {e}")

            if not new_docs:
                return 0

            # 如果索引为空，完整重建
            if self.bm25_index is None:
                return await self.build_from_vector_store()

            # 增量添加新文档
            for doc_id, document in new_docs:
                tokens = list(jieba.cut(document.page_content))
                # 对于rank-bm25，需要重建索引（因为不支持增量添加）
                # 所以这里我们重建整个索引
                self.corpus.append(tokens)
                self.doc_id_order.append(doc_id)
                self.documents[doc_id] = document

            # 重建BM25索引
            self.bm25_index = BM25Okapi(self.corpus, k1=self.k1, b=self.b, epsilon=0.25)

            # 更新同步状态
            self.last_sync_vector_count = current_vector_count
            self.last_sync_time = datetime.now()

            # 保存
            self._save()

            logger.info(f"BM25 index synced: {len(new_docs)} new documents added")

            return len(new_docs)

        except Exception as e:
            logger.error(f"Failed to sync BM25 index: {e}")
            return 0

    async def search(self, query: str, k: int = 10) -> List[tuple[Document, float]]:
        """
        BM25搜索

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            [(Document, BM25分数), ...]
        """
        if self.bm25_index is None:
            logger.warning("BM25 index is empty, returning no results")
            return []

        try:
            # 分词
            tokenized_query = list(jieba.cut(query))

            # 搜索 - BM25Okapi.get_top_n返回按相关性排序的文档内容列表
            raw_results = self.bm25_index.get_top_n(tokenized_query, self.corpus, n=k)

            # 转换为Document对象（按返回顺序已经是按相关性排序的）
            results = []
            seen_doc_ids = set()  # 去重

            for doc_content in raw_results:
                # 通过内容查找doc_id
                for doc_id in self.doc_id_order:
                    if doc_id in seen_doc_ids:
                        continue
                    document = self.documents.get(doc_id)
                    if document and document.page_content == doc_content:
                        # BM25的get_top_n不返回分数，我们用排名作为分数的代理
                        # 排名越高（索引越小），分数越高
                        rank_score = 1.0 / (len(results) + 1)  # 简单的排名分数
                        results.append((document, rank_score))
                        seen_doc_ids.add(doc_id)
                        break

                if len(results) >= k:
                    break

            logger.debug(f"BM25 search: query='{query[:30]}...', returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_documents": len(self.documents),
            "last_sync_vector_count": self.last_sync_vector_count,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "k1": self.k1,
            "b": self.b,
            "index_path": self.index_path,
        }

    def _save(self):
        """保存索引到磁盘"""
        try:
            index_file = os.path.join(self.index_path, "bm25_index.pkl")

            if self.bm25_index is not None:
                save_data = {
                    "index": self.bm25_index,
                    "documents": self.documents,
                    "vector_count": self.last_sync_vector_count,
                    "sync_time": self.last_sync_time,
                    "created_at": datetime.now().isoformat(),
                }

                with open(index_file, "wb") as f:
                    pickle.dump(save_data, f)

                logger.debug(f"BM25 index saved: {len(self.documents)} documents")
            else:
                logger.debug("BM25 index is None, skipping save")

        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")

    async def warmup(self) -> None:
        """预热：执行测试搜索"""
        try:
            await self.search("test query", k=1)
            logger.info("BM25IndexManager warmup completed")
        except Exception as e:
            logger.warning(f"BM25IndexManager warmup failed: {e}")

    async def cleanup(self) -> None:
        """清理资源"""
        self.bm25_index = None
        self.documents = {}
        logger.info("BM25IndexManager cleanup completed")
