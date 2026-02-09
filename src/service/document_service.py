"""
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-29 11:39:32
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-02-02 18:24:55
FilePath: /RAG_service/src/service/document_service.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import aiofiles

from src.pipeline.document_processor import DocumentProcessingPipeline
from src.extractor.ocr_module.core.exceptions import OCRError

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        # 使用配置中的 processed_dir，如果没有配置则使用默认值
        processed_dir_config = getattr(settings_obj, "processed_dir", None)
        self.processed_dir = (
            Path(processed_dir_config)
            if processed_dir_config
            else Path("./data/processed")
        )

    async def process_document(
        self, file_path: str, file_id: str, file_name: str
    ) -> tuple[bool, str, List]:
        try:
            logger.info(f"开始处理文件: {file_name} (ID: {file_id})")
            logger.info(f"全局参数: {self.settings}")
            config = {
                "enable_pdf_ocr": self.settings.enable_pdf_ocr,
                "ocr_engine": self.settings.ocr_engine,
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
                "pdf_parse_mode": self.settings.pdf_parse_mode,
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
