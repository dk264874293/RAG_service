'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-05 06:06:30
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-05 06:15:59
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
    @abstractmethod
    def extract(self, doc: str) -> dict:
        raise NotImplementedError