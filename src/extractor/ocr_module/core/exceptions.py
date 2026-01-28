"""
自定义异常类
"""


class OCRError(Exception):
    """OCR 基础异常"""

    pass


class OCREngineInitError(OCRError):
    """OCR 引擎初始化失败"""

    pass


class OCRNetworkError(OCRError):
    """OCR 网络请求失败"""

    pass


class OCRConfigError(OCRError):
    """OCR 配置错误"""

    pass


class OCRParseError(OCRError):
    """OCR 结果解析失败"""

    pass


class OCRInputError(OCRError):
    """OCR 输入参数错误"""

    pass
