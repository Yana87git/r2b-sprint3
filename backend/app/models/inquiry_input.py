"""inquiry_inputs — 投入された入力（ファイルとメール本文）。① の用語「入力」に対応。"""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

KINDS = ("file", "mail_body")
FORMATS = ("excel", "pdf", "word", "mail_body")
# 入力に付く読み取り不可の理由は判読不能のみ（タイムアウト・最大ターン数は案件側）
STATUSES = ("pending", "read", "read_no_items", "unreadable")
MAX_FILE_BYTES = 20 * 1024 * 1024


class InquiryInput(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "inquiry_inputs"

    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    byte_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    unreadable_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    read_range: Mapped[str | None] = mapped_column(String(512), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    excluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    excluded_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint("kind IN ('file','mail_body')", name="ck_inputs_kind"),
        CheckConstraint("format IN ('excel','pdf','word','mail_body')", name="ck_inputs_format"),
        CheckConstraint(
            "status IN ('pending','read','read_no_items','unreadable')", name="ck_inputs_status"
        ),
        CheckConstraint(
            "unreadable_reason IS NULL OR unreadable_reason = 'illegible'",
            name="ck_inputs_unreadable_reason",
        ),
        CheckConstraint(
            f"byte_size IS NULL OR byte_size <= {MAX_FILE_BYTES}", name="ck_inputs_size"
        ),
        CheckConstraint(
            "(kind = 'file' AND storage_path IS NOT NULL AND content_text IS NULL) OR "
            "(kind = 'mail_body' AND content_text IS NOT NULL AND storage_path IS NULL)",
            name="ck_inputs_kind_payload",
        ),
        Index("ix_inquiry_inputs_inquiry_id", "inquiry_id"),
    )
