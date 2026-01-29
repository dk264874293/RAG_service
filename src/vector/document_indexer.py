"""
Document indexer service
Vectorizes and stores documents into FAISS
"""

import logging
from typing import List, Dict, Any

from langchain_core.documents import Document as LangchainDocument

from ..models.document import Document
from .embed_service import EmbeddingService
from .vector_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """Document indexing service"""

    def __init__(
        self,
        config_obj,
        vector_store: FAISSVectorStore,
        embedding_service: EmbeddingService,
    ):
        self.config = config_obj
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    async def index_document(self, file_id: str, documents: List[Document]) -> bool:
        """
        Index all chunks of a document

        Args:
            file_id: File ID
            documents: List of document chunks

        Returns:
            Success status
        """
        try:
            # Convert to Langchain Document format
            langchain_docs = []
            for doc in documents:
                lc_doc = LangchainDocument(
                    page_content=doc.page_content,
                    metadata={**doc.metadata, "file_id": file_id, "doc_id": doc.id_},
                )
                langchain_docs.append(lc_doc)

            # Add to vector store
            success = await self.vector_store.add_documents(langchain_docs)

            if success:
                # Save index
                await self.vector_store.save_index()
                logger.info(
                    f"Document indexed successfully: file_id={file_id}, chunks={len(documents)}"
                )

            return success

        except Exception as e:
            logger.error(f"Document indexing failed: file_id={file_id}, error={e}")
            return False

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return self.vector_store.get_stats()
