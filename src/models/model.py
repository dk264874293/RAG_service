"""
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 12:24:17
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 13:04:29
FilePath: /RAG_agent/src/models/model.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
"""

import sqlalchemy as sa
from flask import request
from datetime import datetime

# from flask_login import UserMixin
from sqlalchemy import (
    Float,
    Index,
    PrimaryKeyConstraint,
    String,
    exists,
    func,
    select,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column
from .base import Base
from .enums import CreatorUserRole
from .custom_types import LongText, StringUUID


class UploadFile(Base):
    __tablename__ = "upload_files"
    __table_args__ = (
        sa.PrimaryKeyConstraint("id", name="upload_file_pkey"),
        sa.Index("upload_file_tenant_idx", "tenant_id"),
    )

    # NOTE: The `id` field is generated within the application to minimize extra roundtrips
    # (especially when generating `source_url`).
    # The `server_default` serves as a fallback mechanism.
    id: Mapped[str] = mapped_column(StringUUID, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(StringUUID, nullable=False)
    storage_type: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    extension: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=True)

    # The `created_by_role` field indicates whether the file was created by an `Account` or an `EndUser`.
    # Its value is derived from the `CreatorUserRole` enumeration.
    created_by_role: Mapped[str] = mapped_column(
        String(255), nullable=False, server_default=sa.text("'account'")
    )

    # The `created_by` field stores the ID of the entity that created this upload file.
    #
    # If `created_by_role` is `ACCOUNT`, it corresponds to `Account.id`.
    # Otherwise, it corresponds to `EndUser.id`.
    created_by: Mapped[str] = mapped_column(StringUUID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # The fields `used` and `used_by` are not consistently maintained.
    #
    # When using this model in new code, ensure the following:
    #
    # 1. Set `used` to `true` when the file is utilized.
    # 2. Assign `used_by` to the corresponding `Account.id` or `EndUser.id` based on the `created_by_role`.
    # 3. Avoid relying on these fields for logic, as their values may not always be accurate.
    #
    # `used` may indicate whether the file has been utilized by another service.
    used: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )

    # `used_by` may indicate the ID of the user who utilized this file.
    used_by: Mapped[str | None] = mapped_column(StringUUID, nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(LongText, default="")

    def __init__(
        self,
        *,
        tenant_id: str,
        storage_type: str,
        key: str,
        name: str,
        size: int,
        extension: str,
        mime_type: str,
        created_by_role: CreatorUserRole,
        created_by: str,
        created_at: datetime,
        used: bool,
        used_by: str | None = None,
        used_at: datetime | None = None,
        hash: str | None = None,
        source_url: str = "",
    ):
        self.id = str(uuid.uuid4())
        self.tenant_id = tenant_id
        self.storage_type = storage_type
        self.key = key
        self.name = name
        self.size = size
        self.extension = extension
        self.mime_type = mime_type
        self.created_by_role = created_by_role.value
        self.created_by = created_by
        self.created_at = created_at
        self.used = used
        self.used_by = used_by
        self.used_at = used_at
        self.hash = hash
        self.source_url = source_url
