"""
安全相关工具函数
处理JWT令牌、密码哈希等安全操作
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import bcrypt
from jose import JWTError, jwt
from pydantic import ValidationError

import config


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    # bcrypt 有72字节限制，手动截断
    truncated_password = (
        plain_password[:72] if len(plain_password) > 72 else plain_password
    )
    return bcrypt.checkpw(
        truncated_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    # bcrypt 有72字节限制，手动截断
    truncated_password = password[:72] if len(password) > 72 else password
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(truncated_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


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
            minutes=config.settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode, config.settings.secret_key, algorithm=config.settings.algorithm
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
            token, config.settings.secret_key, algorithms=[config.settings.algorithm]
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
            token, config.settings.secret_key, algorithms=[config.settings.algorithm]
        )

        # 检查过期时间
        exp = payload.get("exp")
        if exp is None:
            return None

        expire_datetime = datetime.fromtimestamp(exp)
        if expire_datetime < datetime.utcnow():
            return None

        return payload
    except JWTError:
        return None
