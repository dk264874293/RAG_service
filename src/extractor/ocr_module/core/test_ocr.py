'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-26 20:19:42
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-28 10:34:45
FilePath: /RAG_service/src/extractor/ocr_module/core/test_ocr.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE

'''
import json
import os
import base64
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import List
from dotenv import load_dotenv

import sys

load_dotenv()

project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
sys.path.insert(0, project_root)

from paddle_ocr import PaddleOCRWrapper
# from src.extractor.ocr_module.core.base_ocr import OCRResult

class TestPaddleOCRWrapper:
    def config_local_v3(self):
        return {"ocr_version": "PP-StructureV3", "output_dir": '../../../../output_dir'}
    
    def config_remote_vl(self):
        return {
            "ocr_version": "PaddleOCR-VL",
            "api_endpoint": "https://le2fu7r9l7c9bdf7.aistudio-app.com/layout-parsing",
            "api_key": os.getenv("PADDLEOCR_API_KEY"),
            "output_dir": "../../../../output_dir",
        }

    def test_init_paddle_ocr_vl(self, input_file:str):
        """测试 PaddleOCR-VL 远程模式初始化"""
        # with open(input_file, "rb") as file:
        #     file_bytes = file.read()
        #     file_data = base64.b64encode(file_bytes).decode("ascii")
        config = self.config_remote_vl()
        # required_payload = {
        #     "file": file_data,
        #     "fileType": 0,  # For PDF documents, set `fileType` to 0; for images, set `fileType` to 1
        # }
        print('config -->', config)
        
        wrapper = PaddleOCRWrapper(config)
        wrapper.recognize(input_file)

if __name__ == "__main__":
    test = TestPaddleOCRWrapper()
    test.test_init_paddle_ocr_vl(input_file="./pdfs/25AA0118采样.pdf")