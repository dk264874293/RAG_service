import logging
from typing import List

from src.models.document import Document
from src.vector.document_indexer import DocumentIndexer

logger = logging.getLogger(__name__)


class VectorService:
    def __init__(self, settings_obj, vector_store, embedding_service):
        self.settings = settings_obj
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.indexer = DocumentIndexer(settings_obj, vector_store, embedding_service)
        logger.info("VectorService initialized")

    async def vectorize_document(self, file_id: str, documents: List[Document]) -> bool:
        try:
            if not documents:
                logger.warning(
                    f"Empty documents for file_id={file_id}, skip vectorization"
                )
                return False

            logger.info(
                f"Start vectorizing document: file_id={file_id}, chunks={len(documents)}"
            )

            success = await self.indexer.index_document(file_id, documents)

            if success:
                logger.info(f"Document vectorization successful: file_id={file_id}")
            else:
                logger.warning(f"Document vectorization failed: file_id={file_id}")

            return success

        except Exception as e:
            logger.error(f"Vectorization failed for file_id={file_id}: {e}")
            return False

    async def delete_vectors(self, file_id: str) -> int:
        try:
            logger.info(f"Deleting vectors for file_id={file_id}")

            deleted_count = await self.vector_store.delete_documents(file_id)

            await self.vector_store.save_index()

            logger.info(f"Deleted {deleted_count} vectors for file_id={file_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete vectors for file_id={file_id}: {e}")
            return 0

    async def get_index_stats(self):
        return await self.indexer.get_index_stats()
