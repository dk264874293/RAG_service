"""
多租户模型定义
支持租户隔离、配额管理和计费
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TenantStatus(str, Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class TenantPlan(str, Enum):
    """租户套餐"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Tenant(Base):
    """
    租户模型

    支持多租户数据隔离、资源配额、计费等
    """
    __tablename__ = "tenants"

    # 主键
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 基本信息
    tenant_id = Column(String(50), unique=True, nullable=False, index=True)  # 租户ID，用于URL和数据隔离
    tenant_name = Column(String(100), nullable=False)  # 租户名称
    tenant_slug = Column(String(100), unique=True, nullable=False, index=True)  # URL友好的标识符

    # 联系信息
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50))

    # 状态和套餐
    status = Column(String(20), default=TenantStatus.ACTIVE.value, nullable=False, index=True)
    plan = Column(String(50), default=TenantPlan.FREE.value, nullable=False)

    # 配额配置
    quotas = Column(JSON, nullable=False)  # JSON格式的配额配置
    # 示例:
    # {
    #     "max_documents": 1000,
    #     "max_storage_mb": 5120,
    #     "max_api_calls_per_day": 10000,
    #     "max_users": 5,
    #     "enable_advanced_features": false
    # }

    # 使用统计
    usage_stats = Column(JSON, nullable=False)  # JSON格式的使用统计
    # 示例:
    # {
    #     "document_count": 150,
    #     "storage_used_mb": 256,
    #     "api_calls_today": 2340,
    #     "user_count": 3
    # }

    # 配置（租户级配置覆盖）
    settings = Column(JSON, nullable=False)
    # 示例:
    # {
    #     "faiss_index_type": "flat",
    #     "enable_reranker": true,
    #     "custom_branding": false
    # }

    # 计费相关
    billing_email = Column(String(255))
    billing_address = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    suspended_at = Column(DateTime)  # 暂停时间
    deleted_at = Column(DateTime)  # 软删除时间

    # 关系
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, tenant_id={self.tenant_id}, name={self.tenant_name})>"

    @property
    def is_active(self) -> bool:
        """是否激活状态"""
        return self.status == TenantStatus.ACTIVE.value

    @property
    def is_suspended(self) -> bool:
        """是否暂停状态"""
        return self.status == TenantStatus.SUSPENDED.value

    def get_quota(self, key: str, default: Any = None) -> Any:
        """获取配额值"""
        if self.quotas:
            return self.quotas.get(key, default)
        return default

    def set_quota(self, key: str, value: Any) -> None:
        """设置配额值"""
        if self.quotas is None:
            self.quotas = {}
        self.quotas[key] = value

    def get_usage(self, key: str, default: Any = 0) -> Any:
        """获取使用量"""
        if self.usage_stats:
            return self.usage_stats.get(key, default)
        return default

    def increment_usage(self, key: str, amount: int = 1) -> None:
        """增加使用量"""
        if self.usage_stats is None:
            self.usage_stats = {}
        self.usage_stats[key] = self.get_usage(key) + amount

    def check_quota(self, quota_key: str, usage_key: Optional[str] = None, increment: int = 0) -> bool:
        """
        检查配额是否足够

        Args:
            quota_key: 配额键名
            usage_key: 使用量键名（默认与quota_key相同）
            increment: 预期增加量

        Returns:
            是否在配额范围内
        """
        if usage_key is None:
            usage_key = quota_key

        quota = self.get_quota(quota_key, float('inf'))
        usage = self.get_usage(usage_key, 0)

        return (usage + increment) <= quota

    def get_plan_limits(self) -> Dict[str, Any]:
        """获取套餐默认配额"""
        plan_limits = {
            TenantPlan.FREE: {
                "max_documents": 100,
                "max_storage_mb": 512,
                "max_api_calls_per_day": 1000,
                "max_users": 1,
                "enable_advanced_features": False,
                "enable_bm25": False,
                "enable_reranker": False,
            },
            TenantPlan.BASIC: {
                "max_documents": 1000,
                "max_storage_mb": 5120,
                "max_api_calls_per_day": 10000,
                "max_users": 5,
                "enable_advanced_features": True,
                "enable_bm25": True,
                "enable_reranker": True,
            },
            TenantPlan.PROFESSIONAL: {
                "max_documents": 10000,
                "max_storage_mb": 51200,
                "max_api_calls_per_day": 100000,
                "max_users": 20,
                "enable_advanced_features": True,
                "enable_bm25": True,
                "enable_reranker": True,
                "enable_generational_index": True,
            },
            TenantPlan.ENTERPRISE: {
                "max_documents": -1,  # 无限制
                "max_storage_mb": -1,  # 无限制
                "max_api_calls_per_day": -1,  # 无限制
                "max_users": -1,  # 无限制
                "enable_advanced_features": True,
                "enable_bm25": True,
                "enable_reranker": True,
                "enable_generational_index": True,
                "custom_support": True,
            },
        }
        return plan_limits.get(self.plan, {})


class UserTenant(Base):
    """用户-租户关联表"""
    __tablename__ = "user_tenants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # 角色和权限
    role = Column(String(50), default="member")  # owner, admin, member
    permissions = Column(JSON)  # 租户级别的权限

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)
    invited_at = Column(DateTime, default=datetime.utcnow)
    joined_at = Column(DateTime)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TenantUsageLog(Base):
    """租户使用量日志（用于计费和分析）"""
    __tablename__ = "tenant_usage_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

    # 使用类型
    resource_type = Column(String(50), nullable=False)  # api_call, storage, document, user
    action = Column(String(50), nullable=False)  # create, read, update, delete
    quantity = Column(Integer, default=1, nullable=False)  # 数量变化

    # 元数据
    metadata = Column(JSON)  # 额外信息，如API端点、文档类型等

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
