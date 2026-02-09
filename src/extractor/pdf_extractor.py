"""
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-04 18:23:47
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-07 07:45:41
FilePath: /RAG_service/loader/pdf_loader.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AEi
"""

import io
import logging
import hashlib
from functools import lru_cache
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel, Field, validator

import pypdfium2
import pypdfium2.raw as pdfium_c
from PIL import Image

from .extractor_base import BaseExtractor
from ..models.document import Document

from .ocr_module.ocr_service import OCRService
from .ocr_module.core.base_ocr import OCRResult
from .ocr_module.core.exceptions import OCRError
from ..exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class PdfExtractorConfig(BaseModel):
    """PDF 提取器配置模型，用于参数校验"""

    model_config = {"extra": "allow"}

    min_image_size: int = Field(
        default=100, gt=0, le=10000, description="最小图片尺寸（像素）"
    )
    max_image_size_mb: float = Field(
        default=5, gt=0, le=100, description="最大图片大小（MB）"
    )
    ocr_confidence_threshold: float = Field(
        default=0.6, ge=0, le=1, description="OCR 置信度阈值"
    )

    @validator("max_image_size_mb")
    def check_size_relationship(cls, v, values):
        if "min_image_size" in values:
            min_size = values["min_image_size"]
            if v * 1024 * 1024 < min_size:
                raise ValueError("max_image_size_mb 必须允许大于 min_image_size 的图片")
        return v


# ==================== 自定义异常类 ====================
class PdfExtractorError(Exception):
    """PDF提取器基础异常类"""

    pass


class PageRenderError(PdfExtractorError):
    """页面渲染异常"""

    pass


class ImageExtractionError(PdfExtractorError):
    """图片提取异常"""

    pass


# ==================== 常量定义 ====================
class PdfExtractorConstants:
    """PDF提取器常量类"""

    # 解析模式枚举
    MODE_TEXT_LAYER = "text_layer"
    MODE_FULL_OCR = "full_ocr"

    # 默认配置值
    DEFAULT_RENDER_SCALE = 2.0  # 渲染缩放比例
    DEFAULT_PARSE_MODE = MODE_TEXT_LAYER  # 默认解析模式
    DEFAULT_OCR_CONFIDENCE_THRESHOLD = 0.6  # 默认OCR置信度阈值
    DEFAULT_IMAGE_MIN_SIZE = 100  # 默认最小图片尺寸
    DEFAULT_MAX_IMAGE_SIZE_MB = 5  # 默认最大图片大小（MB）

    # 图片标记文本
    IMAGE_MARKER = "![从 PDF 页面提取的图片]"
    OCR_NO_TEXT_MARKER = "![从 PDF 页面提取的图片（OCR无文本）]"
    LOW_CONFIDENCE_PREFIX = "[低置信度OCR文本: "
    ENHANCED_OCR_PREFIX = "[OCR文本 (置信度: {confidence:.2f}, 引擎: {engine}): "

    # 图片格式魔术字节：(魔术字节, 扩展名, MIME类型)
    IMAGE_FORMATS = [
        (b"\xff\xd8\xff", "jpg", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n", "png", "image/png"),
        (b"\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a", "jp2", "image/jp2"),
        (b"GIF8", "gif", "image/gif"),
        (b"BM", "bmp", "image/bmp"),
        (b"II*\x00", "tiff", "image/tiff"),
        (b"MM\x00*", "tiff", "image/tiff"),
        (b"II+\x00", "tiff", "image/tiff"),
        (b"MM\x00+", "tiff", "image/tiff"),
    ]

    MAX_MAGIC_LEN = max(len(m) for m, _, _ in IMAGE_FORMATS)


class PdfExtractor(BaseExtractor):
    """
    增强版PDF提取器，集成OCR功能

    支持：
    - 两种解析模式：text_layer（文本层）和 full_ocr（整页OCR）
    - 图像OCR文本提取
    - A/B测试实验分组
    - OCR结果缓存
    - 配置项检查（图片尺寸、大小限制）
    """

    # 类级别共享线程池，避免重复创建
    _executor = ThreadPoolExecutor(max_workers=4)

    def __init__(
        self,
        file_path: str,
        tenant_id: str,
        user_id: str,
        file_cache_key: str | None = None,
        config: Optional[Dict] = None,
        enable_ocr: bool = True,
        parse_mode: str = PdfExtractorConstants.DEFAULT_PARSE_MODE,
    ):
        """
        初始化增强版PDF提取器

        Args:
            file_path: PDF文件路径
            tenant_id: 工作区ID
            user_id: 用户ID
            file_cache_key: 缓存键（可选）
            config: 配置字典
            enable_ocr: 是否启用OCR，默认True
            parse_mode: PDF解析模式
                - "text_layer": 使用pypdfium2提取文本层 + 图片OCR
                - "full_ocr": 对整个PDF页面进行OCR
                默认为 "text_layer"
        """
        super().__init__(file_path, tenant_id, user_id, file_cache_key)
        # 使用 Pydantic 校验配置参数
        try:
            logger.info(f"self->config: {config}")  # 修复日志格式
            self.config_model = PdfExtractorConfig(**(config or {}))
            self.config = {**(config or {}), **self.config_model.model_dump()}
        except Exception as e:
            raise ConfigurationError(f"PDF 提取器配置无效: {e}") from e

        self.enable_ocr = enable_ocr
        logger.info(f"enable_ocr: {enable_ocr}")  # 修复日志格式

        # 从配置读取 parse_mode，如果参数未提供则使用配置值
        final_parse_mode = parse_mode or self.config.get(
            "pdf_parse_mode", PdfExtractorConstants.DEFAULT_PARSE_MODE
        )
        self.parse_mode = final_parse_mode

        # 验证解析模式
        if self.parse_mode not in [
            PdfExtractorConstants.MODE_TEXT_LAYER,
            PdfExtractorConstants.MODE_FULL_OCR,
        ]:
            logger.warning(
                f"无效的解析模式: {self.parse_mode}, 使用默认值: {PdfExtractorConstants.DEFAULT_PARSE_MODE}"
            )
            self.parse_mode = PdfExtractorConstants.DEFAULT_PARSE_MODE

        # 初始化OCR处理器（仅在需要时）
        self.ocr_service = None
        if self.enable_ocr:
            self._init_ocr_service()

        # A/B测试变体（如果启用）
        self.experiment_variant = self._assign_experiment_variant()

        # 图片缓存（使用 LRU 缓存限制内存占用，最多缓存 50 张图片）
        self.image_cache = lru_cache(maxsize=50)(self._get_cached_ocr_result)
        self._ocr_result_store = {}

        logger.info(
            f"EnhancedPdfExtractor初始化: 文件={file_path}, 变体={self.experiment_variant}, OCR={self.enable_ocr}, 解析模式={self.parse_mode}"
        )

    def _init_ocr_service(self):
        """
        初始化OCR服务（根据配置构建OCRService实例）

        OCR配置项：
        - ocr_engine: OCR引擎类型（paddle-api, paddle-local）
        - ocr_languages: OCR语言列表
        - confidence_threshold: 置信度阈值
        - enable_ocr_cache: 是否启用OCR缓存
        - cache_ttl: 缓存有效期（秒）
        - min_image_size: 最小图片尺寸（像素）
        - max_image_size_mb: 最大图片大小（MB）
        - ocr_api_endpoint: PaddleOCR API 端点
        - ocr_output_dir: PaddleOCR 输出目录

        Raises:
            OCRError: OCR服务初始化失败时抛出
        """
        try:
            # 获取OCR引擎类型
            engine = self.config.get("ocr_engine", "paddle")

            # 获取两种配置的置信度阈值
            pdf_extractor_threshold = self.config.get(
                "ocr_confidence_threshold",
                PdfExtractorConstants.DEFAULT_OCR_CONFIDENCE_THRESHOLD,
            )

            ocr_module_threshold = self.config.get(
                "ocr_module_confidence_threshold", pdf_extractor_threshold
            )
            # 构建 OCRService 配置参数
            self.ocr_service = OCRService(
                engine=engine,
                ocr_version=self.config.get("ocr_version", "PaddleOCR-VL"),
                confidence_threshold=ocr_module_threshold,
                cache_ttl=self.config.get("cache_ttl", 3600),
                api_endpoint=self.config.get("ocr_api_endpoint"),
                api_key=self.config.get("ocr_api_key"),
                output_dir=self.config.get("ocr_output_dir"),
                parse_mode=self.config.get("pdf_parse_mode", "text_layer"),
            )
            self.pdf_extractor_threshold = pdf_extractor_threshold

            logger.info(
                f"OCR服务初始化成功: 引擎={engine}, "
                f"ocr_module阈值={ocr_module_threshold}, "
                f"pdf_extractor阈值={pdf_extractor_threshold}"
            )

        except Exception as e:
            logger.error(f"OCR服务初始化失败: {e}")
            raise OCRError(f"OCR服务初始化失败: {e}") from e

    def _assign_experiment_variant(self) -> str:
        """
        分配A/B测试实验变体

        流程：
        1. 检查是否启用A/B测试
        2. 如果未启用，返回 "control"
        3. 如果启用，根据权重随机分配实验变体

        Returns:
            实验变体名称（control, ocr_basic, ocr_enhanced）
        """
        if not self.config.get("enable_ab_testing", False):
            # A/B测试未启用，使用默认变体
            return "control"

        # 这里可以调用专门的A/B测试模块
        # 暂时使用简单的随机分配
        import random

        experiment_groups = self.config.get(
            "experiment_groups", {"control": 0.5, "ocr_basic": 0.3, "ocr_enhanced": 0.2}
        )

        # 归一化权重
        total = sum(experiment_groups.values())
        if total <= 0:
            return "control"

        rand = random.random() * total
        cumulative = 0
        for variant, weight in experiment_groups.items():
            cumulative += weight
            if rand <= cumulative:
                return variant

        return "control"

    def _run_async_ocr_task(self, ocr_func: callable, *args, **kwargs) -> Any:
        """
        同步包装器：调用 OCR 函数（修复异步包装器问题）

        关键修复：OCRService.recognize() 是同步函数，不需要 asyncio.run()
        原问题：对同步函数使用 asyncio.run() 会导致 "a coroutine was expected" 错误

        Args:
            ocr_func: OCR任务函数（同步函数）
            *args: OCR任务的位置参数
            **kwargs: OCR任务的关键字参数

        Returns:
            OCR任务的结果

        Raises:
            OCRError: OCR执行失败时抛出
        """
        try:
            # 直接调用同步函数，不需要 asyncio.run()
            return ocr_func(*args, **kwargs)
        except Exception as e:
            error_msg = f"OCR任务执行失败: {e}"
            logger.error(error_msg)
            raise OCRError(error_msg) from e

    @classmethod
    def cleanup(cls):
        """清理类级别资源（关闭线程池）"""
        if hasattr(cls, "_executor") and cls._executor is not None:
            cls._executor.shutdown(wait=True)
            logger.info("PdfExtractor 线程池已关闭")

    def _get_cached_ocr_result(self, img_hash: str, img_bytes: bytes) -> Optional[str]:
        """
        获取缓存的 OCR 结果（作为 LRU 缓存的内部方法）

        Args:
            img_hash: 图片哈希值
            img_bytes: 图片字节数据

        Returns:
            OCR 识别的文本（如果存在），否则返回 None
        """
        return self._ocr_result_store.get(img_hash)

    def _set_cached_ocr_result(self, img_hash: str, result: str):
        """存储 OCR 结果到缓存"""
        self._ocr_result_store[img_hash] = result

    def _extract_images(self, page):
        """
        从 PDF 页面提取图片并执行OCR

        参数：
            page: pypdfium2 页面对象。

        返回：
            包含OCR文本的字符串。
        """
        # 检查是否启用OCR
        if not self.enable_ocr:
            # OCR未启用：使用原始方法（仅标记图片）
            return super()._extract_images(page)

        # OCR处理：提取图片并执行OCR
        image_content = []

        try:
            image_objects = page.get_objects(filter=(pdfium_c.FPDF_PAGEOBJ_IMAGE,))

            for obj_idx, obj in enumerate(image_objects):
                try:
                    img_byte_arr = io.BytesIO()
                    obj.extract(img_byte_arr, fb_format="png")
                    img_bytes = img_byte_arr.getvalue()

                    if not img_bytes:
                        continue

                    # 检查缓存
                    img_hash = hashlib.md5(img_bytes).hexdigest()
                    cached_result = self.image_cache(img_hash, img_bytes)

                    if cached_result:
                        logger.debug(f"使用缓存的OCR结果: 图片{obj_idx}")
                        ocr_text = cached_result
                    else:
                        # 执行OCR（可能抛出OCRError）
                        ocr_text = self._perform_ocr(img_bytes, obj_idx)
                        # 缓存结果
                        self._set_cached_ocr_result(img_hash, ocr_text)

                    # 添加到内容
                    if ocr_text:
                        image_content.append(ocr_text)
                    else:
                        # OCR失败或没有文本，使用占位符
                        image_content.append("![从 PDF 页面提取的图片（OCR无文本）]")

                except OCRError as e:
                    logger.error(f"图片{obj_idx} OCR失败: {e}")
                    # 根据配置决定是否继续处理
                    if self.config.get("ocr_error_continue", False):
                        image_content.append(f"![OCR失败: {e}]")
                    else:
                        raise  # 中断处理

                except Exception as e:
                    logger.error("从 PDF 提取图片失败: %s", e)
                    continue

        except Exception as e:
            logger.warning("无法从 PDF 页面获取对象: %s", e)

        return "\n".join(image_content)

    def _perform_ocr(self, img_bytes: bytes, img_index: int) -> str:
        """
        执行图片OCR处理（同步包装）

        Args:
            img_bytes: 图片字节数据
            img_index: 图片索引

        Returns:
            OCR识别的文本

        Raises:
            OCRError: OCR处理失败时抛出
        """
        if not self.ocr_service:
            raise OCRError("OCR服务未初始化")

        try:
            # 使用统一的异步OCR任务执行器
            result = self._run_async_ocr_task(
                self.ocr_service.recognize,
                img_bytes,
                return_format="dict",
            )
            logger.debug("OCR识别结果: %s", result)

            # 处理结果
            if isinstance(result, str):
                # return_format='text' 或 'json'
                if not result.strip():
                    logger.info(f"图片{img_index} OCR未识别到文本")
                return result
            elif isinstance(result, list) and len(result) > 0:
                # return_format='dict' 或 None
                # 转换字典为OCRResult对象
                ocr_results = []
                for r in result:
                    if isinstance(r, dict):
                        ocr_results.append(OCRResult(**r))
                    elif isinstance(r, OCRResult):
                        ocr_results.append(r)

                # 合并所有文本
                texts = [r.text for r in ocr_results if r.text]

                if not texts:
                    logger.info(f"图片{img_index} OCR未识别到文本")
                    return ""

                # 计算平均置信度
                avg_confidence = sum(r.confidence for r in ocr_results) / len(
                    ocr_results
                )

                # 根据实验变体返回格式
                if self.experiment_variant == "ocr_basic":
                    # 基础版：直接返回OCR文本
                    return " ".join(texts)
                elif self.experiment_variant == "ocr_enhanced":
                    # 增强版：添加元信息
                    return (
                        PdfExtractorConstants.ENHANCED_OCR_PREFIX.format(
                            confidence=avg_confidence,
                            engine=self.ocr_service.engine_name,
                        )
                        + " ".join(texts)
                        + "]"
                    )
                else:
                    return " ".join(texts)
            else:
                # OCR 未识别到文本
                logger.info(f"图片{img_index} OCR未识别到文本")
                return ""

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"图片{img_index} OCR处理异常: {e}")
            raise OCRError(f"图片{img_index} OCR处理失败: {e}") from e

    def _render_page_to_image(
        self, page, scale: float = PdfExtractorConstants.DEFAULT_RENDER_SCALE
    ) -> Optional[Image.Image]:
        """
        将PDF页面渲染为PIL图片（包含配置项检查）

        Args:
            page: pypdfium2页面对象
            scale: 渲染缩放比例，默认2.0（提高清晰度）

        Returns:
            PIL Image对象（如果图片不符合配置，返回None）

        Raises:
            PageRenderError: 页面渲染失败时抛出
        """
        try:
            # 渲染页面为bitmap
            # 注意：pypdfium2 v5.0+ 移除了 FPDF_COLORSCHEME_BGR 常量
            # 使用默认的 color_scheme=None 即可（默认为 RGB 格式）
            bitmap = page.render(
                scale=scale,
                rotation=0,
            )

            # 转换为PIL Image（pypdfium2 v5.0+ 默认为 RGB 格式）
            pil_image = bitmap.to_pil()

            # 检查图片尺寸（如果小于最小尺寸，跳过）
            if (
                pil_image.width < self.config_model.min_image_size
                or pil_image.height < self.config_model.min_image_size
            ):
                logger.warning(
                    f"图片尺寸过小（{pil_image.size}），小于最小值（{self.config_model.min_image_size}），跳过OCR"
                )
                return None

            # 检查文件大小（估算）
            max_image_size_bytes = self.config_model.max_image_size_mb * 1024 * 1024

            # 估算文件大小（PIL Image的tobytes方法）
            estimated_size = len(pil_image.tobytes())
            if estimated_size > max_image_size_bytes:
                logger.warning(
                    f"图片过大（{estimated_size / (1024 * 1024):.2f} MB），超过最大值（{self.config_model.max_image_size_mb} MB），跳过OCR"
                )
                return None

            return pil_image

        except Exception as e:
            error_msg = f"渲染页面为图片失败: {e}"
            logger.error(error_msg)
            raise PageRenderError(error_msg) from e

    def _run_async_ocr_page(self, image_path: str, page_num: int) -> str:
        """
        在同步上下文中运行整页OCR处理（使用统一的异步OCR执行器）

        Args:
            image_path: 图片路径
            page_num: 页码

        Returns:
            OCR识别的文本

        Raises:
            OCRError: OCR执行失败时抛出
        """
        try:
            # 使用统一的异步OCR任务执行器
            result_text = self._run_async_ocr_task(
                self.ocr_service.recognize,
                image_path,
                return_format="text",
            )

            if result_text:
                logger.info(f"页面{page_num} OCR识别成功，文本长度: {len(result_text)}")
            else:
                logger.warning(f"页面{page_num} OCR未识别到文本")

            return result_text

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"页面{page_num} 异步OCR执行失败: {e}")
            raise OCRError(f"页面{page_num} OCR执行失败: {e}") from e

    def _ocr_page(self, page_image: Image.Image, page_num: int) -> str:
        """
        对整页图片进行OCR识别

        Args:
            page_image: PIL图片对象
            page_num: 页码

        Returns:
            OCR识别的文本

        Raises:
            OCRError: OCR处理失败时抛出
        """
        if not self.ocr_service:
            raise OCRError("OCR服务未初始化")

        try:
            import tempfile

            # 创建临时文件保存页面图片（delete=True确保文件自动清理）
            with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp_file:
                tmp_path = tmp_file.name
                page_image.save(tmp_path, "PNG")

                # 在临时文件有效期间进行OCR处理
                ocr_text = self._run_async_ocr_page(tmp_path, page_num)

                return ocr_text

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"页面{page_num} OCR处理失败: {e}")
            raise OCRError(f"页面{page_num} OCR处理失败: {e}") from e

    def _extract_with_text_layer(self, page) -> str:
        """
        使用文本层提取 + 图片OCR（原有逻辑）

        流程：
        1. 从页面提取文本层（直接可选择的文本）
        2. 提取页面中的图片（如果enable_ocr为True，执行图片OCR）
        3. 合并文本和图片OCR结果

        Args:
            page: pypdfium2页面对象

        Returns:
            提取的文本内容（文本层 + 图片OCR）

        Raises:
            PdfExtractorError: 提取失败时抛出
        """
        try:
            # 提取文本层
            text_page = page.get_textpage()
            content = text_page.get_text_range()
            text_page.close()

            # 提取图片（可能包含OCR）
            try:
                image_content = self._extract_images(page)
                if image_content:
                    content += "\n" + image_content
            except ImageExtractionError as e:
                logger.warning(f"图片提取失败: {e}")
                # 继续处理，不影响文本提取

            return content

        except Exception as e:
            logger.error(f"文本层提取失败: {e}")
            raise PdfExtractorError(f"文本层提取失败: {e}") from e

    def _extract_with_full_ocr(self, pdf_bytes: bytes, page_number: int) -> str:
        """
        使用整页OCR提取（直接传递PDF给API）

        流程：
        1. 直接将PDF文件传递给OCR服务
        2. API支持完整PDF文件处理（fileType=0）

        Args:
            pdf_bytes: PDF文件的字节数据
            page_number: 页码（用于日志）

        Returns:
            OCR识别的文本内容
        """
        try:
            # 直接传递PDF文件给OCR服务
            ocr_text = self._run_async_ocr_task(
                self.ocr_service.recognize,
                pdf_bytes,
                return_format="text",
            )

            if ocr_text:
                logger.info(f"页面{page_number} OCR识别成功，文本长度: {len(ocr_text)}")
            else:
                logger.warning(f"页面{page_number} OCR未识别到文本")

            return ocr_text

        except OCRError:
            raise
        except Exception as e:
            logger.error(f"页面{page_number} OCR执行失败: {e}")
            raise OCRError(f"页面{page_number} OCR执行失败: {e}") from e

    def extract(self) -> list:
        """
        提取PDF文件内容，根据parse_mode选择不同的提取策略

        流程：
        1. 如果parse_mode == "full_ocr"：
           - 直接将整个PDF文件传递给OCR API
           - API一次性处理所有页面（fileType=0）
        2. 如果parse_mode == "text_layer"（默认）：
           - 提取文本层
           - 对页面中的图片进行OCR（如果enable_ocr为True）

        Returns:
            Document对象列表

        Raises:
            PdfExtractorError: PDF解析失败时抛出
        """
        documents = []
        try:
            pdf_reader = pypdfium2.PdfDocument(self._file_path, autoclose=True)
            try:
                # 读取PDF文件的字节数据（用于full_ocr模式）
                with open(self._file_path, "rb") as f:
                    pdf_bytes = f.read()

                if self.parse_mode == PdfExtractorConstants.MODE_FULL_OCR:
                    # 模式2：整页OCR（适合扫描版PDF）
                    # 直接传递整个PDF给OCR API，一次性处理所有页面
                    content = self._extract_with_full_ocr(pdf_bytes, 0)

                    # 创建单个文档对象（包含所有页面内容）
                    metadata = {"source": self._file_path, "page": 0}
                    documents.append(Document(page_content=content, metadata=metadata))
                else:
                    # 模式1：文本层提取 + 图片OCR（默认，适合有文本层的PDF）
                    for page_number, page in enumerate(pdf_reader):
                        content = self._extract_with_text_layer(page)
                        metadata = {"source": self._file_path, "page": page_number}
                        documents.append(
                            Document(page_content=content, metadata=metadata)
                        )
            finally:
                pdf_reader.close()

        except Exception as e:
            error_msg = f"PDF解析失败: {self._file_path}, 错误: {e}"
            logger.error(error_msg)
            raise PdfExtractorError(error_msg) from e

        return documents

    def get_ocr_stats(self) -> Dict[str, Any]:
        """
        获取OCR处理统计信息

        Returns:
            包含以下字段的字典：
            - ocr_available: OCR是否可用
            - engine_name: OCR引擎名称
            - engine_info: OCR引擎详细信息
            - experiment_variant: 实验变体
            - cached_images: 缓存的图片数量
            - config: OCR配置信息
        """
        if not self.ocr_service:
            return {"ocr_available": False}

        stats = {
            "ocr_available": True,
            "engine_name": self.ocr_service.engine_name,
            "engine_info": self.ocr_service.get_engine_info(),
            "experiment_variant": self.experiment_variant,
            "cached_images": len(self._ocr_result_store),
            "config": {
                "ocr_engine": self.config.get("ocr_engine", "paddle-api"),
                "enable_ab_testing": self.config.get("enable_ab_testing", False),
                "ocr_confidence_threshold": getattr(
                    self, "pdf_extractor_threshold", 0.6
                ),
            },
        }

        # 添加缓存统计（如果可用）
        if self.ocr_service.cache_manager:
            stats["cache_stats"] = {
                "enabled": True,
                "ttl": self.ocr_service.config.cache_ttl,
            }

        return stats
