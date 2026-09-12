"""agent_runs — エージェントの実行記録（agent.md の出力形式）。トレースと1対1。"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin

STOP_REASONS = (
    "completed",
    "failed",
    "max_turns",
    "inner_timeout",
    "inactivity_timeout",
    "outer_timeout",
)
FAILURE_REASONS = ("illegible", "no_items")


class AgentRun(CreatedAtMixin, Base):
    __tablename__ = "agent_runs"

    # 主キーはトレースのファイル名 backend/traces/{run_id}.jsonl と同じ
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("inquiries.id", ondelete="CASCADE"), nullable=False
    )
    # 1 = 自動起動、2 = 再実行。再実行は1回まで（② FUNC-07）を DB でも担保する
    attempt_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    max_turns: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="running")
    stop_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    turns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trace_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    __table_args__ = (
        CheckConstraint("attempt_no IN (1, 2)", name="ck_agent_runs_attempt_no"),
        CheckConstraint("status IN ('running','finished')", name="ck_agent_runs_status"),
        CheckConstraint(
            "stop_reason IS NULL OR stop_reason IN "
            "('completed','failed','max_turns','inner_timeout','inactivity_timeout','outer_timeout')",
            name="ck_agent_runs_stop_reason",
        ),
        CheckConstraint(
            "failure_reason IS NULL OR failure_reason IN ('illegible','no_items')",
            name="ck_agent_runs_failure_reason",
        ),
        UniqueConstraint("inquiry_id", "attempt_no", name="uq_agent_runs_inquiry_attempt"),
        Index("ix_agent_runs_inquiry_started_at", "inquiry_id", started_at.desc()),
    )
