"""
FAISS vector store manager
Handles FAISS index creation, loading, saving and querying
"""

import os
import logging
from typing import List, Tuple, Dict, Any, Optional, Set
import faiss
import pickle

from langchain_community.vectorstores import FAISS
from langchain_community.docstore import InMemoryDocstore
from langchain_core.documents import Document as LangchainDocument

logger = logging.getLogger(__name__)


class FAISSVectorStore:
    """FAISS vector store manager"""

    def __init__(self, config_obj, embedding_service):
        self.index_path = config_obj.faiss_index_path
        self.embedding_service = embedding_service
        self.vector_store = None
        self.deleted_ids_file = os.path.join(
            os.path.dirname(self.index_path), "deleted_ids.pkl"
        )
        self.deleted_ids: Set[str] = set()
        self._initialize()

    def _initialize(self):
        """Initialize or load FAISS index"""
        try:
            if os.path.exists(self.index_path):
                self._load_existing_index()
            else:
                self._create_new_index()
            self._load_deleted_ids()
        except Exception as e:
            logger.error(f"Failed to initialize FAISS store: {e}")
            self._create_new_index()

    def _load_existing_index(self):
        """Load existing FAISS index"""
        try:
            self.vector_store = FAISS.load_local(
                self.index_path,
                self.embedding_service.embedding_model,
                allow_dangerous_deserialization=True,
            )
            vector_count = self.vector_store.index.ntotal
            logger.info(f"Successfully loaded FAISS index: {vector_count} vectors")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}, will create new index")
            raise e

    def _create_new_index(self):
        """Create new empty FAISS index without dummy vectors"""
        try:
            sample_embedding = self.embedding_service.embedding_model.embed_query(
                "test"
            )
            dimension = len(sample_embedding)

            faiss_index = faiss.IndexFlatL2(dimension)

            self.vector_store = FAISS(
                embedding_function=self.embedding_service.embedding_model,
                index=faiss_index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

            self.vector_store.save_local(self.index_path)

            logger.info(f"Created new empty FAISS index with dimension {dimension}")
        except Exception as e:
            logger.error(f"Failed to create new FAISS index: {e}")
            raise e

    async def add_documents(self, documents: List[LangchainDocument]) -> bool:
        """
        Add documents to vector store

        Args:
            documents: List of Langchain documents

        Returns:
            Success status
        """
        try:
            self.vector_store.add_documents(documents)
            logger.info(
                f"Successfully added {len(documents)} documents to vector store"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return False

    async def save_index(self) -> bool:
        """Save FAISS index to disk"""
        try:
            self.vector_store.save_local(self.index_path)
            vector_count = self.vector_store.index.ntotal
            logger.info(
                f"Successfully saved FAISS index to {self.index_path}: {vector_count} vectors"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            total_vectors = self.vector_store.index.ntotal
            return {
                "total_vectors": total_vectors,
                "active_vectors": total_vectors - len(self.deleted_ids),
                "deleted_vectors": len(self.deleted_ids),
                "index_path": self.index_path,
                "dimension": self.embedding_service.get_dimension(),
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "total_vectors": 0,
                "active_vectors": 0,
                "deleted_vectors": len(self.deleted_ids),
                "index_path": self.index_path,
                "dimension": 0,
            }

    def _load_deleted_ids(self):
        """Load deleted document IDs from disk"""
        try:
            if os.path.exists(self.deleted_ids_file):
                with open(self.deleted_ids_file, "rb") as f:
                    self.deleted_ids = pickle.load(f)
                logger.info(f"Loaded {len(self.deleted_ids)} deleted IDs")
        except Exception as e:
            logger.error(f"Failed to load deleted IDs: {e}")
            self.deleted_ids = set()

    def _save_deleted_ids(self):
        """Save deleted document IDs to disk"""
        try:
            with open(self.deleted_ids_file, "wb") as f:
                pickle.dump(self.deleted_ids, f)
            logger.info(f"Saved {len(self.deleted_ids)} deleted IDs")
        except Exception as e:
            logger.error(f"Failed to save deleted IDs: {e}")

    async def delete_documents(self, file_id: str) -> int:
        """
        Delete all documents associated with a file ID

        Note: FAISS doesn't support direct deletion, so we use soft deletion
        by marking documents as deleted and filtering them out during search.

        Args:
            file_id: File ID to delete

        Returns:
            Number of documents marked as deleted
        """
        try:
            deleted_count = 0

            for doc_id in list(self.vector_store.index_to_docstore_id.keys()):
                try:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc and doc.metadata.get("file_id") == file_id:
                        self.deleted_ids.add(doc_id)
                        deleted_count += 1
                except Exception:
                    continue

            if deleted_count > 0:
                self._save_deleted_ids()
                logger.info(
                    f"Marked {deleted_count} documents as deleted for file_id={file_id}"
                )

            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return 0

    async def similarity_search(
        self, query: str, k: int = 5, filter_dict: Optional[Dict] = None
    ) -> List[LangchainDocument]:
        """
        Similarity search with deleted documents filtered out

        Args:
            query: Query text
            k: Number of results to return
            filter_dict: Metadata filter conditions

        Returns:
            List of relevant documents
        """
        try:
            search_k = k * 3
            if filter_dict:
                results = self.vector_store.similarity_search(
                    query, k=search_k, filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=search_k)

            filtered_results = [
                doc
                for doc in results
                if doc.metadata.get("doc_id") not in self.deleted_ids
            ][:k]

            logger.info(
                f"Similarity search: query='{query[:50]}...', returned {len(filtered_results)} results"
            )
            return filtered_results
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            return []

    async def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> List[Tuple[LangchainDocument, float]]:
        """
        Similarity search with scores, filtering deleted documents

        Args:
            query: Query text
            k: Number of results to return

        Returns:
            List of (document, score) tuples
        """
        try:
            search_k = k * 3
            all_results = self.vector_store.similarity_search_with_score(
                query, k=search_k
            )

            filtered_results = [
                (doc, score)
                for doc, score in all_results
                if doc.metadata.get("doc_id") not in self.deleted_ids
            ][:k]

            logger.info(
                f"Similarity search with scores: returned {len(filtered_results)} results"
            )
            return filtered_results
        except Exception as e:
            logger.error(f"Similarity search with scores failed: {e}")
            return []

    async def rebuild_index(self) -> bool:
        """
        Rebuild FAISS index by removing deleted documents

        This creates a new index excluding soft-deleted documents.
        Call this periodically when too many documents are deleted.

        Returns:
            Success status
        """
        try:
            all_docs = []
            for doc_id in self.vector_store.index_to_docstore_id.values():
                try:
                    doc = self.vector_store.docstore.search(doc_id)
                    if doc and doc.metadata.get("doc_id") not in self.deleted_ids:
                        all_docs.append(doc)
                except Exception:
                    continue

            self._create_new_index()

            if all_docs:
                self.vector_store.add_documents(all_docs)

            self.deleted_ids.clear()
            self._save_deleted_ids()
            self.vector_store.save_local(self.index_path)

            logger.info(f"Rebuilt index with {len(all_docs)} active documents")
            return True
        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")
            return False
