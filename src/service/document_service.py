import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import aiofiles

from config import settings
from src.pipeline.document_processor import DocumentProcessingPipeline
from src.extractor.ocr_module.core.exceptions import OCRError

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.processed_dir = Path("./data/processed")

    async def process_document(
        self, file_path: str, file_id: str, file_name: str
    ) -> tuple[bool, str, List]:
        try:
            config = {
                "enable_pdf_ocr": self.settings.enable_pdf_ocr,
                "ocr_engine": self.settings.ocr_engine,
                "ocr_version": self.settings.ocr_engine,
                "ocr_confidence_threshold": self.settings.ocr_confidence_threshold,
                "ocr_module_confidence_threshold": self.settings.ocr_module_confidence_threshold,
                "ocr_api_endpoint": self.settings.ocr_api_endpoint,
                "ocr_api_key": self.settings.ocr_api_key,
                "ocr_output_dir": self.settings.ocr_output_dir,
                "ocr_error_continue": self.settings.ocr_error_continue,
                "enable_chunking": self.settings.enable_chunking,
                "chunk_size": self.settings.chunk_size,
                "chunk_overlap": self.settings.chunk_overlap,
                "chunking_strategy": self.settings.chunking_strategy,
            }

            pipeline = DocumentProcessingPipeline(config)
            documents = await pipeline.process_document(file_path)

            content_preview = ""
            if documents and documents[0].page_content:
                content_preview = documents[0].page_content[:500]

                if len(documents[0].page_content) > 500:
                    content_preview += "..."

            self.processed_dir.mkdir(parents=True, exist_ok=True)
            result_file = self.processed_dir / f"{file_id}.json"

            result_data = {
                "file_id": file_id,
                "file_name": file_name,
                "processed_at": datetime.now().isoformat(),
                "documents": [
                    {"page_content": doc.page_content, "metadata": doc.metadata}
                    for doc in documents
                ],
            }

            async with aiofiles.open(result_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(result_data, ensure_ascii=False, indent=2))

            # Vectorize and index documents
            try:
                from src.api.dependencies import (
                    get_embedding_service,
                    get_vector_store,
                )
                from src.vector.document_indexer import DocumentIndexer

                embedding_service = get_embedding_service()
                vector_store = get_vector_store()
                indexer = DocumentIndexer(
                    self.settings, vector_store, embedding_service
                )

                await indexer.index_document(file_id, documents)
                logger.info(f"Document vectorization successful: file_id={file_id}")

            except Exception as e:
                logger.error(
                    f"Document vectorization failed: file_id={file_id}, error={e}"
                )
                # Vectorization failure doesn't block main flow

            return True, "处理成功", documents

        except OCRError as e:
            logger.error(f"OCR处理失败: {e}")
            return False, f"OCR处理失败: {e}", []
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            return False, f"处理失败: {e}", []

    def get_content_preview(self, content: str) -> str:
        if not content:
            return ""

        preview = content[:500]
        if len(content) > 500:
            preview += "..."

        return preview

    async def delete_document(self, file_id: str) -> int:
        """
        Delete document vectors from FAISS index

        Args:
            file_id: File ID to delete

        Returns:
            Number of documents deleted
        """
        try:
            from src.api.dependencies import get_vector_store

            vector_store = get_vector_store()
            deleted_count = await vector_store.delete_documents(file_id)

            await vector_store.save_index()

            logger.info(
                f"Deleted {deleted_count} document vectors for file_id={file_id}"
            )
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete document vectors: {e}")
            return 0
