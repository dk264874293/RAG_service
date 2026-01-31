"""
认证依赖和授权逻辑
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.security import verify_token
import config


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    获取当前认证用户

    Args:
        credentials: HTTP Bearer令牌

    Returns:
        dict: 用户信息

    Raises:
        HTTPException: 令牌无效或过期
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    return {"user_id": user_id, "token": token, "payload": payload}


async def get_current_active_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    获取当前活跃用户（可扩展添加用户状态检查）

    Args:
        current_user: 当前用户信息

    Returns:
        dict: 用户信息
    """
    return current_user


async def verify_api_key(api_key: str) -> bool:
    """
    验证API密钥（可选的认证方式）

    Args:
        api_key: API密钥

    Returns:
        bool: 密钥是否有效
    """
    return api_key == config.settings.api_key if config.settings.api_key else False


class OptionalAuth:
    """
    可选认证依赖 - 如果提供令牌则验证，否则返回None
    """

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(
            HTTPBearer(auto_error=False)
        ),
    ) -> Optional[dict]:
        if credentials is None:
            return None

        token = credentials.credentials
        payload = verify_token(token)

        if payload is None:
            return None

        user_id: str = payload.get("sub")
        if user_id is None:
            return None

        return {"user_id": user_id, "token": token, "payload": payload}


optional_auth = OptionalAuth()
