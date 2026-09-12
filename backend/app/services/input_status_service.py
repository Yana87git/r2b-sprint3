"""入力の状態の記録（set_file_status）。

入力に付けられる状態は「明細なし」と「判読不能」の2つだけ。
**判読不能（illegible）以外の理由を入力単位で付けてはいけない**（agent.md 完了条件①）。
タイムアウトと最大ターン数超過は案件全体の停止理由であって、個々の入力には付かない。
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InquiryInput, ItemValue

# ツールが受け取る言い方 → DB の状態
STATUS_MAP = {"no_items": "read_no_items", "illegible": "unreadable"}
MAX_READ_RANGE = 512


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


async def set_status(
    session: AsyncSession,
    inquiry_id: uuid.UUID,
    input_id: str | None,
    status: str | None,
    read_up_to: str | None = None,
) -> dict[str, Any]:
    """入力1件の状態を記録する。返す形は §3-5 のとおり。"""
    if status not in STATUS_MAP:
        return _error("status は no_items か illegible のどちらかです")
    try:
        target_id = uuid.UUID(str(input_id))
    except (ValueError, AttributeError, TypeError):
        return _error("input_id が入力の ID の形式ではありません")

    input_ = await session.get(InquiryInput, target_id)
    if input_ is None or input_.inquiry_id != inquiry_id:
        # 他の案件の入力は触れない（ガードレール）
        return _error("この案件にその入力はありません")

    # すでに行を読み取った入力に「明細なし・判読不能」は付かない
    used = (
        await session.execute(
            select(ItemValue.id).where(ItemValue.source_input_id == target_id).limit(1)
        )
    ).first()
    if used is not None:
        return _error(
            f"「{input_.display_name}」はすでに品目行の読み取り元になっています。"
            "状態を変えるには先に品目リスト案を保存し直してください"
        )

    input_.status = STATUS_MAP[status]
    input_.unreadable_reason = "illegible" if status == "illegible" else None
    input_.row_count = 0
    if read_up_to:
        input_.read_range = str(read_up_to)[:MAX_READ_RANGE]

    return {
        "ok": True,
        "input_id": str(input_.id),
        "display_name": input_.display_name,
        "status": input_.status,
    }
