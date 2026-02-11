"""
RBAC认证中间件
集成JWT认证和权限检查
"""

import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException, status, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.models.rbac import Permission
from src.api.rbac_dependencies import get_current_user_id, get_current_tenant_id

logger = logging.getLogger(__name__)


class RBACAuthMiddleware(BaseHTTPMiddleware):
    """
    RBAC认证中间件

    功能：
    1. 从JWT中提取用户信息
    2. 加载用户角色
    3. 注入权限检查能力到请求状态
    """

    # 公开端点列表（跳过认证）
    PUBLIC_PATHS = [
        "/api/auth/login",
        "/api/auth/register",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/metrics",
        "/static/",
    ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 跳过公开端点
        if self._is_public_endpoint(request):
            return await call_next(request)

        try:
            # 提取用户信息（从JWT或API Key）
            user_id = await self._extract_user_id(request)

            if user_id:
                # 注入用户ID到请求状态
                request.state.user_id = user_id

                # 检查是否是超级用户
                is_superuser = await self._check_superuser(request, user_id)
                if is_superuser:
                    request.state.is_superuser = True

                # 加载用户角色（简化版本，实际应从数据库加载）
                # await self._load_user_roles(user_id, request)

            # 处理请求
            response = await call_next(request)

            return response

        except Exception as e:
            logger.error(f"RBAC middleware error: {e}")
            # 出错时继续处理请求，让后续的路由处理
            return await call_next(request)

    def _is_public_endpoint(self, request: Request) -> bool:
        """是否公开端点"""
        path = request.url.path

        # 检查精确匹配
        if path in self.PUBLIC_PATHS:
            return True

        # 检查前缀匹配
        for public_path in self.PUBLIC_PATHS:
            if public_path.endswith("/") and path.startswith(public_path):
                return True

        return False

    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """
        从请求中提取用户ID

        支持：
        1. JWT Token (Authorization: Bearer xxx)
        2. API Key (X-API-Key: xxx)
        """
        # 1. 尝试从Authorization header提取JWT
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user_id = await self._decode_jwt(token)
            if user_id:
                return user_id

        # 2. 尝试从API Key提取
        api_key = request.headers.get("X-API-Key")
        if api_key:
            user_id = await self._validate_api_key(api_key)
            if user_id:
                return user_id

        return None

    async def _decode_jwt(self, token: str) -> Optional[str]:
        """
        解码JWT Token

        简化版本：实际应使用JWT库验证
        """
        try:
            # 这里应该使用实际的JWT验证逻辑
            # from src.service.auth_service import decode_token
            # payload = decode_token(token)
            # return payload.get("user_id")

            # 简化版本：返回None
            return None

        except Exception as e:
            logger.error(f"Failed to decode JWT: {e}")
            return None

    async def _validate_api_key(self, api_key: str) -> Optional[str]:
        """
        验证API Key

        简化版本：实际应查询数据库验证
        """
        try:
            # 这里应该查询数据库验证API Key
            # from src.service.api_key_service import validate_api_key
            # user = await validate_api_key(api_key)
            # return user.id if user else None

            # 简化版本：返回None
            return None

        except Exception as e:
            logger.error(f"Failed to validate API key: {e}")
            return None

    async def _check_superuser(self, request: Request, user_id: str) -> bool:
        """
        检查是否是超级用户

        简化版本：实际应查询数据库
        """
        try:
            # 这里应该查询数据库检查用户的is_superuser字段
            # from src.service.user_service import get_user_by_id
            # user = await get_user_by_id(user_id)
            # return user.is_superuser if user else False

            # 简化版本：返回False
            return False

        except Exception as e:
            logger.error(f"Failed to check superuser: {e}")
            return False

    async def _load_user_roles(self, user_id: str, request: Request) -> None:
        """
        加载用户角色

        简化版本：实际应从数据库加载
        """
        try:
            # 这里应该从数据库加载用户的角色
            # from src.service.rbac_service import RBACService
            # rbac_service = RBACService(get_settings())
            # user_roles = await rbac_service._get_user_roles(session, user_id)
            # request.state.user_roles = user_roles

            # 简化版本：跳过
            pass

        except Exception as e:
            logger.error(f"Failed to load user roles: {e}")


# 便捷依赖函数
async def get_request_user_id(request: Request) -> Optional[str]:
    """获取当前请求的用户ID"""
    return getattr(request.state, "user_id", None)


async def get_request_tenant_id(request: Request) -> Optional[str]:
    """获取当前请求的租户ID"""
    return getattr(request.state, "tenant_id", None)


def require_auth(request: Request) -> str:
    """
    要求认证的依赖

    用法:
        @app.get("/api/protected")
        async def protected_endpoint(user_id: str = Depends(require_auth)):
            ...
    """
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    return user_id


def require_superuser(request: Request) -> bool:
    """
    要求超级用户权限的依赖

    用法:
        @app.post("/api/admin/users")
        async def admin_endpoint(_: bool = Depends(require_superuser)):
            ...
    """
    is_superuser = getattr(request.state, "is_superuser", False)

    if not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser required"
        )

    return True
