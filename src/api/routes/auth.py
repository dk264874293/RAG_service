"""
认证相关API路由
提供用户登录、令牌刷新等认证功能
"""

from datetime import timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from src.core.security import create_access_token, verify_password
from src.config import settings


router = APIRouter(prefix="/api/auth", tags=["认证"])


class LoginRequest(BaseModel):
    """登录请求模型"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """令牌响应模型"""

    access_token: str = Field(..., description="访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")


class TokenData(BaseModel):
    """令牌数据模型"""

    user_id: str
    username: str


# 临时用户数据库（生产环境应使用真实数据库）
# 这仅用于演示，生产环境应该连接到真实的用户数据库
FAKE_USERS_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU9bK8fk.5qW",  # 密码: admin123
        "user_id": "admin_user",
        "disabled": False,
    }
}


def authenticate_user(username: str, password: str) -> Dict[str, Any] | None:
    """
    验证用户凭据

    Args:
        username: 用户名
        password: 密码

    Returns:
        用户信息字典，验证失败返回None
    """
    user = FAKE_USERS_DB.get(username)
    if not user:
        return None

    if not verify_password(password, user["password"]):
        return None

    return user


@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """
    用户登录

    使用OAuth2密码流进行身份验证，成功后返回JWT访问令牌。

    Args:
        form_data: OAuth2密码表单（username和password）

    Returns:
        TokenResponse: 包含访问令牌、令牌类型和过期时间

    Raises:
        HTTPException: 用户名或密码错误时返回401
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户账户已被禁用"
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["user_id"], "username": user["username"]},
        expires_delta=access_token_expires,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login/json", response_model=TokenResponse)
async def login_json(login_data: LoginRequest) -> TokenResponse:
    """
    用户登录（JSON格式）

    与/login端点功能相同，但接受JSON格式的请求体。

    Args:
        login_data: 包含username和password的JSON对象

    Returns:
        TokenResponse: 包含访问令牌、令牌类型和过期时间

    Raises:
        HTTPException: 用户名或密码错误时返回401
    """
    user = authenticate_user(login_data.username, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="用户账户已被禁用"
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["user_id"], "username": user["username"]},
        expires_delta=access_token_expires,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/verify-token")
async def verify_token_endpoint(
    current_user: dict = Depends(src.core.auth.get_current_user),
) -> Dict[str, Any]:
    """
    验证令牌有效性

    验证当前请求的JWT令牌是否有效。

    Args:
        current_user: 当前认证用户信息（从依赖注入获取）

    Returns:
        包含用户信息的字典

    Raises:
        HTTPException: 令牌无效时返回401
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "payload": current_user["payload"],
    }
