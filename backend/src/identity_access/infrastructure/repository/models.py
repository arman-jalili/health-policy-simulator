"""ORM model for the IdentityAccess key store (ADR-002).

Canonical: .pi/architecture/modules/identity-access.md

Table name follows the ownership rule ``identity_access_<entity>``. The model is private to
``infrastructure/repository``; migration ``0104`` is the schema authority. Only the salted hash and
salt are stored — plaintext keys never reach this table.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class ApiKeyRow(Base):
    """One API key: metadata plus the salted hash, never the plaintext."""

    __tablename__ = "identity_access_api_key"
    __table_args__ = (Index("ix_identity_access_api_key_key_hash", "key_hash"),)

    key_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    salt: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
