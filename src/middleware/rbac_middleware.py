"""
RBAC中间件
在请求处理链中注入权限检查
"""

import logging
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .rbac import RBACUser, Permission, PermissionChecker

logger = logging.getLogger(__name__)


class RBACMiddleware(BaseHTTPMiddleware):
    """
    RBAC中间件

    功能：
    1. 从JWT中提取用户信息
    2. 加载用户角色
    3. 注入权限检查能力
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 跳过公开端点
        if self._is_public_endpoint(request):
            return await call_next(request)

        # 提取用户信息（从JWT）
        user = await self._extract_user_from_token(request)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # 加载用户角色
        await self._load_user_roles(user, request)

        # 注入用户到请求状态
        request.state.user = user

        # 处理请求
        response = await call_next(request)

        return response

    def _is_public_endpoint(self, request: Request) -> bool:
        """是否公开端点"""
        public_paths = [
            "/api/auth/login",
            "/api/auth/register",
            "/docs",
            "/health",
            "/metrics",
        ]
        return any(request.url.path.startswith(path) for path in public_paths)

    async def _extract_user_from_token(self, request: Request) -> Optional[RBACUser]:
        """从JWT Token提取用户"""
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return None

            if not auth_header.startswith("Bearer "):
                return None

            token = auth_header.split(" ")[1]

            # 验证JWT并提取用户ID
            # 这里简化了，实际应该使用JWT验证逻辑
            # user_id = decode_jwt(token)
            # user = await get_user(user_id)

            # 简化版本
            return None

        except Exception as e:
            logger.error(f"Failed to extract user from token: {e}")
            return None

    async def _load_user_roles(self, user: RBACUser, request: Request) -> None:
        """加载用户角色"""
        # 这里应该从数据库加载用户的角色
        # 并附加到user对象上
        # 简化版本
        pass


def get_current_user() -> Optional[RBACUser]:
    """
    获取当前请求的用户

    用法（在依赖注入中使用）:
        def get_user(request: Request) -> Optional[RBACUser]:
            return getattr(request.state, "user", None)
    """
    # 这个函数在依赖注入中使用
    # 实际实现应该在dependencies.py中
    pass


def check_permission(
    permission: Permission,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
):
    """
    权限检查依赖函数

    用法:
        @app.get("/api/documents/{doc_id}")
        async def get_document(
            doc_id: str,
            user: RBACUser = Depends(get_current_user),
            _: bool = Depends(check_permission(Permission.DOCUMENT_READ, "document", doc_id))
        ):
            ...
    """
    async def dependency(
        request: Request,
        user: Optional[RBACUser] = Depends(get_current_user),
    ) -> bool:
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # 提取resource_id（如果有）
        resource_id = request.path_params.get("id") if hasattr(request, "path_params") else None

        # 检查权限
        tenant_id = getattr(request.state, "tenant_id", None)

        has_perm = PermissionChecker.has_permission(
            user, permission, resource_type, resource_id, tenant_id
        )

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )

        return True
