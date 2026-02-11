"""
RBAC权限服务
提供权限检查、角色管理、审计日志等功能
"""

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from src.models.rbac import (
    RBACRole, RBACUserRole, ResourcePermission, AuditLog,
    Permission, RoleType, ROLE_PERMISSIONS
)

if TYPE_CHECKING:
    from config import Settings

logger = logging.getLogger(__name__)


class RBACService:
    """
    RBAC权限服务

    功能:
    1. 权限检查
    2. 角色管理
    3. 资源级权限控制
    4. 审计日志
    """

    def __init__(self, config: Any):
        """
        初始化RBAC服务

        Args:
            config: 配置对象
        """
        self.config = config
        self.enable_rbac = getattr(config, "enable_rbac", True)
        self.enable_audit_log = getattr(config, "enable_audit_log", True)

    async def check_permission(
        self,
        session: AsyncSession,
        user_id: str,
        permission: Permission,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        检查用户是否有权限

        Args:
            session: 数据库会话
            user_id: 用户ID
            permission: 所需权限
            resource_type: 资源类型
            resource_id: 资源ID
            tenant_id: 租户ID

        Returns:
            是否有权限
        """
        if not self.enable_rbac:
            return True

        # 1. 获取用户的所有角色
        user_roles = await self._get_user_roles(session, user_id, tenant_id)

        # 2. 检查角色权限
        for user_role in user_roles:
            role = user_role.role
            if permission.value in role.get("permissions", []):
                # 记录审计日志
                await self._log_permission_check(
                    session, user_id, permission, resource_type, resource_id, tenant_id, True
                )
                return True

        # 3. 检查资源级权限
        if resource_type and resource_id:
            has_resource_perm = await self._check_resource_permission(
                session, user_id, permission, resource_type, resource_id, tenant_id
            )
            if has_resource_perm:
                await self._log_permission_check(
                    session, user_id, permission, resource_type, resource_id, tenant_id, True
                )
                return True

        # 记录拒绝日志
        await self._log_permission_check(
            session, user_id, permission, resource_type, resource_id, tenant_id, False
        )

        return False

    async def _get_user_roles(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取用户的所有角色"""
        # 构建查询
        query = (
            select(RBACUserRole, RBACRole)
            .join(RBACRole, RBACUserRole.role_id == RBACRole.id)
            .where(RBACUserRole.user_id == user_id)
        )

        # 租户级角色过滤
        if tenant_id:
            query = query.where(
                or_(
                    RBACUserRole.tenant_id == tenant_id,
                    RBACUserRole.tenant_id.is_(None),  # 系统级角色
                )
            )

        result = await session.execute(query)
        user_roles = []

        for user_role, role in result.all():
            user_roles.append({
                "id": str(user_role.id),
                "role_id": str(user_role.role_id),
                "tenant_id": user_role.tenant_id,
                "role": {
                    "id": str(role.id),
                    "name": role.name,
                    "permissions": role.permissions,
                    "role_type": role.role_type,
                }
            })

        return user_roles

    async def _check_resource_permission(
        self,
        session: AsyncSession,
        user_id: str,
        permission: Permission,
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """检查资源级权限"""
        # 构建查询
        conditions = [
            ResourcePermission.resource_type == resource_type,
            ResourcePermission.resource_id == resource_id,
            ResourcePermission.permission == permission.value,
            or_(
                ResourcePermission.user_id == user_id,
                ResourcePermission.user_id.is_(None),  # 公开权限
            )
        ]

        # 租户隔离
        if tenant_id:
            conditions.append(
                or_(
                    ResourcePermission.tenant_id == tenant_id,
                    ResourcePermission.tenant_id.is_(None),
                )
            )

        # 检查权限是否过期
        conditions.append(
            or_(
                ResourcePermission.expires_at.is_(None),
                ResourcePermission.expires_at > datetime.utcnow(),
            )
        )

        query = select(ResourcePermission).where(and_(*conditions))
        result = await session.execute(query)
        return result.first() is not None

    async def assign_role(
        self,
        session: AsyncSession,
        user_id: str,
        role_id: str,
        tenant_id: Optional[str] = None,
        granted_by: Optional[str] = None,
    ) -> RBACUserRole:
        """
        为用户分配角色

        Args:
            session: 数据库会话
            user_id: 用户ID
            role_id: 角色ID
            tenant_id: 租户ID
            granted_by: 授予者ID

        Returns:
            用户角色关联对象
        """
        # 检查是否已存在
        query = select(RBACUserRole).where(
            and_(
                RBACUserRole.user_id == user_id,
                RBACUserRole.role_id == role_id,
                RBACUserRole.tenant_id == tenant_id if tenant_id else RBACUserRole.tenant_id.is_(None)
            )
        )
        result = await session.execute(query)
        existing = result.first()

        if existing:
            logger.warning(f"User {user_id} already has role {role_id}")
            return existing[0]

        # 创建新关联
        user_role = RBACUserRole(
            id=str(uuid4()),
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            granted_by=granted_by,
        )

        session.add(user_role)
        await session.flush()

        # 记录审计日志
        await self._create_audit_log(
            session,
            user_id=granted_by or user_id,
            action="assign_role",
            resource_type="user_role",
            resource_id=str(user_role.id),
            tenant_id=tenant_id,
            success=True,
            new_value={"user_id": user_id, "role_id": role_id, "tenant_id": tenant_id},
        )

        logger.info(f"Assigned role {role_id} to user {user_id}")
        return user_role

    async def revoke_role(
        self,
        session: AsyncSession,
        user_id: str,
        role_id: str,
        tenant_id: Optional[str] = None,
        revoked_by: Optional[str] = None,
    ) -> bool:
        """
        撤销用户角色

        Args:
            session: 数据库会话
            user_id: 用户ID
            role_id: 角色ID
            tenant_id: 租户ID
            revoked_by: 操作者ID

        Returns:
            是否成功
        """
        # 查找用户角色
        query = select(RBACUserRole).where(
            and_(
                RBACUserRole.user_id == user_id,
                RBACUserRole.role_id == role_id,
                RBACUserRole.tenant_id == tenant_id if tenant_id else RBACUserRole.tenant_id.is_(None)
            )
        )
        result = await session.execute(query)
        user_role = result.first()

        if not user_role:
            logger.warning(f"User {user_id} does not have role {role_id}")
            return False

        # 记录审计日志
        await self._create_audit_log(
            session,
            user_id=revoked_by or user_id,
            action="revoke_role",
            resource_type="user_role",
            resource_id=str(user_role[0].id),
            tenant_id=tenant_id,
            success=True,
            old_value={"user_id": user_id, "role_id": role_id, "tenant_id": tenant_id},
        )

        # 删除
        await session.delete(user_role[0])

        logger.info(f"Revoked role {role_id} from user {user_id}")
        return True

    async def grant_resource_permission(
        self,
        session: AsyncSession,
        resource_type: str,
        resource_id: str,
        permission: str,
        user_id: Optional[str] = None,
        role_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        granted_by: Optional[str] = None,
    ) -> ResourcePermission:
        """
        授予资源级权限

        Args:
            session: 数据库会话
            resource_type: 资源类型
            resource_id: 资源ID
            permission: 权限
            user_id: 用户ID
            role_id: 角色ID
            tenant_id: 租户ID
            conditions: 权限条件
            expires_at: 过期时间
            granted_by: 授予者ID

        Returns:
            资源权限对象
        """
        resource_perm = ResourcePermission(
            id=str(uuid4()),
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            conditions=conditions,
            expires_at=expires_at,
        )

        session.add(resource_perm)
        await session.flush()

        # 记录审计日志
        await self._create_audit_log(
            session,
            user_id=granted_by or user_id,
            action="grant_permission",
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id,
            success=True,
            new_value={
                "permission": permission,
                "user_id": user_id,
                "role_id": role_id,
                "conditions": conditions,
            },
        )

        logger.info(f"Granted {permission} on {resource_type}:{resource_id} to user {user_id}")
        return resource_perm

    async def _create_audit_log(
        self,
        session: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """创建审计日志"""
        if not self.enable_audit_log:
            return None

        audit_log = AuditLog(
            id=str(uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            old_value=old_value,
            new_value=new_value,
        )

        session.add(audit_log)
        await session.flush()

        return audit_log

    async def _log_permission_check(
        self,
        session: AsyncSession,
        user_id: str,
        permission: Permission,
        resource_type: Optional[str],
        resource_id: Optional[str],
        tenant_id: Optional[str],
        granted: bool,
    ):
        """记录权限检查（仅记录拒绝）"""
        if not self.enable_audit_log or granted:
            return

        await self._create_audit_log(
            session,
            user_id=user_id,
            action="permission_denied",
            resource_type=resource_type or "unknown",
            resource_id=resource_id,
            tenant_id=tenant_id,
            success=False,
            error_message=f"Permission denied: {permission.value}",
            new_value={"permission": permission.value},
        )

    async def get_audit_logs(
        self,
        session: AsyncSession,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        查询审计日志

        Args:
            session: 数据库会话
            user_id: 用户ID
            tenant_id: 租户ID
            action: 操作类型
            resource_type: 资源类型
            limit: 返回数量
            offset: 偏移量

        Returns:
            审计日志列表
        """
        query = select(AuditLog)

        # 过滤条件
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if tenant_id:
            conditions.append(AuditLog.tenant_id == tenant_id)
        if action:
            conditions.append(AuditLog.action == action)
        if resource_type:
            conditions.append(AuditLog.resource_type == resource_type)

        if conditions:
            query = query.where(and_(*conditions))

        # 排序和分页
        query = query.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(query)
        return result.scalars().all()
