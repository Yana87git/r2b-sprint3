"""引合一覧（⑤ #5）。③ SCR-02 の表と、状況ごとの件数を返す。

ページネーションは設けない（保持期間90日で150〜200件）。N+1 を避けるため、
形式・行数・実行・出力はそれぞれ1回のクエリでまとめて取る。
"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, Inquiry, InquiryInput, ItemListExport, ItemRow, User

STATUSES = ("received", "reading", "unreadable", "awaiting_review", "confirmed")


async def list_inquiries(session: AsyncSession, status: str | None = None) -> dict[str, Any]:
    stmt = select(Inquiry).order_by(Inquiry.submitted_at.desc())
    if status:
        stmt = stmt.where(Inquiry.status == status)
    inquiries = list((await session.execute(stmt)).scalars())
    ids = [i.id for i in inquiries]

    counts = {s: 0 for s in STATUSES}
    for row in await session.execute(select(Inquiry.status, func.count()).group_by(Inquiry.status)):
        counts[row[0]] = row[1]
    counts["all"] = sum(counts[s] for s in STATUSES)

    formats: dict[Any, list[str]] = {}
    unreadable_inputs: dict[Any, int] = {}
    rows_total: dict[Any, int] = {}
    rows_unchecked: dict[Any, int] = {}
    runs: dict[Any, AgentRun] = {}
    pending: dict[Any, int] = {}
    if ids:
        for input_ in (
            await session.execute(
                select(InquiryInput)
                .where(InquiryInput.inquiry_id.in_(ids))
                .order_by(InquiryInput.created_at)
            )
        ).scalars():
            kinds = formats.setdefault(input_.inquiry_id, [])
            if input_.format not in kinds:
                kinds.append(input_.format)
            if input_.status == "unreadable" and input_.excluded_at is None:
                unreadable_inputs[input_.inquiry_id] = (
                    unreadable_inputs.get(input_.inquiry_id, 0) + 1
                )

        for item in (
            await session.execute(select(ItemRow).where(ItemRow.inquiry_id.in_(ids)))
        ).scalars():
            if item.excluded_at is not None:
                continue
            rows_total[item.inquiry_id] = rows_total.get(item.inquiry_id, 0) + 1
            if item.check_state != "checked":
                rows_unchecked[item.inquiry_id] = rows_unchecked.get(item.inquiry_id, 0) + 1

        for run in (
            await session.execute(
                select(AgentRun).where(AgentRun.inquiry_id.in_(ids)).order_by(AgentRun.started_at)
            )
        ).scalars():
            runs[run.inquiry_id] = run  # 新しいものが後に来るので上書きで最新になる

        for export in (
            await session.execute(select(ItemListExport).where(ItemListExport.inquiry_id.in_(ids)))
        ).scalars():
            pending[export.inquiry_id] = export.pending_row_count

    names = {user.id: user.display_name for user in (await session.execute(select(User))).scalars()}

    return {
        "counts": counts,
        "inquiries": [
            {
                "inquiry_id": str(i.id),
                "title": i.title,
                "status": i.status,
                "unreadable_reason": i.unreadable_reason,
                "submitted_at": i.submitted_at.isoformat(),
                "submitted_by_name": names.get(i.submitted_by, ""),
                "formats": formats.get(i.id, []),
                "total_rows": rows_total.get(i.id, 0),
                "unchecked_rows": rows_unchecked.get(i.id, 0),
                "unreadable_input_count": unreadable_inputs.get(i.id, 0),
                "pending_row_count": pending.get(i.id),
                "latest_run_id": str(runs[i.id].run_id) if i.id in runs else None,
            }
            for i in inquiries
        ],
    }
