"""
自定义异常类定义

定义了应用中使用的各种异常类型，以便进行更精细的错误处理和用户反馈。
"""


class ValidationError(Exception):
    """数据验证异常"""

    pass


class ProcessingError(Exception):
    """文档处理异常"""

    pass


class StorageError(Exception):
    """存储操作异常"""

    pass


class OCRError(Exception):
    """OCR 识别异常"""

    pass


class FileFormatError(Exception):
    """文件格式不支持异常"""

    pass


class ConfigurationError(Exception):
    """配置错误异常"""

    pass
