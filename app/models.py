"""SQLAlchemy ORM 模型定义。

包含：
- ``User``：用户主表；
- ``OAuthLink``：第三方登录绑定（微信等）；
- ``Token``：登录令牌；
- ``VerifyCode``：短信/邮箱验证码；
- ``Hitem3dTask``：Hitem3D 任务及其 OSS 转存 / 原图归档状态。
"""
from __future__ import annotations

import time
from typing import List, Optional

from sqlalchemy import JSON, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _now() -> float:
    return time.time()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), unique=True, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_now)

    oauth_links: Mapped[List["OAuthLink"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class OAuthLink(Base):
    __tablename__ = "oauth_links"
    __table_args__ = (
        Index("ix_oauth_provider_uid", "provider", "uid", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    uid: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="oauth_links")


class Token(Base):
    __tablename__ = "tokens"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    expires_at: Mapped[float] = mapped_column(Float, index=True)


class VerifyCode(Base):
    __tablename__ = "verify_codes"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    code: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[float] = mapped_column(Float, index=True)


class Hitem3dTask(Base):
    __tablename__ = "hitem3d_tasks"

    task_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    state: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # Asset category: "model_3d" | "parallax" | "hogel"
    asset_type: Mapped[str] = mapped_column(String(32), default="model_3d", index=True)
    model_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumb_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    # --- OSS storage metadata ------------------------------------------------
    # ``upload_state``: pending / uploading / done / failed
    oss_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(default=None, nullable=True)
    upload_state: Mapped[str] = mapped_column(String(16), default="pending")
    upload_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Original uploaded source images (OSS keys). Stored as JSON list of strings.
    source_keys: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[float] = mapped_column(Float, default=_now, index=True)
    updated_at: Mapped[float] = mapped_column(Float, default=_now)
