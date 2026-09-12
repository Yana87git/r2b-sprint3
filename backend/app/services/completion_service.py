"""完了条件・失敗条件の判定（check_completion）。§4 のとおり上から順に評価する。

**LLM に判断させず、すべてコードで書く。**
案件の状態を変えられるのはこの判定だけで、変えられる先は「確認待ち」と「読み取り不可」の2つ。
incomplete のときは案件の状態を変えない（エージェントが直して呼び直す）。
"""
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput, ItemRow, ItemValue, ValueClue
from app.services.source_verify_service import FIELD_LABEL, mark_verified, verify_all

REQUIRED_FIELDS = ("item_name", "model_no", "quantity", "unit", "due_date")
SETTLED_STATUSES = ("read", "read_no_items", "unreadable")
DUE_KINDS = ("fixed_date", "month_range", "needs_confirmation")


def _unmet(condition: str, message: str) -> dict[str, str]:
    return {"condition": condition, "message": message}


def _is_blank(value: ItemValue) -> bool:
    """値が埋まっていないか。納期は value ではなく kind と日付で表す。"""
    if value.field == "due_date":
        return value.due_kind is None
    return not (value.value_text or "").strip()


async def check(session: AsyncSession, inquiry_id: uuid.UUID) -> dict[str, Any]:
    """判定して案件の状態を決める。返す形は §3-6 のとおり。"""
    inquiry = await session.get(Inquiry, inquiry_id)
    if inquiry is None:
        return {"result": "incomplete", "unmet": [_unmet("①", "案件が見つかりません")]}

    inputs = list(
        (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id))
        ).scalars()
    )
    rows = list(
        (
            await session.execute(
                select(ItemRow).where(ItemRow.inquiry_id == inquiry_id).order_by(ItemRow.row_no)
            )
        ).scalars()
    )
    values_by_row: dict[uuid.UUID, list[ItemValue]] = {}
    if rows:
        stmt = select(ItemValue).where(ItemValue.item_row_id.in_([r.id for r in rows]))
        for value in (await session.execute(stmt)).scalars():
            values_by_row.setdefault(value.item_row_id, []).append(value)

    # --- 失敗条件（先に見る）---
    if inputs and all(i.status == "unreadable" for i in inputs):
        inquiry.status = "unreadable"
        inquiry.unreadable_reason = "illegible"
        return {"result": "failed_illegible", "unmet": []}

    readable = [i for i in inputs if i.status in ("read", "read_no_items")]
    if not rows and readable:
        inquiry.status = "unreadable"
        inquiry.unreadable_reason = "no_items"
        return {"result": "failed_no_items", "unmet": []}

    # --- 完了条件①〜⑥ ---
    unmet: list[dict[str, str]] = []

    # ① すべての入力の状態が確定し、読み取り済みが1件以上
    unsettled = [i for i in inputs if i.status not in SETTLED_STATUSES]
    if not inputs:
        unmet.append(_unmet("①", "入力が1件もありません"))
    elif unsettled:
        names = "、".join(i.display_name for i in unsettled[:3])
        unmet.append(_unmet("①", f"状態が決まっていない入力があります: {names}"))
    elif not any(i.status == "read" for i in inputs):
        unmet.append(_unmet("①", "読み取り済みの入力が1件もありません"))

    # ② 品目行が1行以上
    if not rows:
        unmet.append(_unmet("②", "品目リスト案が1行もありません"))

    # ③ 全行の必須5項目が、値を持つか要確認
    for row in rows:
        by_field = {v.field: v for v in values_by_row.get(row.id, [])}
        for field in REQUIRED_FIELDS:
            value = by_field.get(field)
            if value is None:
                unmet.append(
                    _unmet("③", f"{row.row_no}行目の {FIELD_LABEL.get(field, field)} がありません")
                )
            elif value.state != "needs_confirmation" and _is_blank(value):
                unmet.append(
                    _unmet("③", f"{row.row_no}行目の {FIELD_LABEL.get(field, field)} が空欄です")
                )

    # ④ 読み取り元があり、照合の不一致が0件（verify_sources と同じ処理を呼ぶ）
    mismatches = await verify_all(session, inquiry_id) if rows else []
    for m in mismatches[:5]:
        note = m.get("note") or f"位置にあるのは「{m['actual_text']}」です"
        unmet.append(
            _unmet(
                "④",
                f"{m['row_no']}行目の {m['field']}: 原文「{m['raw_text']}」と一致しません（{note}）",
            )
        )
    if len(mismatches) > 5:
        unmet.append(_unmet("④", f"ほか {len(mismatches) - 5} 件の不一致があります"))

    # ⑤ 確信度があり、確信が低い値には手がかりが1つ以上
    low_ids = [v.id for vs in values_by_row.values() for v in vs if v.confidence == "low"]
    clue_counts: dict[uuid.UUID, int] = {}
    if low_ids:
        for clue in (
            await session.execute(select(ValueClue).where(ValueClue.item_value_id.in_(low_ids)))
        ).scalars():
            clue_counts[clue.item_value_id] = clue_counts.get(clue.item_value_id, 0) + 1
    for row in rows:
        for value in values_by_row.get(row.id, []):
            if value.confidence == "low" and clue_counts.get(value.id, 0) == 0:
                unmet.append(
                    _unmet(
                        "⑤",
                        f"{row.row_no}行目の {FIELD_LABEL.get(value.field, value.field)} は"
                        "確信が低いのに手がかり（H1〜H4）がありません",
                    )
                )

    # ⑥ 数量が数値、納期が値域のいずれか
    for row in rows:
        for value in values_by_row.get(row.id, []):
            if value.state == "needs_confirmation":
                continue
            if value.field == "quantity" and not isinstance(value.quantity_value, Decimal):
                unmet.append(_unmet("⑥", f"{row.row_no}行目の quantity が数値として解釈できません"))
            if value.field == "due_date" and value.due_kind not in DUE_KINDS:
                unmet.append(_unmet("⑥", f"{row.row_no}行目の due_date の値域が不正です"))

    if unmet:
        # incomplete のときは案件の状態を変えない
        return {"result": "incomplete", "unmet": unmet}

    await mark_verified(session, inquiry_id)
    inquiry.status = "awaiting_review"
    inquiry.unreadable_reason = None
    return {"result": "completed", "unmet": []}
