"""
多租户中间件
拦截请求，提取租户信息，注入租户上下文
"""

import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.tenant import Tenant, TenantStatus
from ..models.model import User

logger = logging.getLogger(__name__)


# 租户上下文（线程本地存储）
from contextvars import ContextVar
_tenant_context: ContextVar[Optional[dict]] = ContextVar('tenant_context', default=None)


class TenantContext:
    """租户上下文"""

    def __init__(
        self,
        tenant_id: str,
        tenant: Tenant,
        user: Optional[User] = None,
    ):
        self.tenant_id = tenant_id
        self.tenant = tenant
        self.user = user

    @property
    def tenant_obj(self) -> Tenant:
        return self.tenant

    def get_quota(self, key: str, default=None):
        """获取配额"""
        return self.tenant.get_quota(key, default)

    def get_usage(self, key: str, default=0):
        """获取使用量"""
        return self.tenant.get_usage(key, default)

    def check_quota(self, quota_key: str, increment: int = 0) -> bool:
        """检查配额"""
        return self.tenant.check_quota(quota_key, increment=increment)


def get_tenant_context() -> Optional[TenantContext]:
    """获取当前请求的租户上下文"""
    context_data = _tenant_context.get()
    if context_data:
        return TenantContext(**context_data)
    return None


def get_current_tenant() -> Optional[Tenant]:
    """获取当前租户对象"""
    context = get_tenant_context()
    return context.tenant if context else None


def get_current_tenant_id() -> Optional[str]:
    """获取当前租户ID"""
    context = get_tenant_context()
    return context.tenant_id if context else None


class TenantMiddleware(BaseHTTPMiddleware):
    """
    多租户中间件

    功能：
    1. 从请求中提取租户标识
    2. 验证租户状态和权限
    3. 注入租户上下文
    4. 检查配额
    """

    # 支持的租户识别方式
    TENANT_HEADER = "X-Tenant-ID"  # HTTP头
    TENANT_QUERY_PARAM = "tenant_id"  # 查询参数
    TENANT_SUBDOMAIN = True  # 子域名模式（如 tenant.example.com）

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        # 跳过健康检查等端点
        if self._should_skip_tenant_check(request):
            return await call_next(request)

        # 提取租户ID
        tenant_id = self._extract_tenant_id(request)

        if not tenant_id:
            # 公开端点（如注册、登录）
            if self._is_public_endpoint(request):
                return await call_next(request)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant ID not provided"
            )

        # 获取租户信息
        tenant = await self._get_tenant(request, tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id} not found"
            )

        # 检查租户状态
        if not tenant.is_active:
            if tenant.is_suspended:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tenant {tenant_id} is suspended"
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant {tenant_id} is not active"
            )

        # 注入租户上下文
        await self._inject_tenant_context(request, tenant)

        # 记录API调用（用于配额检查）
        await self._record_api_call(request, tenant)

        # 处理请求
        response = await call_next(request)

        # 添加租户头到响应
        response.headers["X-Tenant-ID"] = tenant_id

        return response

    def _should_skip_tenant_check(self, request: Request) -> bool:
        """是否跳过租户检查"""
        skip_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico",
            "/static",
        ]

        return any(request.url.path.startswith(path) for path in skip_paths)

    def _is_public_endpoint(self, request: Request) -> bool:
        """是否公开端点"""
        public_paths = [
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/forgot-password",
            "/api/public",
        ]

        return any(request.url.path.startswith(path) for path in public_paths)

    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """提取租户ID"""
        # 优先级: HTTP头 > 子域名 > 查询参数

        # 1. HTTP头
        tenant_id = request.headers.get(self.TENANT_HEADER)
        if tenant_id:
            return tenant_id

        # 2. 子域名（如 tenant.example.com）
        if self.TENANT_SUBDOMAIN:
            host = request.headers.get("host", "")
            if "." in host:
                subdomain = host.split(".")[0]
                if subdomain and subdomain not in ["www", "api", "app"]:
                    return subdomain

        # 3. 查询参数
        if hasattr(request, "query_params"):
            tenant_id = request.query_params.get(self.TENANT_QUERY_PARAM)
            if tenant_id:
                return tenant_id

        return None

    async def _get_tenant(self, request: Request, tenant_id: str) -> Optional[Tenant]:
        """获取租户对象"""
        # 从数据库获取
        # 这里需要依赖注入的数据库session
        # 简化版本，实际应该从request.state中获取
        return None

    async def _inject_tenant_context(self, request: Request, tenant: Tenant) -> None:
        """注入租户上下文到ContextVar"""
        context_data = {
            "tenant_id": tenant.tenant_id,
            "tenant": tenant,
            "user": getattr(request.state, "user", None),
        }
        _tenant_context.set(context_data)

        # 同时也注入到request.state
        request.state.tenant = tenant
        request.state.tenant_id = tenant.tenant_id

        logger.debug(f"Injected tenant context: {tenant.tenant_id}")

    async def _record_api_call(self, request: Request, tenant: Tenant) -> None:
        """记录API调用（用于配额检查）"""
        # 异步记录，不阻塞请求
        # 可以使用消息队列或后台任务
        tenant.increment_usage("api_calls_today")
        # 这里简化了，实际应该使用更精确的计数方式


async def require_tenant(request: Request) -> Tenant:
    """
    依赖注入函数：要求请求必须有有效的租户

    用法:
        @app.get("/api/documents")
        async def list_documents(request: Request, tenant: Tenant = Depends(require_tenant)):
            ...
    """
    tenant = getattr(request.state, "tenant")
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context not found"
        )
    return tenant


async def require_active_tenant(request: Request) -> Tenant:
    """
    依赖注入函数：要求请求必须有激活的租户
    """
    tenant = await require_tenant(request)
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active"
        )
    return tenant


class TenantService:
    """租户服务"""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory

    async def create_tenant(
        self,
        tenant_id: str,
        tenant_name: str,
        plan: str = "free",
        contact_email: str = None,
        quotas: Optional[dict] = None,
    ) -> Tenant:
        """创建新租户"""
        async with self.db_session_factory() as session:
            # 检查租户ID是否已存在
            existing = await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            if existing.scalar_one_or_none():
                raise ValueError(f"Tenant ID {tenant_id} already exists")

            # 创建租户
            tenant = Tenant(
                tenant_id=tenant_id,
                tenant_name=tenant_name,
                tenant_slug=tenant_id.lower().replace("-", ""),
                contact_email=contact_email or f"{tenant_id}@example.com",
                plan=plan,
                quotas=quotas or {},
                usage_stats={},
                settings={},
            )

            session.add(tenant)
            await session.commit()
            await session.refresh(tenant)

            logger.info(f"Created tenant: {tenant_id}")
            return tenant

    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        async with self.db_session_factory() as session:
            result = await session.execute(
                select(Tenant).where(
                    Tenant.tenant_id == tenant_id,
                    Tenant.status == TenantStatus.ACTIVE.value
                )
            )
            return result.scalar_one_or_none()

    async def update_tenant_usage(
        self,
        tenant_id: str,
        resource_type: str,
        action: str,
        quantity: int = 1,
        metadata: Optional[dict] = None,
    ) -> None:
        """更新租户使用量"""
        async with self.db_session_factory() as session:
            # 获取租户
            result = await session.execute(
                select(Tenant).where(Tenant.tenant_id == tenant_id)
            )
            tenant = result.scalar_one_or_none()

            if not tenant:
                logger.warning(f"Tenant not found: {tenant_id}")
                return

            # 更新使用量
            if resource_type == "api_call":
                tenant.increment_usage("api_calls_today", quantity)
            elif resource_type == "document":
                tenant.increment_usage("document_count", quantity)
            elif resource_type == "storage":
                tenant.increment_usage("storage_used_mb", quantity)

            # 创建使用日志
            usage_log = TenantUsageLog(
                tenant_id=tenant.id,
                resource_type=resource_type,
                action=action,
                quantity=quantity,
                metadata=metadata,
            )

            session.add(usage_log)
            await session.commit()

    async def check_tenant_quota(
        self,
        tenant_id: str,
        quota_key: str,
        increment: int = 0,
    ) -> bool:
        """检查租户配额"""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False

        return tenant.check_quota(quota_key, increment=increment)
