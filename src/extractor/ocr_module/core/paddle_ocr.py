# core/paddle_ocr.py
import os
import base64
from typing import List, Union, Dict, Any
from PIL import Image
import numpy as np
import logging
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tempfile import NamedTemporaryFile

from .base_ocr import BaseOCR, OCRResult
from .exceptions import (
    OCREngineInitError,
    OCRNetworkError,
    OCRConfigError,
    OCRParseError,
    OCRInputError,
)
from .result_saver import ResultSaver


class PaddleOCRWrapper(BaseOCR):
    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.engine = None

        self.version = None
        self.run_mode = None
        self.api_endpoint = config.get("api_endpoint", None)
        self.api_key = config.get("api_key", None)
        self.output_dir = config.get("output_dir", None)
        self.result_saver = None
        self.logger.info("初始化 PaddleOCRWrapper", config)

        self._validate_config()
        self._detect_version()
        self._init_result_saver()

    def _validate_config(self):
        """验证配置参数"""
        self.logger.info("验证配置参数", self.config)
        ocr_version = self.config.get("ocr_engine", "PaddleOCR-VL")
        if ocr_version not in ["PP-StructureV3", "PaddleOCR-VL", "PP-OCRv5"]:
            raise OCRConfigError(f"不支持的 OCR 版本: {ocr_version}")

        if ocr_version == "PaddleOCR-VL":
            if not self.api_endpoint:
                raise OCRConfigError("远程模式需要配置 api_endpoint 参数")
            if not self.api_key:
                raise OCRConfigError("远程模式需要配置 api_key 参数")
            if not self.output_dir:
                raise OCRConfigError("远程模式需要配置 output_dir 参数")

    def _init_result_saver(self):
        """初始化结果保存器"""
        if self.output_dir:
            max_image_size = self.config.get("max_image_size", 10 * 1024 * 1024)
            download_timeout = self.config.get("download_timeout", 100)
            self.result_saver = ResultSaver(
                output_dir=self.output_dir,
                max_image_size=max_image_size,
                download_timeout=download_timeout,
                logger=self.logger,
            )

    def _detect_version(self):
        """检测PaddleOCR版本并确定运行模式 ，支持PP-StructureV3和PaddleOCR-VL"""
        ocr_version = self.config.get("ocr_version", "PaddleOCR-VL")

        if ocr_version == "PP-StructureV3":
            self.version = "PP-StructureV3"
            self.run_mode = "local"
            self.logger.info("使用 PP-StructureV3 版本，本地模式运行")
        elif ocr_version == "PaddleOCR-VL":
            self.version = "PaddleOCR-VL"
            self.run_mode = "remote"
            self.logger.info("使用 PaddleOCR-VL 版本，远程API模式运行")
        else:
            self.version = "PP-OCRv5"
            self.run_mode = "local"
            self.logger.info("使用默认 PP-OCRv5 版本，本地模式运行")

    def _extract_filename(self, input_data) -> str:
        """
        从输入数据中提取文件名

        Args:
            input_data: 输入数据

        Returns:
            文件名
        """
        if isinstance(input_data, str):
            return os.path.basename(input_data)
        elif isinstance(input_data, dict):
            return input_data.get("filename", "unknown")
        else:
            return "unknown"

    def initialize(self):
        """初始化PaddleOCR，根据版本选择运行模式"""
        try:
            if self.run_mode == "local":
                self._initialize_local()
            elif self.run_mode == "remote":
                self._initialize_remote()
            else:
                raise OCRConfigError(f"未知的运行模式: {self.run_mode}")

            self.initialized = True
            self.logger.info(
                f"PaddleOCR初始化完成 - 版本: {self.version}, 模式: {self.run_mode}"
            )
        except Exception as e:
            self.logger.error(f"PaddleOCR 初始化失败: {e}")
            raise OCREngineInitError(f"OCR 引擎初始化失败: {e}") from e

    def _initialize_local(self):
        try:
            if self.version == "PP-OCRv5":
                from paddleocr import PaddleOCR

                self.engine = PaddleOCR(
                    # 文档方向调整
                    use_doc_orientation_classify=False,
                    # 文本图像矫正模块
                    use_doc_unwarping=False,
                    # 文本行方向分类模块
                    use_textline_orientation=False,
                )
            elif self.version == "PP-StructureV3":
                from paddleocr import PPStructureV3

                self.engine = PPStructureV3(
                    # 文档方向调整
                    use_doc_orientation_classify=True,
                    #  文本图像矫正模块
                    use_doc_unwarping=True,
                    # 图表解析模块
                    useChartRecognition=False,
                )
            self.logger.info("本地 PaddleOCR 引擎初始化成功")
        except ImportError as e:
            self.logger.error(f"PaddleOCR 依赖未安装: {e}")
            raise OCREngineInitError("请先安装 paddleocr 库") from e
        except Exception as e:
            self.logger.error(f"本地 PaddleOCR 初始化失败: {e}")
            raise OCREngineInitError(f"本地 OCR 引擎初始化失败: {e}") from e

    def _initialize_remote(self):
        """初始化远程API模式"""
        self.engine = {
            "api_endpoint": self.api_endpoint,
            "api_key": self.api_key,
            "timeout": self.config.get("api_timeout", 60),
        }
        self.logger.info(f"远程 API 模式初始化成功，端点: {self.api_endpoint}")

    def recognize(
        self, input_data: Union[str, bytes, np.ndarray, Image.Image, dict], **kwargs
    ) -> List[OCRResult]:
        """
        统一的 OCR 识别接口

        Args:
            input_data: 输入数据，支持以下类型：
                - str: 文件路径
                - bytes: 图片二进制数据（远程模式）
                - np.ndarray: 图片数组（本地模式）
                - Image.Image: PIL 图片对象（本地模式）
                - dict: {"file": base64_encoded, "fileType": 0}（远程模式）
            **kwargs: 额外参数

        Returns:
            OCR 结果列表
        """
        if not self.initialized:
            self.initialize()

        filename = self._extract_filename(input_data)

        if self.run_mode == "local":
            return self._recognize_local(input_data, filename=filename, **kwargs)
        elif self.run_mode == "remote":
            return self._recognize_remote(input_data, filename=filename, **kwargs)
        else:
            raise OCRConfigError(f"未知的运行模式: {self.run_mode}")

    def _recognize_local(
        self,
        input_data: Union[str, np.ndarray, Image.Image],
        filename: str = "unknown",
        **kwargs,
    ) -> List[OCRResult]:
        """
        本地模式 OCR 识别

        Args:
            input_data: 文件路径、图片数组或 PIL 图片对象
            filename: 文件名

        Returns:
            OCR 结果列表
        """
        temp_file = None

        try:
            path = None

            if isinstance(input_data, str):
                path = input_data
            elif isinstance(input_data, np.ndarray):
                temp_file = NamedTemporaryFile(delete=False, suffix=".png")
                Image.fromarray(input_data).save(temp_file.name)
                path = temp_file.name
            elif isinstance(input_data, Image.Image):
                temp_file = NamedTemporaryFile(delete=False, suffix=".png")
                input_data.save(temp_file.name)
                path = temp_file.name
            else:
                raise OCRInputError(
                    f"不支持的输入类型: {type(input_data)}。"
                    "本地模式支持 str、np.ndarray、Image.Image"
                )

            result = self.engine.predict(path, **kwargs)

            # 保存本地 OCR 结果
            if self.result_saver:
                saved_files = self.result_saver.save_local_results(result, filename)
                self.logger.debug(f"已保存本地结果到 {len(saved_files)} 个文件")

            return self._parse_results(result)

        except Exception as e:
            self.logger.error(f"本地 OCR 识别失败: {e}")
            raise OCREngineInitError(f"本地 OCR 识别失败: {e}") from e
        finally:
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except OSError:
                    pass

    def _recognize_remote(
        self, input_data: Union[bytes, str, dict], filename: str = "unknown", **kwargs
    ) -> List[OCRResult]:
        """
        远程 API 模式 OCR 识别

        Args:
            input_data:
                - bytes: 图片的二进制数据（PNG、JPG等）
                - str: 文件路径（PDF 或图片）
                - dict: {"file": base64_encoded, "fileType": 0/1}
            filename: 文件名

        Returns:
            OCR 结果列表
        """
        try:
            file_data = None

            if isinstance(input_data, dict):
                file_data = input_data.get("file", "")
            elif isinstance(input_data, str):
                if not os.path.exists(input_data):
                    raise OCRInputError(f"文件不存在: {input_data}")
                with open(input_data, "rb") as f:
                    file_bytes = f.read()
                file_data = base64.b64encode(file_bytes).decode("ascii")
            elif isinstance(input_data, bytes):
                file_data = base64.b64encode(input_data).decode("ascii")
                # 修复：bytes 输入默认为图片（fileType=1）
                # 因为从 PDF 提取的图片是 PNG/JPG 格式
            else:
                raise OCRInputError(
                    f"不支持的输入类型: {type(input_data)}。"
                    "远程模式支持 bytes、str、dict"
                )

            headers = {
                "Authorization": f"token {self.engine['api_key']}",
                "Content-Type": "application/json",
            }

            features = self.config.get(
                "features",
                {
                    "orientation_classify": False,
                    "unwarping": False,
                    "chart_recognition": True,
                    "layout_detection": True,
                },
            )

            payload = {
                "file": file_data,
                "useDocOrientationClassify": features.get(
                    "orientation_classify", False
                ),
                "useDocUnwarping": features.get("unwarping", False),
                "useChartRecognition": features.get("chart_recognition", True),
                "useLayoutDetection": features.get("layout_detection", True),
                **kwargs,
            }

            # 日志脱敏
            safe_payload = payload.copy()
            safe_payload["file"] = f"<{len(payload['file'])} bytes>"
            self.logger.info(f"OCR 识别请求: {safe_payload}")

            timeout = self.engine.get("timeout", 60)
            response = requests.post(
                self.engine["api_endpoint"],
                json=payload,
                headers=headers,
                timeout=timeout,
            )

            response.raise_for_status()
            result = response.json().get("result")

            if not result:
                raise OCRParseError("API 返回结果为空")

            return self._parse_api_results(result, filename=filename)

        except requests.RequestException as e:
            self.logger.error(f"远程 API 请求失败: {e}")
            raise OCRNetworkError(f"远程 API 请求失败: {e}") from e
        except Exception as e:
            self.logger.error(f"远程 OCR 识别失败: {e}")
            raise OCREngineInitError(f"远程 OCR 识别失败: {e}") from e

    def _parse_results(self, raw_result) -> List[OCRResult]:
        """
        解析本地 OCR 结果

        Args:
            raw_result: 本地 OCR 引擎返回的原始结果

        Returns:
            OCR 结果列表
        """
        results = []

        if raw_result is None:
            return results

        try:
            for idx, line in enumerate(raw_result):
                if line is None:
                    continue

                for bbox_info in line:
                    if len(bbox_info) >= 2:
                        bbox = bbox_info[0]
                        text, confidence = bbox_info[1]

                        result = OCRResult(
                            text=text,
                            confidence=confidence,
                            bbox=bbox,
                            line_num=idx,
                            label="ocr",
                        )
                        results.append(result)
        except Exception as e:
            self.logger.error(f"解析本地 OCR 结果失败: {e}")
            raise OCRParseError(f"解析本地 OCR 结果失败: {e}") from e

        return results

    def _parse_api_results(
        self, api_result: Dict[str, Any], filename: str = "unknown"
    ) -> List[OCRResult]:
        """
        解析远程 API 返回的结果

        Args:
            api_result: API 返回的结果字典
            filename: 文件名

        Returns:
            OCR 结果列表
        """
        results = []

        if api_result is None or "layoutParsingResults" not in api_result:
            return results

        try:
            # 保存文件（如果配置了 result_saver）
            if self.result_saver:
                saved_files = self.save_api_results(api_result, filename)
                self.logger.debug(f"已保存 {len(saved_files)} 个文件")
                self.logger.debug(f"保存的文件: {saved_files}")

            # 解析 OCR 结果
            # 修复：根据实际 API 返回结构提取数据
            for i, res in enumerate(api_result["layoutParsingResults"]):
                # 尝试从 markdown.text 中提取文本（优先）
                markdown_text = ""
                if "markdown" in res and "text" in res["markdown"]:
                    markdown_text = res["markdown"]["text"]

                # 如果没有 markdown.text，尝试从 parsing_res_list 提取（向后兼容）
                if not markdown_text and "parsing_res_list" in res:
                    parsing_res_list = res["parsing_res_list"]
                    for item in parsing_res_list:
                        content = item.get("block_content", "")
                        if content:
                            markdown_text += content + "\n"

                # 如果有文本内容，创建 OCRResult
                if markdown_text:
                    result = OCRResult(
                        label="layout_parse",
                        text=markdown_text.strip(),
                        confidence=1.0,  # API 返回的文本置信度较高
                        bbox=[],  # API 不返回具体的 bbox
                        line_num=i,
                    )
                    results.append(result)

        except Exception as e:
            self.logger.error(f"解析 API 结果失败: {e}")
            raise OCRParseError(f"解析 API 结果失败: {e}") from e

        return results

    def recognize_batch(
        self,
        images: List[Union[str, np.ndarray, "Image.Image", bytes]],
        max_workers: int = 4,
        **kwargs,
    ) -> List[List[OCRResult]]:
        """
        批量识别图片（支持并发）

        Args:
            images: 图片列表，支持 str、np.ndarray、Image.Image、bytes
            max_workers: 最大并发数
            **kwargs: 额外参数

        Returns:
            OCR 结果列表的列表
        """
        if not self.initialized:
            self.initialize()

        results = [None] * len(images)

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_idx = {
                    executor.submit(self.recognize, img, **kwargs): idx
                    for idx, img in enumerate(images)
                }

                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        self.logger.error(f"批量识别第 {idx} 张图片失败: {e}")
                        results[idx] = []

        except Exception as e:
            self.logger.error(f"批量识别失败: {e}")
            raise

        return results

    def get_engine_info(self) -> Dict[str, Any]:
        """
        获取引擎信息

        Returns:
            引擎信息字典
        """
        info = {
            "version": self.version,
            "run_mode": self.run_mode,
            "initialized": self.initialized,
            "has_result_saver": self.result_saver is not None,
        }

        if self.run_mode == "remote":
            info["api_endpoint"] = self.api_endpoint
            info["output_dir"] = self.output_dir
            if self.result_saver:
                info["max_image_size"] = self.result_saver.max_image_size
                info["download_timeout"] = self.result_saver.download_timeout

        return info

    def save_api_results(
        self, api_result: Dict[str, Any], filename: str = "unknown"
    ) -> Dict[str, Any]:
        saved_files = {"markdown": [], "images": [], "json": []}

        # 验证输入
        if not api_result or "layoutParsingResults" not in api_result:
            self.logger.warning("Invalid api_result: missing layoutParsingResults")
            return saved_files

        # 提取文件名（去除扩展名）
        name = os.path.splitext(filename)[0]
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 创建子文件夹
        subdir = f"{name}_{timestamp}"

        self.result_saver.ensure_output_dir()

        for i, res in enumerate(api_result["layoutParsingResults"]):
            try:
                # 保存 Markdown 文本
                if "markdown" in res and "text" in res["markdown"]:
                    md_path = self.result_saver.save_markdown(
                        res["markdown"]["text"], f"markdown_{i}.md", subdir=subdir
                    )
                    saved_files["markdown"].append(md_path)

                # 下载 markdown.images 中的图片
                if "markdown" in res and "images" in res["markdown"]:
                    for img_name, img_url in res["markdown"]["images"].items():
                        img_path = self.result_saver.download_image(
                            img_url, f"{img_name}_{i}", subdir=subdir
                        )
                        if img_path:
                            saved_files["images"].append(img_path)

                # 下载 outputImages 中的图片
                if "outputImages" in res:
                    for img_name, img_url in res["outputImages"].items():
                        img_path = self.result_saver.download_image(
                            img_url, f"{img_name}_{i}.jpg", subdir=subdir
                        )
                        if img_path:
                            saved_files["images"].append(img_path)

                # 保存 prunedResult
                if "prunedResult" in res:
                    json_path = self.result_saver.save_json(
                        res["prunedResult"], f"prunedResult_{i}.json", subdir=subdir
                    )
                    saved_files["json"].append(json_path)

            except Exception as e:
                self.logger.error(f"Failed to save result {i}: {e}")
                continue

        # 统计信息
        total = sum(len(v) for v in saved_files.values())
        self.logger.info(f"Saved {total} files: {saved_files}")

        return saved_files
