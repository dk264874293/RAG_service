"""
结果保存器 - 解耦文件 I/O 逻辑
"""

import os
import json
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime


class ResultSaver:
    """保存 OCR 结果到本地文件系统"""

    def __init__(
        self,
        output_dir: str,
        max_image_size: int = 10 * 1024 * 1024,
        download_timeout: int = 10,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化结果保存器

        Args:
            output_dir: 输出目录路径
            max_image_size: 图片最大大小限制（字节）
            download_timeout: 下载超时时间（秒）
            logger: 日志记录器
        """
        self.output_dir = output_dir
        self.max_image_size = max_image_size
        self.download_timeout = download_timeout
        self.logger = logger or logging.getLogger(__name__)

    def ensure_output_dir(self):
        """确保输出目录存在"""
        os.makedirs(self.output_dir, exist_ok=True)

    def save_markdown(
        self, content: str, filename: str, subdir: Optional[str] = None
    ) -> str:
        """
        保存 Markdown 文件

        Args:
            content: Markdown 内容
            filename: 文件名
            subdir: 子目录名称（可选）

        Returns:
            保存的完整文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        timestamped_filename = f"{name}_{timestamp}{ext}"

        if subdir:
            full_path = os.path.join(self.output_dir, subdir, timestamped_filename)
        else:
            full_path = os.path.join(self.output_dir, timestamped_filename)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"Markdown document saved at {full_path}")
        return full_path

    def save_json(
        self, data: Dict[str, Any], filename: str, subdir: Optional[str] = None
    ) -> str:
        """
        保存 JSON 文件

        Args:
            data: JSON 数据
            filename: 文件名
            subdir: 子目录名称（可选）

        Returns:
            保存的完整文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        timestamped_filename = f"{name}_{timestamp}{ext}"

        if subdir:
            full_path = os.path.join(self.output_dir, subdir, timestamped_filename)
        else:
            full_path = os.path.join(self.output_dir, timestamped_filename)

        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"JSON file saved at {full_path}")
        return full_path

    def save_text(
        self, content: str, filename: str, subdir: Optional[str] = None
    ) -> str:
        """
        保存纯文本文件

        Args:
            content: 文本内容
            filename: 文件名
            subdir: 子目录名称（可选）

        Returns:
            保存的完整文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        timestamped_filename = f"{name}_{timestamp}{ext}"

        if subdir:
            full_path = os.path.join(self.output_dir, subdir, timestamped_filename)
        else:
            full_path = os.path.join(self.output_dir, timestamped_filename)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"Text file saved at {full_path}")
        return full_path

    def download_image(
        self, url: str, filename: str, subdir: Optional[str] = None
    ) -> Optional[str]:
        """
        下载并保存图片

        Args:
            url: 图片 URL
            filename: 保存的文件名
            subdir: 子目录名称（可选）

        Returns:
            保存的完整文件路径，失败返回 None
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name, ext = os.path.splitext(filename)
            timestamped_filename = f"{name}_{timestamp}{ext}"

            if subdir:
                full_path = os.path.join(self.output_dir, subdir, timestamped_filename)
            else:
                full_path = os.path.join(self.output_dir, timestamped_filename)

            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            response = requests.get(url, timeout=self.download_timeout, stream=True)
            response.raise_for_status()

            # 检查文件大小
            content_length = int(response.headers.get("content-length", 0))
            if content_length > self.max_image_size:
                self.logger.warning(
                    f"Image size {content_length} exceeds limit {self.max_image_size}"
                )
                return None

            # 下载内容
            img_bytes = b""
            for chunk in response.iter_content(chunk_size=8192):
                if len(img_bytes) + len(chunk) > self.max_image_size:
                    self.logger.warning("Image size exceeds limit during download")
                    return None
                img_bytes += chunk

            with open(full_path, "wb") as f:
                f.write(img_bytes)

            self.logger.info(f"Image saved at {full_path}")
            return full_path

        except requests.RequestException as e:
            self.logger.error(f"Failed to download image from {url}: {e}")
            return None

    def save_local_results(
        self, results: List[Any], filename: str = "unknown"
    ) -> Dict[str, Any]:
        """
        保存本地 OCR 结果

        Args:
            results: OCR 结果列表
            filename: 文件名

        Returns:
            保存的文件路径字典
        """
        saved_files = {"text": []}

        if not results:
            return saved_files

        # 提取文件名（去除扩展名）
        name = os.path.splitext(filename)[0]
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 创建子文件夹
        subdir = f"{name}_{timestamp}"

        self.ensure_output_dir()

        # 保存为文本文件
        text_content = ""
        for result in results:
            if hasattr(result, "text"):
                text_content += f"{result.text}\n"

        if text_content:
            text_path = self.save_text(text_content, "ocr_results.txt", subdir=subdir)
            saved_files["text"].append(text_path)

        # 统计信息
        total = sum(len(v) for v in saved_files.values())
        self.logger.info(f"Saved {total} files: {saved_files}")

        return saved_files

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

        self.ensure_output_dir()

        for i, res in enumerate(api_result["layoutParsingResults"]):
            try:
                # 保存 Markdown 文本
                if "markdown" in res and "text" in res["markdown"]:
                    md_path = self.save_markdown(
                        res["markdown"]["text"], f"markdown_{i}.md", subdir=subdir
                    )
                    saved_files["markdown"].append(md_path)

                # 下载 markdown.images 中的图片
                if "markdown" in res and "images" in res["markdown"]:
                    for img_name, img_url in res["markdown"]["images"].items():
                        img_path = self.download_image(
                            img_url, f"{img_name}_{i}", subdir=subdir
                        )
                        if img_path:
                            saved_files["images"].append(img_path)

                # 下载 outputImages 中的图片
                if "outputImages" in res:
                    for img_name, img_url in res["outputImages"].items():
                        img_path = self.download_image(
                            img_url, f"{img_name}_{i}.jpg", subdir=subdir
                        )
                        if img_path:
                            saved_files["images"].append(img_path)

                # 保存 prunedResult
                if "prunedResult" in res:
                    json_path = self.save_json(
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

    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        清理旧文件

        Args:
            max_age_hours: 文件最大保留时间（小时）
        """
        import time

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        if not os.path.exists(self.output_dir):
            return

        for root, dirs, files in os.walk(self.output_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_age = current_time - os.path.getmtime(file_path)

                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        self.logger.info(f"Cleaned up old file: {file_path}")
                    except OSError as e:
                        self.logger.error(f"Failed to remove {file_path}: {e}")
