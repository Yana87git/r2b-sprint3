"""品目リスト案の保存（save_item_rows）。

- **案件のぶんを丸ごと置き換える**（item_rows / item_values / value_clues）
- 検査で誤りが見つかっても保存する。そのうえで {row_no, field, message} の一覧を返す
  （保存せず弾くと、check_completion が「何も保存されていない」としか見えず、
  ③〜⑥ のどれが足りないかを返せない）
- ただし DB の制約に反する値（抽出済みなのに原文や読み取り元が無い）は、その項目だけ
  保存しない。伏せて「要確認」で保存すると、完了条件③が素通りしてしまうため
"""
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput, ItemRow, ItemValue, ValueClue

# ツールの項目名 → DB の項目名（⑤・④ の呼び方に合わせる）
FIELD_MAP = {
    "item_name": "item_name",
    "part_no": "model_no",
    "model_no": "model_no",
    "quantity": "quantity",
    "unit": "unit",
    "due_date": "due_date",
    "remarks": "note",
    "note": "note",
}
REQUIRED_FIELDS = ("item_name", "part_no", "quantity", "unit", "due_date")
DUE_KINDS = {
    "fixed": "fixed_date",
    "fixed_date": "fixed_date",
    "month_range": "month_range",
    "needs_confirmation": "needs_confirmation",
}
CLUES = {"H1", "H2", "H3", "H4"}


class SaveError(dict):
    """{row_no, field, message}。"""

    def __init__(self, row_no: Any, field: str, message: str) -> None:
        super().__init__(row_no=row_no, field=field, message=message)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _validate_value(
    row_no: Any, field: str, payload: dict[str, Any], valid_input_ids: set[uuid.UUID]
) -> tuple[dict[str, Any] | None, list[SaveError]]:
    """1つの値を検査し、(保存する内容, 誤り) を返す。保存できないときは None。"""
    errors: list[SaveError] = []
    state = payload.get("state")
    raw_text = payload.get("raw_text")
    value_text = payload.get("value")

    # 必須5項目の空欄
    if state is None and raw_text is None and value_text is None:
        if field in REQUIRED_FIELDS:
            errors.append(
                SaveError(row_no, field, "必須項目が空です。値を入れるか要確認にしてください")
            )
        return None, errors

    if state not in ("extracted", "needs_confirmation"):
        errors.append(
            SaveError(row_no, field, f"state は extracted か needs_confirmation です: {state}")
        )
        return None, errors

    confidence = payload.get("confidence") or "high"
    if confidence not in ("high", "low"):
        errors.append(SaveError(row_no, field, f"confidence は high か low です: {confidence}"))
        confidence = "high"

    clues = [c for c in (payload.get("clues") or []) if c in CLUES]
    # 確信が低いのに手がかりが無い（完了条件⑤がこれに依存）
    if confidence == "low" and not clues:
        errors.append(
            SaveError(row_no, field, "確信が低い値には手がかり（H1〜H4）が1つ以上必要です")
        )

    source = payload.get("source") or {}
    source_input_id: uuid.UUID | None = None
    locator = None

    if state == "extracted":
        # 読み取り元のない値
        if not source.get("input_id") or not source.get("locator"):
            errors.append(
                SaveError(
                    row_no, field, "抽出した値には読み取り元（input_id と locator）が必要です"
                )
            )
            return None, errors
        try:
            source_input_id = uuid.UUID(str(source["input_id"]))
        except ValueError:
            errors.append(
                SaveError(row_no, field, f"input_id が不正です: {source.get('input_id')}")
            )
            return None, errors
        # 案件にないファイルを指す読み取り元
        if source_input_id not in valid_input_ids:
            errors.append(SaveError(row_no, field, "この案件に無い入力を読み取り元にしています"))
            return None, errors
        if raw_text is None:
            errors.append(SaveError(row_no, field, "抽出した値には原文（raw_text）が必要です"))
            return None, errors
        locator = {"label": str(source["locator"])}

    stored: dict[str, Any] = {
        "field": FIELD_MAP[field],
        "state": state,
        "raw_text": raw_text if state == "extracted" else None,
        "value_text": None if value_text is None else str(value_text),
        "confidence": confidence,
        "source_input_id": source_input_id,
        "locator": locator,
        "clues": clues,
        "quantity_value": None,
        "due_kind": None,
        "due_start": None,
        "due_end": None,
    }

    # 数値でない数量
    if field == "quantity" and state == "extracted":
        try:
            stored["quantity_value"] = Decimal(str(value_text))
        except (InvalidOperation, TypeError):
            errors.append(SaveError(row_no, field, f"数量が数値として解釈できません: {value_text}"))

    # 値域の外の納期
    if field == "due_date":
        kind = DUE_KINDS.get(str(payload.get("kind")))
        if kind is None:
            errors.append(
                SaveError(
                    row_no,
                    field,
                    f"納期の kind は fixed / month_range / needs_confirmation です: {payload.get('kind')}",
                )
            )
        else:
            start = _parse_date(payload.get("start_date"))
            end = _parse_date(payload.get("end_date"))
            if kind == "fixed_date":
                if start is None:
                    errors.append(SaveError(row_no, field, "確定日付には start_date が必要です"))
                else:
                    stored["due_start"] = stored["due_end"] = start
            elif kind == "month_range":
                if start is None or end is None:
                    errors.append(
                        SaveError(row_no, field, "月内の範囲には start_date と end_date が必要です")
                    )
                elif start > end:
                    errors.append(
                        SaveError(row_no, field, "範囲は開始日を終了日以前にしてください")
                    )
                elif (start.year, start.month) != (end.year, end.month):
                    errors.append(SaveError(row_no, field, "範囲は同じ月の中にしてください"))
                else:
                    stored["due_start"], stored["due_end"] = start, end
            if kind == "needs_confirmation" and state == "extracted":
                errors.append(
                    SaveError(
                        row_no,
                        field,
                        "kind が needs_confirmation なら state も needs_confirmation です",
                    )
                )
            stored["due_kind"] = kind
            # 表示用のテキスト（納期は value ではなく kind と日付で表すため、ここで作る）
            if stored["value_text"] is None:
                if kind == "fixed_date" and stored["due_start"]:
                    stored["value_text"] = stored["due_start"].isoformat()
                elif kind == "month_range" and stored["due_start"] and stored["due_end"]:
                    stored[
                        "value_text"
                    ] = f"{stored['due_start'].isoformat()}〜{stored['due_end'].isoformat()}"
            # 保存できない組み合わせは落とす（DB の CHECK に反するため）
            if kind == "month_range" and (stored["due_start"] is None or stored["due_end"] is None):
                return None, errors

    return stored, errors


def classify_row(values: list[dict[str, Any]]) -> str:
    """行の分類は値の状態から決まる（④「行の分類の呼び方」）。"""
    if any(v["state"] == "needs_confirmation" for v in values):
        return "needs_confirmation"
    if any(v["confidence"] == "low" for v in values):
        return "low_confidence"
    return "high_confidence"


async def replace_rows(
    session: AsyncSession, inquiry_id: uuid.UUID, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    """品目リスト案を丸ごと置き換える。保存した行数と誤りの一覧を返す。"""
    inputs = (
        (await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id)))
        .scalars()
        .all()
    )
    valid_input_ids = {i.id for i in inputs}

    errors: list[SaveError] = []

    # 置き換え: 既存の行を消す（値と手がかりは ON DELETE CASCADE で消える）
    await session.execute(delete(ItemRow).where(ItemRow.inquiry_id == inquiry_id))

    saved_rows = 0
    rows_per_input: dict[uuid.UUID, int] = {i: 0 for i in valid_input_ids}

    for index, row in enumerate(rows, start=1):
        row_no = row.get("row_no", index)
        # values の下にまとめる形と、行の直下に並べる形の両方を受ける
        # （モデルは後者で送ってくることがある。弾くと直しようがなく堂々巡りになる）
        values_payload = row.get("values") or {
            key: value for key, value in row.items() if key in FIELD_MAP
        }

        stored_values: list[dict[str, Any]] = []
        for field in ("item_name", "part_no", "quantity", "unit", "due_date", "remarks"):
            payload = values_payload.get(field)
            if payload is None:
                # 別名（model_no / note）でも受ける
                alt = {"part_no": "model_no", "remarks": "note"}.get(field)
                payload = values_payload.get(alt) if alt else None
            if payload is None:
                if field in REQUIRED_FIELDS:
                    errors.append(SaveError(row_no, field, "必須項目がありません"))
                continue
            stored, value_errors = _validate_value(row_no, field, payload, valid_input_ids)
            errors.extend(value_errors)
            if stored is not None:
                stored_values.append(stored)

        if not stored_values:
            continue

        item_row = ItemRow(
            inquiry_id=inquiry_id,
            row_no=int(row_no),
            classification=classify_row(stored_values),
        )
        session.add(item_row)
        await session.flush()
        saved_rows += 1

        cited_inputs: set[uuid.UUID] = set()
        for stored in stored_values:
            clues = stored.pop("clues")
            value = ItemValue(item_row_id=item_row.id, **stored)
            session.add(value)
            await session.flush()
            for clue in clues:
                session.add(ValueClue(item_value_id=value.id, clue=clue))
            if stored["source_input_id"] is not None:
                cited_inputs.add(stored["source_input_id"])
        # **行の数**を数える（値の数ではない）。1行の中で同じ入力を何度引いても1行
        for input_id in cited_inputs:
            rows_per_input[input_id] = rows_per_input.get(input_id, 0) + 1

    # 「読み取り済み」は保存した行の読み取り元から自動で決まる（§3-3）
    for input_ in inputs:
        cited = rows_per_input.get(input_.id, 0)
        if cited > 0:
            input_.status = "read"
            input_.row_count = cited
    await session.flush()

    inquiry = await session.get(Inquiry, inquiry_id)
    if inquiry is not None and inquiry.status == "received":
        inquiry.status = "reading"

    return {"saved_rows": saved_rows, "errors": [dict(e) for e in errors]}
