"""
安全相关工具函数
处理JWT令牌、密码哈希等安全操作
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from src.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建JWT访问令牌

    Args:
        data: 要编码到令牌中的数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT令牌
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码JWT访问令牌

    Args:
        token: JWT令牌

    Returns:
        Optional[Dict[str, Any]]: 解码后的数据，如果令牌无效则返回None
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证JWT令牌并返回payload

    Args:
        token: JWT令牌

    Returns:
        Optional[Dict[str, Any]]: 令牌payload，如果令牌无效则返回None
    """
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        exp = payload.get("exp")
        if exp is None:
            return None

        expire_datetime = datetime.fromtimestamp(exp)
        if expire_datetime < datetime.utcnow():
            return None

        return payload
    except JWTError:
        return None
