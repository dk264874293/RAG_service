"""
输入验证和数据清理工具
提供安全的输入验证和数据清理功能
"""

import re
import html
from typing import Optional, List, Any
from pydantic import validator, field_validator


class InputValidator:
    """
    输入验证器类
    提供静态方法用于各种输入验证
    """

    # SQL注入模式
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--)|(/\\*)|(\\*/)|(;)",
        r"\bor\b\s+\d+\s*=\s*\d+",
        r"\bAND\b\s+\d+\s*=\s*\d+",
    ]

    # XSS攻击模式
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<embed[^>]*>",
        r"<object[^>]*>",
    ]

    @staticmethod
    def sanitize_string(input_string: str, max_length: int = 10000) -> str:
        """
        清理字符串输入

        - 移除控制字符
        - HTML转义
        - 限制长度
        - 移除多余的空白字符

        Args:
            input_string: 输入字符串
            max_length: 最大允许长度

        Returns:
            str: 清理后的字符串
        """
        if not input_string:
            return ""

        cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", input_string)

        cleaned = html.escape(cleaned)

        if len(cleaned) > max_length:
            cleaned = cleaned[:max_length]

        cleaned = " ".join(cleaned.split())

        return cleaned

    @staticmethod
    def validate_query(query: str) -> str:
        """
        验证并清理搜索查询

        - 检查SQL注入模式
        - 检查XSS攻击模式
        - 清理特殊字符
        - 限制长度

        Args:
            query: 搜索查询字符串

        Returns:
            str: 清理后的查询字符串

        Raises:
            ValueError: 如果检测到恶意输入
        """
        if not query or not query.strip():
            raise ValueError("查询不能为空")

        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError("查询包含非法字符")

        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError("查询包含非法字符")

        return InputValidator.sanitize_string(query, max_length=1000)

    @staticmethod
    def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
        """
        验证文件类型是否在允许列表中

        Args:
            filename: 文件名
            allowed_extensions: 允许的扩展名列表（例如：[".pdf", ".txt"]）

        Returns:
            bool: 文件类型是否合法
        """
        if not filename:
            return False

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in allowed_extensions

    @staticmethod
    def validate_metadata(metadata: dict) -> dict:
        """
        验证并清理元数据

        - 确保所有键都是字符串
        - 清理所有字符串值
        - 移除空值
        - 限制字典大小

        Args:
            metadata: 元数据字典

        Returns:
            dict: 清理后的元数据
        """
        if not metadata:
            return {}

        cleaned = {}
        for key, value in metadata.items():
            clean_key = str(key)

            if value is None:
                continue

            if isinstance(value, str):
                clean_value = InputValidator.sanitize_string(value, max_length=500)
            elif isinstance(value, (int, float, bool)):
                clean_value = value
            elif isinstance(value, list):
                clean_value = [str(v) for v in value[:10]]
            else:
                clean_value = str(value)

            cleaned[clean_key] = clean_value

        return cleaned

    @staticmethod
    def validate_k_value(k: int, min_k: int = 1, max_k: int = 100) -> int:
        """
        验证k值（检索结果数量）

        Args:
            k: 请求的结果数量
            min_k: 最小允许值
            max_k: 最大允许值

        Returns:
            int: 验证并限制后的k值

        Raises:
            ValueError: 如果k值超出范围
        """
        if not isinstance(k, int):
            raise ValueError("k必须是整数")

        if k < min_k:
            raise ValueError(f"k值不能小于{min_k}")

        if k > max_k:
            raise ValueError(f"k值不能大于{max_k}")

        return k

    @staticmethod
    def validate_file_id(file_id: str) -> str:
        """
        验证文件ID格式

        Args:
            file_id: 文件ID

        Returns:
            str: 清理后的文件ID

        Raises:
            ValueError: 如果文件ID格式无效
        """
        if not file_id or not file_id.strip():
            raise ValueError("文件ID不能为空")

        uuid_pattern = r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$"
        if not re.match(uuid_pattern, file_id.lower()):
            raise ValueError("文件ID格式无效")

        return file_id.strip()


class ValidatedSearchRequest:
    """
    带验证的搜索请求基类
    子类应该继承此类以获得自动验证功能
    """

    @field_validator("query")
    @classmethod
    def validate_query_field(cls, v: str) -> str:
        """验证查询字段"""
        return InputValidator.validate_query(v)

    @field_validator("k")
    @classmethod
    def validate_k_field(cls, v: int) -> int:
        """验证k字段"""
        return InputValidator.validate_k_value(v, min_k=1, max_k=50)

    @field_validator("filters")
    @classmethod
    def validate_filters_field(cls, v: Optional[dict]) -> Optional[dict]:
        """验证过滤器字段"""
        if v is None:
            return None
        return InputValidator.validate_metadata(v)
