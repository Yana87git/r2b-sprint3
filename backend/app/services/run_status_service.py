"""実行の進み具合（⑤ #8）。agent_runs と入力の状態から段階・残り時間・停止理由を返す。"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput
from app.repositories.agent_run_repository import AgentRunRepository

SETTLED_STATUSES = ("read", "read_no_items", "unreadable")
# 残り時間の目安（③ SCR-04「あと約2分」）。D1（入力2件）で約140秒だった実測に合わせる
ETA_BASE_S = 30
ETA_PER_INPUT_S = 60


async def get_status(session: AsyncSession, run_id: uuid.UUID) -> dict[str, Any] | None:
    run = await AgentRunRepository(session).get_by_run_id(run_id)
    if run is None:
        return None
    inquiry = await session.get(Inquiry, run.inquiry_id)
    inputs = list(
        (
            await session.execute(
                select(InquiryInput).where(InquiryInput.inquiry_id == run.inquiry_id)
            )
        ).scalars()
    )
    done = sum(1 for i in inputs if i.status in SETTLED_STATUSES)

    return {
        "run_id": str(run.run_id),
        "inquiry_id": str(run.inquiry_id),
        "attempt_no": run.attempt_no,
        "run_status": run.status,
        "status": inquiry.status if inquiry else None,
        "inputs_done": done,
        "inputs_total": len(inputs),
        "eta_seconds": _eta_seconds(run.status, run.started_at, len(inputs)),
        "stop_reason": run.stop_reason,
        "unreadable_reason": inquiry.unreadable_reason if inquiry else None,
    }


def _eta_seconds(run_status: str, started_at: datetime, inputs_total: int) -> int:
    """残り時間の目安。終わっていれば 0、目安を過ぎても 0（画面はそこで文面を切り替える）。"""
    if run_status != "running":
        return 0
    estimate = ETA_BASE_S + ETA_PER_INPUT_S * max(inputs_total, 1)
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    return max(0, int(estimate - elapsed))
