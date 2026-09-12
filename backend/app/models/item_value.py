"""item_values — 行の中の値（04）。原文と正規化後の値の両方を持つ。"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

FIELDS = ("item_name", "model_no", "quantity", "unit", "due_date", "note")
STATES = ("extracted", "needs_confirmation")
CONFIDENCES = ("high", "low")
# 納期の値域（② FUNC-02 の (a)(b)(c)）
DUE_KINDS = ("fixed_date", "month_range", "needs_confirmation")


class ItemValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "item_values"

    item_row_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("item_rows.id", ondelete="CASCADE"), nullable=False
    )
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    due_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    due_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[str] = mapped_column(String(8), nullable=False)
    source_input_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inquiry_inputs.id"), nullable=True
    )
    # 形式ごとの位置: Excel {"sheet","cell"} / PDF {"page","line"} / Word {"table","row","col"} or {"paragraph"} / メール {"line"}
    locator: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "field IN ('item_name','model_no','quantity','unit','due_date','note')",
            name="ck_item_values_field",
        ),
        CheckConstraint("state IN ('extracted','needs_confirmation')", name="ck_item_values_state"),
        CheckConstraint("confidence IN ('high','low')", name="ck_item_values_confidence"),
        CheckConstraint(
            "due_kind IS NULL OR due_kind IN ('fixed_date','month_range','needs_confirmation')",
            name="ck_item_values_due_kind",
        ),
        # 要確認でない値には必ず原文と読み取り元がある（agent.md 完了条件④・ガードレール）
        CheckConstraint(
            "(state = 'extracted' AND raw_text IS NOT NULL AND source_input_id IS NOT NULL "
            "AND locator IS NOT NULL) OR "
            "(state = 'needs_confirmation' AND raw_text IS NULL AND source_input_id IS NULL "
            "AND locator IS NULL)",
            name="ck_item_values_extracted_needs_source",
        ),
        # (b) 月内の範囲は、同じ月の中で開始日 ≦ 終了日（③ SCR-07）
        CheckConstraint(
            "due_kind IS NULL OR due_kind <> 'month_range' OR "
            "(due_start IS NOT NULL AND due_end IS NOT NULL AND due_start <= due_end "
            "AND date_trunc('month', due_start) = date_trunc('month', due_end))",
            name="ck_item_values_month_range",
        ),
        UniqueConstraint("item_row_id", "field", name="uq_item_values_row_field"),
        Index("ix_item_values_item_row_id", "item_row_id"),
        Index("ix_item_values_source_input_id", "source_input_id"),
    )
