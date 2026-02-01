"""
认证API测试
测试用户注册和登录功能
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app import app
from src.models import Base
from src.core.security import verify_token


# 测试数据库连接
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """
    创建测试数据库会话
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def client():
    """
    创建测试客户端
    """
    return TestClient(app)


def test_register_success(client, test_db):
    """
    测试用户注册成功
    """
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "phone": "13800138000", "password": "123456"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_phone(client, test_db):
    """
    测试手机号唯一性约束
    """
    # 第一次注册
    client.post(
        "/api/auth/register",
        json={"username": "testuser", "phone": "13800138000", "password": "123456"},
    )

    # 尝试用相同手机号再次注册
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser2", "phone": "13800138000", "password": "123456"},
    )

    assert response.status_code == 400
    assert "已被注册" in response.json()["detail"]


def test_register_short_password(client, test_db):
    """
    测试密码长度验证
    """
    response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "phone": "13800138000", "password": "123"},
    )

    assert response.status_code == 422  # Pydantic验证错误
    errors = response.json()["detail"]
    assert any("密码长度不能少于6位" in str(err) for err in errors)


def test_login_with_phone(client, test_db):
    """
    测试使用手机号登录成功
    """
    # 先注册用户
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "phone": "13900139000",
            "password": "password123",
        },
    )

    # 使用手机号登录
    response = client.post(
        "/api/auth/login/json",
        json={"username": "13900139000", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


def test_login_wrong_password(client, test_db):
    """
    测试错误密码登录失败
    """
    # 先注册用户
    client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "phone": "13700137000",
            "password": "password123",
        },
    )

    # 使用错误密码登录
    response = client.post(
        "/api/auth/login/json",
        json={"username": "13700137000", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "用户名或密码错误" in response.json()["detail"]


def test_login_nonexistent_user(client, test_db):
    """
    测试不存在的用户登录失败
    """
    response = client.post(
        "/api/auth/login/json",
        json={"username": "99999999999", "password": "password123"},
    )

    assert response.status_code == 401
    assert "用户名或密码错误" in response.json()["detail"]


def test_verify_token_success(client, test_db):
    """
    测试JWT令牌验证成功
    """
    # 注册并获取token
    register_response = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "phone": "13600136000",
            "password": "password123",
        },
    )
    token = register_response.json()["access_token"]

    # 使用token验证
    response = client.get(
        "/api/auth/verify-token", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
