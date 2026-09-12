"""入力の除外（⑤ #15・② FUNC-07）。

除外は**読み取れなかった入力に対する人の判断**（「この1件は手作業で補う」）。
読み取れている入力には使わせない。除外した入力は、確定の判定（#17）で
「読み取れなかった入力」として数えない。
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput
from app.repositories.user_repository import UserRepository


class ExclusionError(Exception):
    """除外できない（⑤ #15 の 409）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


async def _load(
    session: AsyncSession, inquiry_id: uuid.UUID, input_id: uuid.UUID
) -> tuple[Inquiry, InquiryInput] | None:
    inquiry = await session.get(Inquiry, inquiry_id)
    input_ = await session.get(InquiryInput, input_id)
    if inquiry is None or input_ is None or input_.inquiry_id != inquiry_id:
        return None
    if inquiry.status == "confirmed":
        raise ExclusionError("ALREADY_CONFIRMED", "確定済みの案件は変更できません")
    return inquiry, input_


async def exclude(
    session: AsyncSession, inquiry_id: uuid.UUID, input_id: uuid.UUID
) -> dict[str, Any] | None:
    loaded = await _load(session, inquiry_id, input_id)
    if loaded is None:
        return None
    _, input_ = loaded
    if input_.status != "unreadable":
        raise ExclusionError(
            "INPUT_NOT_EXCLUDABLE",
            "読み取れている入力は除外できません（除外は読み取り不可の入力に使います）",
        )
    if input_.excluded_at is None:
        user = await UserRepository(session).get_fixed_user()
        input_.excluded_at = datetime.now(timezone.utc)
        input_.excluded_by = user.id if user else None
    await session.flush()
    return _payload(input_)


async def cancel(
    session: AsyncSession, inquiry_id: uuid.UUID, input_id: uuid.UUID
) -> dict[str, Any] | None:
    loaded = await _load(session, inquiry_id, input_id)
    if loaded is None:
        return None
    _, input_ = loaded
    input_.excluded_at = None
    input_.excluded_by = None
    await session.flush()
    return _payload(input_)


def _payload(input_: InquiryInput) -> dict[str, Any]:
    return {
        "input_id": str(input_.id),
        "display_name": input_.display_name,
        "status": input_.status,
        "unreadable_reason": input_.unreadable_reason,
        "excluded": input_.excluded_at is not None,
    }
