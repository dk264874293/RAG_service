"""
RBAC权限模型定义
基于角色的访问控制 - 集成到现有模型系统
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from .custom_types import StringUUID


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


class RoleType(str, Enum):
    """角色类型枚举"""
    # 租户级别角色
    TENANT_OWNER = "tenant:owner"
    TENANT_ADMIN = "tenant:admin"
    TENANT_MEMBER = "tenant:member"

    # 系统级别角色
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_OPERATOR = "system:operator"


# 角色权限映射
ROLE_PERMISSIONS: Dict[RoleType, List[Permission]] = {
    # 系统管理员 - 所有权限
    RoleType.SYSTEM_ADMIN: list(Permission),

    # 系统操作员 - 监控和只读
    RoleType.SYSTEM_OPERATOR: [
        Permission.SYSTEM_MONITOR,
        Permission.TENANT_READ,
        Permission.SEARCH_EXECUTE,
        Permission.DOCUMENT_READ,
    ],

    # 租户所有者 - 租户内所有权限
    RoleType.TENANT_OWNER: [
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
    RoleType.TENANT_ADMIN: [
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
    RoleType.TENANT_MEMBER: [
        Permission.DOCUMENT_READ,
        Permission.SEARCH_EXECUTE,
    ],
}


class RBACRole(Base):
    """角色表"""
    __tablename__ = "rbac_roles"

    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="rbac_role_pkey"),
        sa.Index("rbac_role_name_idx", "name"),
        sa.UniqueConstraint("name", name="rbac_role_name_unique"),
    )

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # 权限列表 (JSON格式存储)
    permissions: Mapped[Dict[str, Any]] = mapped_column(sa.JSON, nullable=False, default=list)

    # 角色类型 (租户级/系统级)
    role_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    is_system_role: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.current_timestamp(),
        onupdate=sa.func.current_timestamp()
    )

    # 关系
    user_roles = relationship("RBACUserRole", back_populates="role", cascade="all, delete-orphan")


class RBACUserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"

    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="user_role_pkey"),
        sa.Index("user_role_user_idx", "user_id"),
        sa.Index("user_role_role_idx", "role_id"),
        sa.Index("user_role_tenant_idx", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(StringUUID, nullable=False, index=True)

    # 租户级角色（可选，用于多租户隔离）
    tenant_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True, index=True)

    # 授予者信息
    granted_by: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True)
    granted_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()
    )

    # 关系
    role = relationship("RBACRole", back_populates="user_roles")


class ResourcePermission(Base):
    """
    资源级权限

    用于精细化的资源权限控制
    例如：特定文档的访问权限
    """
    __tablename__ = "resource_permissions"

    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="resource_permission_pkey"),
        sa.Index("resource_perm_resource_idx", "resource_type", "resource_id"),
        sa.Index("resource_perm_user_idx", "user_id"),
        sa.Index("resource_perm_role_idx", "role_id"),
        sa.Index("resource_perm_tenant_idx", "tenant_id"),
    )

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)

    # 资源信息
    resource_type: Mapped[str] = mapped_column(sa.String(50), nullable=False, index=True)  # document, tenant, etc
    resource_id: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)

    # 权限
    permission: Mapped[str] = mapped_column(sa.String(50), nullable=False)  # read, write, delete

    # 授权主体
    user_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True, index=True)
    role_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True, index=True)

    # 条件（可选，用于复杂权限规则）
    conditions: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)  # {"status": "published", "category": "public"}

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.current_timestamp()
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)  # 权限过期时间


class AuditLog(Base):
    """
    审计日志
    记录所有敏感操作
    """
    __tablename__ = "audit_logs"

    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="audit_log_pkey"),
        sa.Index("audit_log_user_idx", "user_id"),
        sa.Index("audit_log_tenant_idx", "tenant_id"),
        sa.Index("audit_log_action_idx", "action"),
        sa.Index("audit_log_request_idx", "request_id"),
        sa.Index("audit_log_created_idx", "created_at"),
    )

    id: Mapped[str] = mapped_column(StringUUID, primary_key=True)

    # 操作信息
    user_id: Mapped[str] = mapped_column(StringUUID, nullable=False, index=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(StringUUID, nullable=True, index=True)

    action: Mapped[str] = mapped_column(sa.String(50), nullable=False, index=True)  # create, read, update, delete
    resource_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)  # document, user, tenant
    resource_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)  # 受影响的资源ID

    # 操作结果
    success: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)

    # 上下文信息
    ip_address: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True, index=True)  # 关联到请求追踪

    # 变更前后的值
    old_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    new_value: Mapped[Optional[Dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=sa.func.current_timestamp(), index=True
    )
