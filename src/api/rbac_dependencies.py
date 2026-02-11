"""
RBAC依赖注入
为FastAPI路由提供权限检查和用户信息获取
"""

from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rbac import Permission
from src.service.rbac_service import RBACService
from src.api.dependencies import get_rbac_service
from src.models.engine import get_async_session_factory
from config import settings


async def get_db_session() -> AsyncSession:
    """获取数据库会话"""
    session_factory = get_async_session_factory(settings.database_url)
    async with session_factory() as session:
        yield session


async def get_current_user_id(request: Request) -> Optional[str]:
    """
    从请求中获取当前用户ID

    从JWT token中提取用户ID
    """
    # 尝试从请求状态中获取（由认证中间件注入）
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        # 尝试从Authorization header解析
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # 这里应该验证JWT token并提取user_id
            # 简化版本：返回None
            pass

    return user_id


async def get_current_tenant_id(request: Request) -> Optional[str]:
    """
    从请求中获取当前租户ID

    从租户中间件注入的上下文中获取
    """
    # 尝试从请求状态中获取（由租户中间件注入）
    tenant_id = getattr(request.state, "tenant_id", None)
    return tenant_id


def check_permission(
    permission: Permission,
    resource_type: Optional[str] = None,
    resource_id_param: Optional[str] = None,
):
    """
    权限检查依赖工厂

    用法:
        @app.get("/api/documents/{doc_id}")
        async def get_document(
            doc_id: str,
            _: bool = Depends(check_permission(Permission.DOCUMENT_READ, "document", "doc_id"))
        ):
            ...

    Args:
        permission: 所需权限
        resource_type: 资源类型
        resource_id_param: 路径参数名（用于获取resource_id）
    """
    async def dependency(
        request: Request,
        user_id: Optional[str] = Depends(get_current_user_id),
        tenant_id: Optional[str] = Depends(get_current_tenant_id),
        rbac_service: RBACService = Depends(get_rbac_service),
        session: AsyncSession = Depends(get_db_session),
    ) -> bool:
        # 未认证
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )

        # 提取resource_id
        resource_id = None
        if resource_id_param:
            resource_id = request.path_params.get(resource_id_param)

        # 检查权限
        has_perm = await rbac_service.check_permission(
            session,
            user_id=user_id,
            permission=permission,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
        )

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}"
            )

        return True

    return dependency


def require_superuser(request: Request) -> bool:
    """
    要求超级用户权限

    用法:
        @app.post("/api/admin/users")
        async def create_user(_: bool = Depends(require_superuser)):
            ...
    """
    is_superuser = getattr(request.state, "is_superuser", False)

    if not is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser required"
        )

    return True


def require_tenant_owner():
    """
    要求租户所有者权限

    用法:
        @app.delete("/api/tenant/users/{user_id}")
        async def delete_tenant_user(_: bool = Depends(require_tenant_owner())):
            ...
    """
    return check_permission(
        Permission.USER_DELETE,
        resource_type="tenant"
    )


def require_system_admin():
    """
    要求系统管理员权限

    用法:
        @app.get("/api/admin/tenants")
        async def list_tenants(_: bool = Depends(require_system_admin())):
            ...
    """
    return check_permission(
        Permission.SYSTEM_ADMIN,
        resource_type="system"
    )


# 文档操作权限装饰器
require_document_create = lambda: check_permission(Permission.DOCUMENT_CREATE, "document")
require_document_read = lambda: check_permission(Permission.DOCUMENT_READ, "document")
require_document_update = lambda: check_permission(Permission.DOCUMENT_UPDATE, "document")
require_document_delete = lambda: check_permission(Permission.DOCUMENT_DELETE, "document")

# 检索操作权限装饰器
require_search_execute = lambda: check_permission(Permission.SEARCH_EXECUTE)
require_search_advanced = lambda: check_permission(Permission.SEARCH_ADVANCED)

# 合规检查权限装饰器
require_compliance_execute = lambda: check_permission(Permission.COMPLIANCE_EXECUTE)

# 用户管理权限装饰器
require_user_create = lambda: check_permission(Permission.USER_CREATE, "user")
require_user_read = lambda: check_permission(Permission.USER_READ, "user")
require_user_update = lambda: check_permission(Permission.USER_UPDATE, "user")
require_user_delete = lambda: check_permission(Permission.USER_DELETE, "user")
require_user_assign_role = lambda: check_permission(Permission.USER_ASSIGN_ROLE, "user")

# 租户管理权限装饰器
require_tenant_read = lambda: check_permission(Permission.TENANT_READ, "tenant")
require_tenant_update = lambda: check_permission(Permission.TENANT_UPDATE, "tenant")
require_tenant_delete = lambda: check_permission(Permission.TENANT_DELETE, "tenant")

# 系统管理权限装饰器
require_system_admin = lambda: check_permission(Permission.SYSTEM_ADMIN, "system")
require_system_monitor = lambda: check_permission(Permission.SYSTEM_MONITOR, "system")
