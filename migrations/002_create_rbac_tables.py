"""
数据库迁移脚本: 创建RBAC表
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.models.engine import get_async_engine
from src.models.base import Base
from src.models.rbac import RBACRole, RBACUserRole, ResourcePermission, AuditLog
from config import settings


async def migrate():
    """执行迁移"""
    engine = get_async_engine(settings.database_url)

    print("Starting RBAC tables migration...")

    async with engine.begin() as conn:
        # 创建表
        print("Creating RBAC tables...")

        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                RBACRole.__table__,
                RBACUserRole.__table__,
                ResourcePermission.__table__,
                AuditLog.__table__,
            ]
        )

        print("✓ RBAC tables created successfully")
        print("  - rbac_roles")
        print("  - user_roles")
        print("  - resource_permissions")
        print("  - audit_logs")

        # 创建索引
        print("Creating indexes...")

        # 角色表索引
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_rbac_role_name ON rbac_roles (name)"
        ))
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS rbac_role_name_unique ON rbac_roles (name)"
        ))

        # 用户角色关联表索引
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_user_role_user ON user_roles (user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_user_role_role ON user_roles (role_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_user_role_tenant ON user_roles (tenant_id)"
        ))

        # 资源权限表索引
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_resource_perm_resource ON resource_permissions (resource_type, resource_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_resource_perm_user ON resource_permissions (user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_resource_perm_role ON resource_permissions (role_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_resource_perm_tenant ON resource_permissions (tenant_id)"
        ))

        # 审计日志表索引
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_logs (user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_tenant ON audit_logs (tenant_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_logs (action)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_request ON audit_logs (request_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_logs (created_at)"
        ))

        print("✓ Indexes created successfully")

    print("RBAC tables migration completed!")


async def rollback():
    """回滚迁移"""
    engine = get_async_engine(settings.database_url)

    print("Rolling back RBAC tables...")

    async with engine.begin() as conn:
        # 删除表（注意顺序：先删有外键的表）
        await conn.execute(text("DROP TABLE IF EXISTS audit_logs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS resource_permissions CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS user_roles CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS rbac_roles CASCADE"))

        print("✓ RBAC tables dropped successfully")

    print("Rollback completed!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RBAC tables migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")
    args = parser.parse_args()

    if args.rollback:
        asyncio.run(rollback())
    else:
        asyncio.run(migrate())
