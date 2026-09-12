"""行の修正（⑤ #10・② FUNC-05）。

処理の順序は ⑤ のとおり:
  1. 保存する
  2. **人が直した値は確信度を「高い」にし、手がかり（H1〜H4）を消す**（読み違いではないため）
  3. 行の分類を計算し直す
  4. その行を確認済みにする

原文（raw_text）と読み取り元は**書き換えない**。何と書いてあったかが分からなくなるため
（値を「要確認」に戻したときだけ、④ の CHECK に合わせて原文も外す）。
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ItemRow, ItemValue, ValueClue
from app.repositories.user_repository import UserRepository
from app.services.item_draft_service import FIELD_MAP, classify_row

REQUIRED_FIELDS = ("item_name", "model_no", "quantity", "unit", "due_date")
DUE_KINDS = ("fixed_date", "month_range", "needs_confirmation")


class EditError(Exception):
    """直せない（⑤ #10 の 400）。"""

    def __init__(self, code: str, message: str, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def _parse_date(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError) as e:
        raise EditError("DUE_RANGE_INVALID", "日付の形式が正しくありません", field) from e


def _apply(value: ItemValue, payload: dict[str, Any]) -> None:
    """1つの値に人の入力を当てる。検査に落ちたら EditError。"""
    field = value.field
    state = payload.get("state", "extracted")
    if state not in ("extracted", "needs_confirmation"):
        raise EditError("REQUIRED_FIELD_EMPTY", "値の状態が不正です", field)

    if state == "needs_confirmation":
        if field not in REQUIRED_FIELDS and field != "note":
            raise EditError("REQUIRED_FIELD_EMPTY", "この項目は要確認にできません", field)
        # ④ の CHECK に合わせ、要確認の値は原文も読み取り元も持たない
        value.state = "needs_confirmation"
        value.value_text = None
        value.raw_text = None
        value.source_input_id = None
        value.locator = None
        value.quantity_value = None
        value.due_kind = "needs_confirmation" if field == "due_date" else None
        value.due_start = None
        value.due_end = None
        return

    if field == "due_date":
        kind = payload.get("kind")
        if kind not in DUE_KINDS:
            raise EditError(
                "DUE_DATE_OUT_OF_DOMAIN",
                "納期は「確定日付」「月内の範囲」「要確認」のいずれかです",
                field,
            )
        if kind == "needs_confirmation":
            raise EditError(
                "DUE_DATE_OUT_OF_DOMAIN",
                "納期を要確認にするときは state を needs_confirmation にしてください",
                field,
            )
        start = _parse_date(payload.get("start_date"), field)
        value.due_kind = kind
        value.due_start = start
        if kind == "fixed_date":
            value.due_end = None
            value.value_text = start.isoformat()
        else:
            end = _parse_date(payload.get("end_date"), field)
            if end < start or (start.year, start.month) != (end.year, end.month):
                raise EditError(
                    "DUE_RANGE_INVALID",
                    "月内の範囲は同じ月の中で、開始日が終了日より後にならないようにしてください",
                    field,
                )
            value.due_end = end
            value.value_text = f"{start.isoformat()}〜{end.isoformat()}"
        value.state = "extracted"
        return

    text = str(payload.get("value", "")).strip()
    if not text:
        if field in REQUIRED_FIELDS:
            raise EditError(
                "REQUIRED_FIELD_EMPTY",
                "必須の項目は空欄にできません（分からない場合は要確認にしてください）",
                field,
            )
        # 備考のような任意の項目は空にしてよい
        value.state = "extracted"
        value.value_text = None
        return

    if field == "quantity":
        try:
            value.quantity_value = Decimal(text.replace(",", ""))
        except (InvalidOperation, ValueError) as e:
            raise EditError("QUANTITY_NOT_NUMERIC", "数量は数値で入力してください", field) from e
    value.state = "extracted"
    value.value_text = text


async def update_row(
    session: AsyncSession, inquiry_id: uuid.UUID, row_id: uuid.UUID, values: dict[str, Any]
) -> dict[str, Any] | None:
    """値を直し、確信度と分類を直してから、その行を確認済みにする。"""
    row = await session.get(ItemRow, row_id)
    if row is None or row.inquiry_id != inquiry_id:
        return None

    stored = {
        v.field: v
        for v in (
            await session.execute(select(ItemValue).where(ItemValue.item_row_id == row_id))
        ).scalars()
    }
    user = await UserRepository(session).get_fixed_user()
    now = datetime.now(timezone.utc)
    edited_fields: list[str] = []

    for raw_field, payload in values.items():
        field = FIELD_MAP.get(raw_field, raw_field)
        if field not in FIELD_MAP.values():
            raise EditError("REQUIRED_FIELD_EMPTY", f"知らない項目です: {raw_field}", raw_field)
        if not isinstance(payload, dict):
            raise EditError("REQUIRED_FIELD_EMPTY", "値の形式が正しくありません", field)
        value = stored.get(field)
        if value is None:
            value = ItemValue(item_row_id=row_id, field=field, state="extracted", confidence="high")
            session.add(value)
            stored[field] = value
        _apply(value, payload)
        # 人が直した値は確信度を「高い」にし、手がかりを消す
        value.confidence = "high"
        value.edited_at = now
        value.edited_by = user.id if user else None
        value.verified_at = None
        edited_fields.append(field)

    await session.flush()
    if edited_fields:
        ids = [stored[f].id for f in edited_fields]
        await session.execute(delete(ValueClue).where(ValueClue.item_value_id.in_(ids)))

    # 行の分類を計算し直してから、確認済みにする
    fresh = list(
        (await session.execute(select(ItemValue).where(ItemValue.item_row_id == row_id))).scalars()
    )
    row.classification = classify_row(
        [{"state": v.state, "confidence": v.confidence} for v in fresh]
    )
    row.check_state = "checked"
    row.checked_at = now
    row.checked_by = user.id if user else None
    await session.flush()

    return {
        "row_id": str(row.id),
        "row_no": row.row_no,
        "classification": row.classification,
        "check_state": row.check_state,
        "edited_fields": edited_fields,
    }
