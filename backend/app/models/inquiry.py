"""inquiries — 引合の案件（04）。"""
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

STATUSES = ("received", "reading", "unreadable", "awaiting_review", "confirmed")
UNREADABLE_REASONS = ("illegible", "no_items", "timeout", "max_turns")


class Inquiry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inquiries"

    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="received")
    unreadable_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # KPI1（1件あたりの作業時間）の起点。⑤ #9 が「確認待ちで NULL のとき」だけ書く
    review_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 保持期限（② 非機能）。自動削除は FUNC-10 で今回は対象外
    retention_until: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('received','reading','unreadable','awaiting_review','confirmed')",
            name="ck_inquiries_status",
        ),
        CheckConstraint(
            "unreadable_reason IS NULL OR unreadable_reason IN "
            "('illegible','no_items','timeout','max_turns')",
            name="ck_inquiries_unreadable_reason",
        ),
        Index("ix_inquiries_status_submitted_at", "status", submitted_at.desc()),
        Index("ix_inquiries_retention_until", "retention_until"),
    )
