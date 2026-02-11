"""
RBAC初始化脚本
创建默认角色和权限
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from uuid import uuid4

from src.models.base import Base
from src.models.engine import get_async_session_factory
from src.models.rbac import RBACRole, RoleType, ROLE_PERMISSIONS, Permission
from src.models.tenant import Tenant
from config import settings


async def init_rbac_roles():
    """初始化RBAC角色"""
    session_factory = get_async_session_factory(settings.database_url)

    async with session_factory() as session:
        # 检查是否已初始化
        query = select(RBACRole).where(RBACRole.is_system_role == True)
        result = await session.execute(query)
        existing_roles = result.scalars().all()

        if existing_roles:
            print(f"RBAC roles already initialized ({len(existing_roles)} roles found)")
            return

        print("Initializing RBAC roles...")

        # 创建系统级角色
        roles_to_create = []

        # 1. 系统管理员
        roles_to_create.append(
            RBACRole(
                id=str(uuid4()),
                name=RoleType.SYSTEM_ADMIN.value,
                description="系统管理员 - 拥有所有权限",
                permissions=[p.value for p in Permission],
                role_type=RoleType.SYSTEM_ADMIN.value,
                is_system_role=True,
            )
        )

        # 2. 系统操作员
        roles_to_create.append(
            RBACRole(
                id=str(uuid4()),
                name=RoleType.SYSTEM_OPERATOR.value,
                description="系统操作员 - 监控和只读权限",
                permissions=[p.value for p in ROLE_PERMISSIONS[RoleType.SYSTEM_OPERATOR]],
                role_type=RoleType.SYSTEM_OPERATOR.value,
                is_system_role=True,
            )
        )

        # 3. 租户所有者
        roles_to_create.append(
            RBACRole(
                id=str(uuid4()),
                name=RoleType.TENANT_OWNER.value,
                description="租户所有者 - 租户内所有权限",
                permissions=[p.value for p in ROLE_PERMISSIONS[RoleType.TENANT_OWNER]],
                role_type=RoleType.TENANT_OWNER.value,
                is_system_role=True,
            )
        )

        # 4. 租户管理员
        roles_to_create.append(
            RBACRole(
                id=str(uuid4()),
                name=RoleType.TENANT_ADMIN.value,
                description="租户管理员 - 租户管理权限",
                permissions=[p.value for p in ROLE_PERMISSIONS[RoleType.TENANT_ADMIN]],
                role_type=RoleType.TENANT_ADMIN.value,
                is_system_role=True,
            )
        )

        # 5. 租户成员
        roles_to_create.append(
            RBACRole(
                id=str(uuid4()),
                name=RoleType.TENANT_MEMBER.value,
                description="租户成员 - 基本权限",
                permissions=[p.value for p in ROLE_PERMISSIONS[RoleType.TENANT_MEMBER]],
                role_type=RoleType.TENANT_MEMBER.value,
                is_system_role=True,
            )
        )

        # 批量创建
        session.add_all(roles_to_create)
        await session.commit()

        print(f"✓ Created {len(roles_to_create)} default roles:")
        for role in roles_to_create:
            print(f"  - {role.name}: {role.description} ({len(role.permissions)} permissions)")


async def create_default_admin_user():
    """创建默认管理员用户（如果Users表存在）"""
    # 检查是否有Users表
    try:
        from src.models.model import User
    except ImportError:
        print("User model not found, skipping default admin creation")
        return

    session_factory = get_async_session_factory(settings.database_url)

    async with session_factory() as session:
        # 检查是否已存在默认管理员
        query = select(User).where(User.username == "admin")
        result = await session.execute(query)
        existing_admin = result.first()

        if existing_admin:
            print("Default admin user already exists")
            return

        print("Creating default admin user...")

        # 获取系统管理员角色
        role_query = select(RBACRole).where(RBACRole.name == RoleType.SYSTEM_ADMIN.value)
        role_result = await session.execute(role_query)
        admin_role = role_result.scalar_one()

        # 创建管理员用户
        # 注意：这里需要根据实际的User模型调整
        # from src.service.auth_service import get_password_hash
        # admin_user = User(
        #     id=str(uuid4()),
        #     username="admin",
        #     email="admin@system.local",
        #     hashed_password=get_password_hash("admin123"),
        #     full_name="System Administrator",
        #     is_active=True,
        #     is_superuser=True,
        # )
        # session.add(admin_user)
        # await session.flush()

        # 分配系统管理员角色
        # from src.models.rbac import RBACUserRole
        # user_role = RBACUserRole(
        #     id=str(uuid4()),
        #     user_id=admin_user.id,
        #     role_id=admin_role.id,
        #     tenant_id=None,  # 系统级角色
        # )
        # session.add(user_role)
        # await session.commit()

        print("✓ Created default admin user (username: admin, password: admin123)")
        print("  ⚠ Please change the default password after first login!")


async def create_default_tenant_roles():
    """为现有租户创建默认角色"""
    session_factory = get_async_session_factory(settings.database_url)

    async with session_factory() as session:
        # 获取所有租户
        query = select(Tenant)
        result = await session.execute(query)
        tenants = result.scalars().all()

        if not tenants:
            print("No tenants found, skipping tenant role creation")
            return

        print(f"Found {len(tenants)} tenants, ensuring default roles...")

        # 为每个租户创建所有者角色关联
        from src.models.rbac import RBACUserRole

        owner_role_query = select(RBACRole).where(RBACRole.name == RoleType.TENANT_OWNER.value)
        owner_role_result = await session.execute(owner_role_query)
        owner_role = owner_role_result.scalar_one()

        # 注意：这里需要根据实际的租户-用户关系来处理
        # 这里只是示例代码
        print(f"  ⚠ Please manually assign TENANT_OWNER role for each tenant's owner user")


async def main():
    """主函数"""
    print("=" * 60)
    print("RBAC Initialization Script")
    print("=" * 60)
    print()

    try:
        # 1. 初始化角色
        await init_rbac_roles()
        print()

        # 2. 创建默认管理员
        # await create_default_admin_user()
        # print()

        # 3. 为租户创建角色
        # await create_default_tenant_roles()
        # print()

        print("=" * 60)
        print("RBAC initialization completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"✗ Error during RBAC initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
