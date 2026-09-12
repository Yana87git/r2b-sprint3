"""モデル共通の部品。設計の正は docs/requirements/04-db.md。"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

__all__ = ["Base", "UUIDPrimaryKeyMixin", "TimestampMixin", "CreatedAtMixin"]


class UUIDPrimaryKeyMixin:
    """UUID 主キー（04: 実行IDをトレースのファイル名と共有するため連番にしない）。"""

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class CreatedAtMixin:
    """作成日時のみを持つテーブル用。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TimestampMixin(CreatedAtMixin):
    """作成・更新日時を持つテーブル用。"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
