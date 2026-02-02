'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-05 06:06:30
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-02-02 15:55:42
FilePath: /RAG_service/loader/extractor_base.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
"""
文档加载器实现的抽象接口。
"""
#Python 内置的 abc（抽象基类）模块中，导入了抽象类基模板 ABC 和抽象方法装饰器 abstractmethod，为后续定义抽象类和抽象方法提供支持。
from abc import ABC, abstractmethod

class BaseExtractor(ABC):
    """
    文档加载器实现的抽象接口。
    """
    
    def __init__(self, file_path: str, tenant_id: str, user_id: str, file_cache_key: str | None = None):
        """
        初始化基础提取器
        
        Args:
            file_path: 文件路径
            tenant_id: 工作区ID
            user_id: 用户ID
            file_cache_key: 缓存键（可选）
        """
        self._file_path = file_path
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._file_cache_key = file_cache_key
    
    @abstractmethod
    def extract(self) -> list:
        raise NotImplementedError

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
            # OCR未启用：使用默认方法（仅标记图片）
            return "![从 PDF 页面提取的图片]"

        # 根据实验变体决定处理方式
        if self.experiment_variant == "control":
            # 控制组：使用默认方法（仅标记图片）
            return "![从 PDF 页面提取的图片]"