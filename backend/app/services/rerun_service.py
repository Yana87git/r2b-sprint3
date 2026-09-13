"""エージェントの再実行（⑤ #7・② FUNC-07）。

再実行できるのは**打ち切りで終わったときだけ**（タイムアウト・最大ターン数超過）。
判読不能・明細なしは読み直しても結果が変わらないので許さない。回数は1回まで。
実行記録が1件もない案件（自動起動に失敗した案件）の起動にも同じ口を使う。
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, Inquiry, InquiryInput
from app.services import agent_run_service, inquiry_intake_service

# 打ち切りで終わった案件だけ再実行できる（① 用語・② FUNC-07）
RETRYABLE_REASONS = ("timeout", "max_turns")
MAX_ATTEMPTS = 2


class RerunError(Exception):
    """再実行できない（⑤ #7 の 409）。理由は SCR-10 の文面の出し分けに使う。"""

    def __init__(self, code: str, message: str, reason: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.reason = reason


async def start_rerun(session: AsyncSession, inquiry_id: uuid.UUID) -> dict[str, Any] | None:
    inquiry = await session.get(Inquiry, inquiry_id)
    if inquiry is None:
        return None
    if inquiry.status == "confirmed":
        raise RerunError("ALREADY_CONFIRMED", "確定済みの案件は再実行できません")

    runs = list(
        (await session.execute(select(AgentRun).where(AgentRun.inquiry_id == inquiry_id))).scalars()
    )
    if any(r.status == "running" for r in runs):
        raise RerunError("RUN_IN_PROGRESS", "この案件はいま実行中です")

    attempt_no = len(runs) + 1
    if runs:
        if attempt_no > MAX_ATTEMPTS:
            raise RerunError("RETRY_NOT_ALLOWED", "再実行は1回までです", reason="already_retried")
        if inquiry.status != "unreadable" or inquiry.unreadable_reason not in RETRYABLE_REASONS:
            raise RerunError(
                "RETRY_NOT_ALLOWED",
                "打ち切りで終わった案件だけ再実行できます",
                reason=inquiry.unreadable_reason or inquiry.status,
            )

    # 読み直すので、案件と入力の状態を投入直後に戻す（除外した入力はそのまま）
    inquiry.status = "received"
    inquiry.unreadable_reason = None
    inputs = list(
        (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id))
        ).scalars()
    )
    for input_ in inputs:
        if input_.excluded_at is not None:
            continue
        input_.status = "pending"
        input_.unreadable_reason = None
        input_.read_range = None
        input_.row_count = 0
    await session.commit()

    run_id = await inquiry_intake_service.start_run(
        session, inquiry_id, attempt_no=attempt_no, rollback_on_failure=False
    )
    return {"run_id": run_id, "attempt_no": attempt_no}


async def next_attempt_no(inquiry_id: uuid.UUID) -> int:
    """画面に出す「次は何回目か」。"""
    return await agent_run_service.next_attempt_no(inquiry_id)
