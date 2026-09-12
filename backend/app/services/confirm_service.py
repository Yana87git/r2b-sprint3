"""確定と品目リストの出力（⑤ #17・② FUNC-06）。

確定条件は「未確認の行が0」かつ「読み取れなかった入力が0件」（① 用語）。
**両方残っているときは読み取れなかった入力を先に返す**（再実行で行が増えると未確認が復活するため）。
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput, ItemListExport, ItemRow, ItemValue
from app.repositories.user_repository import UserRepository
from app.services import export_service
from app.services.inquiry_intake_service import storage_root


class ConfirmError(Exception):
    """確定できない（⑤ #17 の 409）。"""

    def __init__(self, code: str, message: str, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra or {}


async def confirm(session: AsyncSession, inquiry_id: uuid.UUID) -> dict[str, Any] | None:
    inquiry = await session.get(Inquiry, inquiry_id)
    if inquiry is None:
        return None
    if inquiry.status == "confirmed":
        raise ConfirmError("ALREADY_CONFIRMED", "この案件はすでに確定しています")

    inputs = list(
        (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id))
        ).scalars()
    )
    unreadable = [i for i in inputs if i.status == "unreadable" and i.excluded_at is None]
    if unreadable:
        raise ConfirmError(
            "UNREADABLE_INPUT_REMAINS",
            "読み取れなかった入力が残っています。除外するか再実行してください",
            {
                "inputs": [
                    {"input_id": str(i.id), "display_name": i.display_name} for i in unreadable
                ]
            },
        )

    rows = list(
        (
            await session.execute(
                select(ItemRow).where(ItemRow.inquiry_id == inquiry_id).order_by(ItemRow.row_no)
            )
        ).scalars()
    )
    active = [r for r in rows if r.excluded_at is None]
    unchecked = [r for r in active if r.check_state != "checked"]
    if unchecked:
        raise ConfirmError(
            "UNCHECKED_ROWS_REMAIN",
            f"未確認の行が{len(unchecked)}行残っています",
            {"unchecked_rows": len(unchecked)},
        )

    values_by_row: dict[uuid.UUID, list[ItemValue]] = {}
    if active:
        for value in (
            await session.execute(
                select(ItemValue).where(ItemValue.item_row_id.in_([r.id for r in active]))
            )
        ).scalars():
            values_by_row.setdefault(value.item_row_id, []).append(value)

    workbook, pending = export_service.build_workbook(inquiry.title, active, values_by_row)
    path = export_service.save(workbook, storage_root() / str(inquiry_id), inquiry_id)

    user = await UserRepository(session).get_fixed_user()
    confirmed_at = datetime.now(timezone.utc)
    inquiry.status = "confirmed"
    inquiry.confirmed_at = confirmed_at
    inquiry.confirmed_by = user.id if user else None
    session.add(
        ItemListExport(
            inquiry_id=inquiry_id,
            storage_path=str(path),
            row_count=len(active),
            pending_row_count=pending,
            created_by=user.id,
        )
    )
    await session.flush()

    return {
        "inquiry_id": str(inquiry_id),
        "confirmed_at": confirmed_at.isoformat(),
        "row_count": len(active),
        "pending_row_count": pending,
        "download_path": f"/api/v1/inquiries/{inquiry_id}/export",
    }
