"""
PDF提取技能
负责从PDF文件中提取文本内容和元数据，支持扫描版PDF的OCR识别
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from src.models.document import Document
from src.extractor.pdf_extractor import PdfExtractor

logger = logging.getLogger(__name__)


class PDFExtractionSkill:
    """
    PDF提取技能
    使用增强版PDF提取器支持文本提取和OCR识别
    """

    def __init__(
        self,
        enable_ocr: bool = False,
        ocr_engine: str = "paddle",
        ocr_confidence_threshold: float = 0.5,
    ):
        """
        初始化PDF提取技能

        Args:
            enable_ocr: 是否启用OCR
            ocr_engine: OCR引擎（paddle, tesseract）
            ocr_confidence_threshold: OCR置信度阈值
        """
        self.enable_ocr = enable_ocr
        self.ocr_engine = ocr_engine
        self.ocr_confidence_threshold = ocr_confidence_threshold

        self.ocr_stats = {
            "total_pages": 0,
            "ocr_pages": 0,
            "extracted_images": 0,
        }

    def extract(
        self,
        file_path: str,
        tenant_id: str = "default",
        user_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        从PDF文件中提取内容

        Args:
            file_path: PDF文件路径
            tenant_id: 租户ID
            user_id: 用户ID
            metadata: 额外元数据

        Returns:
            文档对象列表

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"PDF文件不存在: {file_path}")

        # 配置提取器
        config = {
            "enable_ocr": self.enable_ocr,
            "ocr_engine": self.ocr_engine,
            "ocr_confidence_threshold": self.ocr_confidence_threshold,
        }

        # 创建PDF提取器
        extractor = PdfExtractor(
            file_path=file_path,
            tenant_id=tenant_id,
            user_id=user_id,
            config=config,
            enable_ocr=self.enable_ocr,
        )

        # 提取文档
        documents = extractor.extract()

        # 收集OCR统计信息
        if self.enable_ocr and hasattr(extractor, "get_ocr_stats"):
            self.ocr_stats = extractor.get_ocr_stats()
            logger.info(f"PDF处理完成，OCR统计: {self.ocr_stats}")

        # 增强元数据
        if metadata:
            for doc in documents:
                doc.metadata.update(metadata)

        logger.info(f"PDF提取完成: {len(documents)} 个文档块")
        return documents

    def get_ocr_stats(self) -> Dict[str, int]:
        """
        获取OCR统计信息

        Returns:
            OCR统计字典
        """
        return self.ocr_stats

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        从PDF文件中提取元数据

        Args:
            file_path: PDF文件路径

        Returns:
            元数据字典
        """
        path_obj = Path(file_path)
        return {
            "source": str(file_path),
            "filename": path_obj.name,
            "file_type": ".pdf",
            "file_size": path_obj.stat().st_size if path_obj.exists() else 0,
            "tenant_id": "default",
            "user_id": "default",
        }


class PDFBatchExtractionSkill:
    """
    PDF批量提取技能
    支持批量处理多个PDF文件
    """

    def __init__(self, extraction_skill: PDFExtractionSkill):
        """
        初始化批量提取技能

        Args:
            extraction_skill: PDF提取技能实例
        """
        self.extraction_skill = extraction_skill

    async def extract_batch(
        self,
        file_paths: List[str],
        tenant_id: str = "default",
        user_id: str = "default",
    ) -> Dict[str, List[Document]]:
        """
        批量提取PDF文件

        Args:
            file_paths: PDF文件路径列表
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            文件路径到文档列表的映射字典
        """
        import asyncio
        from functools import partial

        results = {}

        async def extract_single(file_path: str) -> tuple[str, List[Document]]:
            try:
                documents = await asyncio.to_thread(
                    self.extraction_skill.extract,
                    file_path=file_path,
                    tenant_id=tenant_id,
                    user_id=user_id,
                )
                return file_path, documents
            except Exception as e:
                logger.error(f"PDF提取失败: {file_path}, error={e}")
                return file_path, []

        # 并行提取
        tasks = [extract_single(fp) for fp in file_paths]
        completed_tasks = await asyncio.gather(*tasks)

        # 收集结果
        for file_path, documents in completed_tasks:
            results[file_path] = documents

        logger.info(f"批量PDF提取完成: 共处理 {len(file_paths)} 个文件")
        return results
