"""item_rows — 品目リスト案の行（04）。"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

# 表示名と識別子の対応は 04「行の分類の呼び方」が正
CLASSIFICATIONS = ("needs_confirmation", "low_confidence", "high_confidence")
CHECK_STATES = ("unchecked", "checked")


class ItemRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "item_rows"

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False
    )
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[str] = mapped_column(String(32), nullable=False)
    # 人が読み取り元を最初に開いた時刻。一括確認の抜き取り判定に使う（機械の照合は item_values.verified_at）
    source_opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    check_state: Mapped[str] = mapped_column(String(16), nullable=False, server_default="unchecked")
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    excluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    excluded_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "classification IN ('needs_confirmation','low_confidence','high_confidence')",
            name="ck_item_rows_classification",
        ),
        CheckConstraint("check_state IN ('unchecked','checked')", name="ck_item_rows_check_state"),
        UniqueConstraint("inquiry_id", "row_no", name="uq_item_rows_inquiry_row_no"),
        Index("ix_item_rows_inquiry_row_no", "inquiry_id", "row_no"),
        Index("ix_item_rows_inquiry_classification", "inquiry_id", "classification"),
    )
