"""
数据库初始化脚本
创建所有数据库表并初始化基础数据
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

import config
from src.models import Base
from src.core.security import get_password_hash


async def create_database():
    """
    创建数据库（如果不存在）
    """
    engine = create_async_engine(
        config.settings.database_url.replace("/rag_service", "/mysql"), echo=False
    )

    async with engine.begin() as conn:
        # 创建数据库
        await conn.execute(
            text(
                "CREATE DATABASE IF NOT EXISTS rag_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )

    await engine.dispose()
    print("Database created/verified successfully")


async def create_tables():
    """
    创建所有表
    """
    engine = create_async_engine(
        config.settings.database_url,
        echo=False,
        pool_size=config.settings.database_pool_size,
        max_overflow=config.settings.database_max_overflow,
    )

    async with engine.begin() as conn:
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("Tables created successfully")


async def create_admin_user():
    """
    创建初始管理员用户（可选）
    如果不存在admin用户则创建
    """
    from src.models.user import User

    engine = create_async_engine(config.settings.database_url, echo=False)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            # 检查是否已存在admin用户
            result = await session.execute(
                text("SELECT * FROM users WHERE phone = :phone"), {"phone": "admin"}
            )
            admin_exists = result.fetchone()

            if not admin_exists:
                # 创建admin用户
                admin_user = User(
                    username="admin",
                    phone="admin",
                    password=get_password_hash("admin123"),
                )
                session.add(admin_user)
                print("Admin user created (phone: admin, password: admin123)")
            else:
                print("Admin user already exists")

    await engine.dispose()


async def main():
    """
    主函数：执行所有初始化步骤
    """
    print("Starting database initialization...")
    print("-" * 50)

    # 1. 创建数据库
    await create_database()
    print()

    # 2. 创建表
    await create_tables()
    print()

    # 3. 创建管理员用户（可选）
    try:
        await create_admin_user()
    except Exception as e:
        print(f"Warning: Could not create admin user: {e}")

    print("-" * 50)
    print("Database initialization completed!")


if __name__ == "__main__":
    asyncio.run(main())
