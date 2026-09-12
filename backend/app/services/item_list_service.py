"""品目リスト案の取得と確認（⑤ #9・#11）。画面（SCR-05）はこの2本で動く。"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput, ItemListExport, ItemRow, ItemValue, User, ValueClue
from app.repositories.user_repository import UserRepository

# 要確認 → 確信が低い → 確信が高い の順に見せる（③ SCR-05）
CLASSIFICATION_ORDER = {"needs_confirmation": 0, "low_confidence": 1, "high_confidence": 2}
UNREADABLE_STATUSES = ("unreadable",)


async def get_items(
    session: AsyncSession,
    inquiry_id: uuid.UUID,
    *,
    filter_: str | None = None,
    include_excluded: bool = True,
) -> dict[str, Any] | None:
    """行・値・読み取り元・手がかりと集計を返す。**KPI1 の起点をここで記録する。**"""
    inquiry = await session.get(Inquiry, inquiry_id)
    if inquiry is None:
        return None

    # 案件が「確認待ち」で未記録のときだけ、確認を始めた時刻を入れる（2回目以降は何も変えない）
    if inquiry.status == "awaiting_review" and inquiry.review_started_at is None:
        inquiry.review_started_at = datetime.now(timezone.utc)

    rows = list(
        (
            await session.execute(
                select(ItemRow).where(ItemRow.inquiry_id == inquiry_id).order_by(ItemRow.row_no)
            )
        ).scalars()
    )
    # N+1 を避けるため、値と手がかりは1回ずつでまとめて取る
    values_by_row: dict[uuid.UUID, list[ItemValue]] = {}
    clues_by_value: dict[uuid.UUID, list[ValueClue]] = {}
    if rows:
        values = list(
            (
                await session.execute(
                    select(ItemValue).where(ItemValue.item_row_id.in_([r.id for r in rows]))
                )
            ).scalars()
        )
        for value in values:
            values_by_row.setdefault(value.item_row_id, []).append(value)
        if values:
            for clue in (
                await session.execute(
                    select(ValueClue).where(ValueClue.item_value_id.in_([v.id for v in values]))
                )
            ).scalars():
                clues_by_value.setdefault(clue.item_value_id, []).append(clue)

    summary = _summarize(rows)
    inputs = list(
        (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id))
        ).scalars()
    )
    summary["unreadable_input_count"] = sum(
        1 for i in inputs if i.status in UNREADABLE_STATUSES and i.excluded_at is None
    )
    # 読み取り元は「見積依頼.xlsx 明細!C12」の形で見せる（③ SCR-05）。
    # 名前の解決はサーバー側でやる（画面が入力の一覧を別に引かなくて済むように）
    input_names = {i.id: i.display_name for i in inputs}
    names = {u.id: u.display_name for u in (await session.execute(select(User))).scalars()}

    shown = _filter_rows(rows, values_by_row, filter_, include_excluded)
    shown.sort(key=lambda r: (CLASSIFICATION_ORDER.get(r.classification, 9), r.row_no))

    export = (
        await session.execute(select(ItemListExport).where(ItemListExport.inquiry_id == inquiry_id))
    ).scalar_one_or_none()

    return {
        "inquiry_id": str(inquiry_id),
        "title": inquiry.title,
        "status": inquiry.status,
        "confirmed_at": _iso(inquiry.confirmed_at),
        "confirmed_by_name": names.get(inquiry.confirmed_by, "") if inquiry.confirmed_by else None,
        "pending_row_count": export.pending_row_count if export else None,
        "export_row_count": export.row_count if export else None,
        "review_started_at": _iso(inquiry.review_started_at),
        "inputs": [_input_payload(i) for i in inputs],
        "rows": [
            _row_payload(r, values_by_row.get(r.id, []), clues_by_value, input_names) for r in shown
        ],
        "summary": summary,
    }


def _input_payload(input_: InquiryInput) -> dict[str, Any]:
    return {
        "input_id": str(input_.id),
        "display_name": input_.display_name,
        "format": input_.format,
        "status": input_.status,
        "unreadable_reason": input_.unreadable_reason,
        "row_count": input_.row_count,
        "excluded": input_.excluded_at is not None,
    }


async def get_inquiry(session: AsyncSession, inquiry_id: uuid.UUID) -> Inquiry | None:
    return await session.get(Inquiry, inquiry_id)


async def check_row(
    session: AsyncSession, inquiry_id: uuid.UUID, row_id: uuid.UUID
) -> dict[str, Any] | None:
    """行を確認済みにする（⑤ #11）。確認済みの行をもう一度押しても時刻は動かさない。"""
    row = await session.get(ItemRow, row_id)
    if row is None or row.inquiry_id != inquiry_id:
        return None
    if row.check_state != "checked":
        user = await UserRepository(session).get_fixed_user()
        row.check_state = "checked"
        row.checked_at = datetime.now(timezone.utc)
        row.checked_by = user.id if user else None
    await session.flush()

    rows = list(
        (await session.execute(select(ItemRow).where(ItemRow.inquiry_id == inquiry_id))).scalars()
    )
    return {
        "row_id": str(row.id),
        "check_state": row.check_state,
        "checked_at": _iso(row.checked_at),
        "summary": _summarize(rows),
    }


def _filter_rows(
    rows: list[ItemRow],
    values_by_row: dict[uuid.UUID, list[ItemValue]],
    filter_: str | None,
    include_excluded: bool,
) -> list[ItemRow]:
    if filter_ == "needs_confirmation":
        # 除外した行は出力されないので、問い合わせの対象にしない（⑤ #9）
        return [
            r
            for r in rows
            if r.excluded_at is None
            and any(v.state == "needs_confirmation" for v in values_by_row.get(r.id, []))
        ]
    if include_excluded:
        return list(rows)
    return [r for r in rows if r.excluded_at is None]


def _summarize(rows: list[ItemRow]) -> dict[str, Any]:
    """画面の集計表示用に、その場で数える（⑤ #9）。"""
    active = [r for r in rows if r.excluded_at is None]
    by_classification: dict[str, int] = {}
    for row in active:
        by_classification[row.classification] = by_classification.get(row.classification, 0) + 1
    return {
        "total_rows": len(rows),
        "excluded_rows": len(rows) - len(active),
        "unchecked_rows": sum(1 for r in active if r.check_state != "checked"),
        "sampled_rows": sum(1 for r in active if r.source_opened_at is not None),
        "by_classification": by_classification,
    }


def _row_payload(
    row: ItemRow,
    values: list[ItemValue],
    clues_by_value: dict[uuid.UUID, list[ValueClue]],
    input_names: dict[uuid.UUID, str],
) -> dict[str, Any]:
    return {
        "row_id": str(row.id),
        "row_no": row.row_no,
        "classification": row.classification,
        "check_state": row.check_state,
        "excluded": row.excluded_at is not None,
        "source_opened": row.source_opened_at is not None,
        "values": {
            v.field: _value_payload(v, clues_by_value.get(v.id, []), input_names) for v in values
        },
    }


def _value_payload(
    value: ItemValue, clues: list[ValueClue], input_names: dict[uuid.UUID, str]
) -> dict[str, Any]:
    return {
        "value_id": str(value.id),
        "state": value.state,
        "confidence": value.confidence,
        "raw_text": value.raw_text,
        "value_text": value.value_text,
        "quantity_value": float(value.quantity_value) if value.quantity_value is not None else None,
        "due_kind": value.due_kind,
        "due_start": value.due_start.isoformat() if value.due_start else None,
        "due_end": value.due_end.isoformat() if value.due_end else None,
        "source": {
            "input_id": str(value.source_input_id),
            "input_name": input_names.get(value.source_input_id, ""),
            "locator": value.locator,
            "locator_label": (value.locator or {}).get("label", ""),
        }
        if value.source_input_id
        else None,
        "clues": [
            {"clue": c.clue, "detail": c.detail} for c in sorted(clues, key=lambda c: c.clue)
        ],
    }


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


# 一括確認に必要な抜き取り（⑤ #12・④ と同じ数え方）
REQUIRED_SAMPLES = 3


class SamplingNotEnoughError(Exception):
    """抜き取りが足りないので一括確認できない（⑤ #12 の 409）。

    **サーバー側で拒否する**（画面のボタンを押せなくするだけにしない。② FUNC-04）。
    """

    def __init__(self, sampled: int, required: int) -> None:
        super().__init__("抜き取りが足りません")
        self.sampled = sampled
        self.required = required


async def bulk_check(session: AsyncSession, inquiry_id: uuid.UUID) -> dict[str, Any]:
    """確信が高い行をまとめて確認済みにする（⑤ #12）。

    N = 確信が高く、除外していない行（**確認済みかどうかは問わない**）。
    確認済みを N から除くと、1行ずつ確認するたびに分母が動いて判定が不安定になる。
    """
    confident = list(
        (
            await session.execute(
                select(ItemRow).where(
                    ItemRow.inquiry_id == inquiry_id,
                    ItemRow.classification == "high_confidence",
                    ItemRow.excluded_at.is_(None),
                )
            )
        ).scalars()
    )
    sampled = sum(1 for r in confident if r.source_opened_at is not None)
    required = min(REQUIRED_SAMPLES, len(confident))
    if sampled < required:
        raise SamplingNotEnoughError(sampled, required)

    user = await UserRepository(session).get_fixed_user()
    now = datetime.now(timezone.utc)
    checked = 0
    for row in confident:
        if row.check_state == "checked":
            continue
        row.check_state = "checked"
        row.checked_at = now
        row.checked_by = user.id if user else None
        checked += 1
    await session.flush()

    rows = list(
        (await session.execute(select(ItemRow).where(ItemRow.inquiry_id == inquiry_id))).scalars()
    )
    return {"checked_rows": checked, "summary": _summarize(rows)}
