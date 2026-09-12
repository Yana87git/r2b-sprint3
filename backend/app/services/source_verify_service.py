"""読み取り元の照合。**原文（raw_text）で照合する**（正規化後の値では一致しない）。

- `verify_sources` ツール（§3-4）は、この関数を呼んで不一致の一覧を返すだけ
- `check_completion` の完了条件④も、この関数の不一致件数を見る
二重に書かないため、照合の実体はここ1か所に置く。
"""
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InquiryInput, ItemRow, ItemValue
from app.services.input_reader import InputNotReadableError, read_input

# ツール項目名へ戻す（誤りの報告は ⑤・§3-3 の呼び方に合わせる）
FIELD_LABEL = {
    "item_name": "item_name",
    "model_no": "part_no",
    "quantity": "quantity",
    "unit": "unit",
    "due_date": "due_date",
    "note": "remarks",
}

LOCATOR_EXCEL = re.compile(r"^(?P<sheet>.+)!(?P<col>[A-Z]+)(?P<row>\d+)$")
LOCATOR_PDF = re.compile(r"^p\.(?P<page>\d+)/(?P<line>\d+)$")
LOCATOR_WORD_TABLE = re.compile(r"^表(?P<table>\d+)/(?P<row>\d+)/(?P<col>\d+)$")
LOCATOR_WORD_PARA = re.compile(r"^段落(?P<para>\d+)$")
LOCATOR_MAIL = re.compile(r"^L(?P<line>\d+)$")


def _normalize(text: str) -> str:
    """比較用にそろえる（空白の違いだけで不一致にしない）。"""
    return re.sub(r"\s+", "", str(text))


def _text_at(input_: InquiryInput, locator: str) -> str | None:
    """位置に実際にあるテキストを返す。読めない・位置が不正なら None。"""
    try:
        if (m := LOCATOR_EXCEL.match(locator)) and input_.format == "excel":
            row = int(m.group("row"))
            result = read_input(input_, sheet=m.group("sheet"), start=row, limit=1)
        elif (m := LOCATOR_PDF.match(locator)) and input_.format == "pdf":
            line = int(m.group("line"))
            result = read_input(input_, page=int(m.group("page")), start=line, limit=1)
        elif (m := LOCATOR_WORD_TABLE.match(locator)) or (m := LOCATOR_WORD_PARA.match(locator)):
            if input_.format != "word":
                return None
            result = read_input(input_, start=1, limit=300)
        elif (m := LOCATOR_MAIL.match(locator)) and input_.kind == "mail_body":
            line = int(m.group("line"))
            result = read_input(input_, start=line, limit=1)
        else:
            return None
    except InputNotReadableError:
        return None

    for cell in result["cells"]:
        if cell["locator"] == locator:
            return cell["text"]
    # Excel は行単位で読むので、同じ行の他のセルが返る場合がある
    return None


async def verify_all(session: AsyncSession, inquiry_id: uuid.UUID) -> list[dict[str, Any]]:
    """保存済みの案をすべて照合し、不一致の一覧を返す。"""
    stmt = (
        select(ItemValue, ItemRow)
        .join(ItemRow, ItemValue.item_row_id == ItemRow.id)
        .where(ItemRow.inquiry_id == inquiry_id, ItemValue.state == "extracted")
        .order_by(ItemRow.row_no)
    )
    pairs = (await session.execute(stmt)).all()

    inputs = {
        i.id: i
        for i in (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id))
        ).scalars()
    }

    mismatches: list[dict[str, Any]] = []
    for value, row in pairs:
        locator = (value.locator or {}).get("label")
        input_ = inputs.get(value.source_input_id)
        if input_ is None or not locator:
            mismatches.append(
                _mismatch(row, value, locator, actual=None, note="読み取り元がありません")
            )
            continue

        actual = _text_at(input_, locator)
        if actual is None:
            mismatches.append(
                _mismatch(row, value, locator, actual=None, note="その位置にテキストがありません")
            )
        elif _normalize(value.raw_text or "") not in _normalize(actual):
            mismatches.append(_mismatch(row, value, locator, actual=actual))
    return mismatches


def _mismatch(
    row: ItemRow, value: ItemValue, locator: str | None, *, actual: str | None, note: str = ""
) -> dict[str, Any]:
    return {
        "row_no": row.row_no,
        "field": FIELD_LABEL.get(value.field, value.field),
        "raw_text": value.raw_text,
        "source": {
            "input_id": str(value.source_input_id) if value.source_input_id else None,
            "locator": locator,
        },
        "actual_text": actual,
        **({"note": note} if note else {}),
    }


async def mark_verified(session: AsyncSession, inquiry_id: uuid.UUID) -> None:
    """照合が通った値に時刻を入れる（④ の裏づけ。監査用）。"""
    from datetime import datetime, timezone

    stmt = (
        select(ItemValue)
        .join(ItemRow, ItemValue.item_row_id == ItemRow.id)
        .where(ItemRow.inquiry_id == inquiry_id, ItemValue.state == "extracted")
    )
    now = datetime.now(timezone.utc)
    for value in (await session.execute(stmt)).scalars():
        value.verified_at = now
