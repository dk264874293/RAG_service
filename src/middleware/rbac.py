"""
RBAC权限模型定义
基于角色的访问控制
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, JSON, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Permission(str, Enum):
    """权限枚举"""
    # 文档操作
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"

    # 检索操作
    SEARCH_EXECUTE = "search:execute"
    SEARCH_ADVANCED = "search:advanced"

    # 合规检查
    COMPLIANCE_EXECUTE = "compliance:execute"

    # 用户管理
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ASSIGN_ROLE = "user:assign_role"

    # 租户管理
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"

    # 系统管理
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"


class Role(str, Enum):
    """角色枚举"""
    # 租户级别角色
    TENANT_OWNER = "tenant:owner"
    TENANT_ADMIN = "tenant:admin"
    TENANT_MEMBER = "tenant:member"

    # 系统级别角色
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_OPERATOR = "system:operator"


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    # 系统管理员 - 所有权限
    Role.SYSTEM_ADMIN: list(Permission),

    # 系统操作员 - 监控和只读
    Role.SYSTEM_OPERATOR: [
        Permission.SYSTEM_MONITOR,
        Permission.TENANT_READ,
        Permission.SEARCH_EXECUTE,
        Permission.DOCUMENT_READ,
    ],

    # 租户所有者 - 租户内所有权限
    Role.TENANT_OWNER: [
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_DELETE,
        Permission.SEARCH_EXECUTE,
        Permission.SEARCH_ADVANCED,
        Permission.COMPLIANCE_EXECUTE,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_ASSIGN_ROLE,
        Permission.TENANT_READ,
        Permission.TENANT_UPDATE,
    ],

    # 租户管理员 - 租户管理权限
    Role.TENANT_ADMIN: [
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_UPDATE,
        Permission.SEARCH_EXECUTE,
        Permission.SEARCH_ADVANCED,
        Permission.USER_READ,
        Permission.USER_UPDATE,
        Permission.USER_ASSIGN_ROLE,
        Permission.TENANT_READ,
    ],

    # 租户成员 - 基本权限
    Role.TENANT_MEMBER: [
        Permission.DOCUMENT_READ,
        Permission.SEARCH_EXECUTE,
    ],
}


class RBACUser(Base):
    """用户（扩展）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False)

    # 多租户关联
    current_tenant_id = Column(Integer, ForeignKey("tenants.id"))

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    tenant = relationship("Tenant", back_populates="users")
    roles = relationship("RBACUserRole", back_populates="user", cascade="all, delete-orphan")


class RBACRole(Base):
    """角色"""
    __tablename__ = "rbac_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text)

    # 权限
    permissions = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)


class RBACUserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role_id = Column(Integer, ForeignKey("rbac_roles.id"), nullable=False)

    # 租户级角色（可选）
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # 授予者信息
    granted_by = Column(Integer, ForeignKey("users.id"))
    granted_at = Column(DateTime, default=datetime.utcnow)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("RBACUser", back_populates="roles")
    role = relationship("RBACRole")


class ResourcePermission(Base):
    """
    资源级权限

    用于精细化的资源权限控制
    例如：特定文档的访问权限
    """
    __tablename__ = "resource_permissions"

    id = Column(Integer, primary_key=True, index=True)

    # 资源信息
    resource_type = Column(String(50), nullable=False, index=True)  # document, tenant, etc
    resource_id = Column(String(255), nullable=False, index=True)

    # 权限
    permission = Column(String(50), nullable=False)  # read, write, delete

    # 授权主体
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    role_id = Column(Integer, ForeignKey("rbac_roles.id"), nullable=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # 条件（可选，用于复杂权限规则）
    conditions = Column(JSON)  # {"status": "published", "category": "public"}

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # 权限过期时间


class AuditLog(Base):
    """
    审计日志
    记录所有敏感操作
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 操作信息
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    action = Column(String(50), nullable=False, index=True)  # create, read, update, delete
    resource_type = Column(String(50), nullable=False)  # document, user, tenant
    resource_id = Column(String(255))  # 受影响的资源ID

    # 操作结果
    success = Column(Boolean, nullable=False)
    error_message = Column(Text)

    # 上下文信息
    ip_address = Column(String(50))
    user_agent = Column(String(255))
    request_id = Column(String(50), index=True)  # 关联到请求追踪

    # 变更前后的值
    old_value = Column(JSON)
    new_value = Column(JSON)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class PermissionChecker:
    """
    权限检查器
    """

    @staticmethod
    def has_permission(
        user: RBACUser,
        permission: Permission,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> bool:
        """
        检查用户是否有权限

        Args:
            user: 用户对象
            permission: 所需权限
            resource_type: 资源类型
            resource_id: 资源ID
            tenant_id: 租户ID

        Returns:
            是否有权限
        """
        # 超级管理员有所有权限
        if user.is_superuser:
            return True

        # 检查角色权限
        user_roles = getattr(user, 'roles', [])
        if user_roles:
            for user_role in user_roles:
                role = user_role.role
                if permission in role.permissions:
                    return True

        # 检查资源级权限
        if resource_type and resource_id:
            return PermissionChecker._check_resource_permission(
                user, permission, resource_type, resource_id, tenant_id
            )

        return False

    @staticmethod
    def _check_resource_permission(
        user: RBACUser,
        permission: Permission,
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[int],
    ) -> bool:
        """检查资源级权限"""
        # 这里应该查询ResourcePermission表
        # 简化版本
        return True  # TODO: 实现实际的权限检查


def require_permission(permission: Permission, resource_type: Optional[str] = None):
    """
    权限检查装饰器

    用法:
        @require_permission(Permission.DOCUMENT_DELETE, "document")
        async def delete_document(document_id: str):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 从请求中获取用户信息
            # 这里简化了，实际应该从request.state.user获取
            # user = get_current_user()
            # if not PermissionChecker.has_permission(user, permission, resource_type):
            #     raise HTTPException(status_code=403, detail="Permission denied")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
