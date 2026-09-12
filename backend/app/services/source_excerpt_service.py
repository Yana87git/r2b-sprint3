"""読み取り元の取得（⑤ #14）。位置のまわりの原本を抜粋して返す。

**この GET は状態を書く**（③ SCR-06 を開いた事実を抜き取りとして記録する）。
確信が高い行を1回目に開いたときだけ `item_rows.source_opened_at` を入れる。
一括確認の抜き取り判定（min(3, N) 行）がこの記録を数えるため、画面の操作ではなく
サーバー側で数える必要がある（② FUNC-04・KPI7）。
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InquiryInput, ItemRow, ItemValue, ValueClue
from app.services.input_reader import InputNotReadableError, read_input
from app.services.source_verify_service import (
    LOCATOR_EXCEL,
    LOCATOR_MAIL,
    LOCATOR_PDF,
    LOCATOR_WORD_PARA,
    LOCATOR_WORD_TABLE,
)

# 抜粋の広さ（前後の行数）
EXCEL_ROWS_AROUND = 2
LINES_AROUND = 4
# 一括確認に必要な抜き取り（④ と同じ数え方）
REQUIRED_SAMPLES = 3


async def get_source(
    session: AsyncSession, inquiry_id: uuid.UUID, value_id: uuid.UUID
) -> dict[str, Any] | None:
    """値1つぶんの読み取り元。値が他の案件のものなら None（ガードレール）。"""
    value = await session.get(ItemValue, value_id)
    if value is None:
        return None
    row = await session.get(ItemRow, value.item_row_id)
    if row is None or row.inquiry_id != inquiry_id:
        return None

    clues = list(
        (
            await session.execute(select(ValueClue).where(ValueClue.item_value_id == value.id))
        ).scalars()
    )

    payload: dict[str, Any] = {
        "value_id": str(value.id),
        "row_id": str(row.id),
        "row_no": row.row_no,
        "field": value.field,
        "state": value.state,
        "confidence": value.confidence,
        "raw_text": value.raw_text,
        "value_text": value.value_text,
        "due_kind": value.due_kind,
        "due_start": value.due_start.isoformat() if value.due_start else None,
        "due_end": value.due_end.isoformat() if value.due_end else None,
        "clues": [
            {"clue": c.clue, "detail": c.detail} for c in sorted(clues, key=lambda c: c.clue)
        ],
        "source": None,
        "excerpt": None,
    }

    if value.source_input_id is not None:
        input_ = await session.get(InquiryInput, value.source_input_id)
        label = (value.locator or {}).get("label", "")
        if input_ is not None:
            payload["source"] = {
                "input_id": str(input_.id),
                "input_name": input_.display_name,
                "format": input_.format,
                "locator_label": label,
            }
            payload["excerpt"] = _excerpt(input_, label)

    # 抜き取りの記録（確信が高い行を1回目に開いたときだけ）
    opened_now = False
    if row.classification == "high_confidence" and row.source_opened_at is None:
        row.source_opened_at = datetime.now(timezone.utc)
        opened_now = True
    await session.flush()

    payload["sampling"] = await _sampling(session, inquiry_id) | {"opened_now": opened_now}
    return payload


async def _sampling(session: AsyncSession, inquiry_id: uuid.UUID) -> dict[str, int]:
    """抜き取りの数え方は ④ と同じ: N = 確信が高く、除外していない行（確認済みも含む）。"""
    rows = list(
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
    return {
        "sampled_rows": sum(1 for r in rows if r.source_opened_at is not None),
        "required_samples": min(REQUIRED_SAMPLES, len(rows)),
        "confident_rows": len(rows),
    }


def _excerpt(input_: InquiryInput, label: str) -> dict[str, Any] | None:
    """位置のまわりを抜き出す。Excel は表、それ以外は行の並び。"""
    try:
        if (m := LOCATOR_EXCEL.match(label)) and input_.format == "excel":
            return _excel_excerpt(input_, m.group("sheet"), m.group("col"), int(m.group("row")))
        if (m := LOCATOR_PDF.match(label)) and input_.format == "pdf":
            return _lines_excerpt(
                input_, label, page=int(m.group("page")), line=int(m.group("line"))
            )
        if LOCATOR_MAIL.match(label) and input_.kind == "mail_body":
            return _lines_excerpt(
                input_, label, page=1, line=int(LOCATOR_MAIL.match(label).group("line"))
            )
        if (
            LOCATOR_WORD_TABLE.match(label) or LOCATOR_WORD_PARA.match(label)
        ) and input_.format == "word":
            return _word_excerpt(input_, label)
    except InputNotReadableError:
        return None
    return None


def _excel_excerpt(input_: InquiryInput, sheet: str, col: str, row_no: int) -> dict[str, Any]:
    start = max(1, row_no - EXCEL_ROWS_AROUND)
    result = read_input(input_, sheet=sheet, start=start, limit=EXCEL_ROWS_AROUND * 2 + 1)
    grid: dict[int, dict[str, str]] = {}
    columns: list[str] = []
    for cell in result["cells"]:
        m = LOCATOR_EXCEL.match(cell["locator"])
        if not m:
            continue
        r, c = int(m.group("row")), m.group("col")
        grid.setdefault(r, {})[c] = cell["text"]
        if c not in columns:
            columns.append(c)
    columns.sort(key=_column_index)
    return {
        "kind": "grid",
        "columns": columns,
        "rows": [
            {
                "no": r,
                "cells": [
                    {"col": c, "text": grid[r].get(c, ""), "hit": r == row_no and c == col}
                    for c in columns
                ],
            }
            for r in sorted(grid)
        ],
    }


def _lines_excerpt(input_: InquiryInput, label: str, *, page: int, line: int) -> dict[str, Any]:
    start = max(1, line - LINES_AROUND)
    result = read_input(input_, page=page, start=start, limit=LINES_AROUND * 2 + 1)
    return {
        "kind": "lines",
        "columns": [],
        "rows": [
            {
                "no": index,
                "text": cell["text"],
                "hit": cell["locator"] == label,
                "locator": cell["locator"],
            }
            for index, cell in enumerate(result["cells"], start=start)
        ],
    }


def _word_excerpt(input_: InquiryInput, label: str) -> dict[str, Any]:
    """Word は表と段落が混ざるので、位置の前後を並び順で切り出す。"""
    result = read_input(input_, start=1, limit=300)
    cells = result["cells"]
    hit = next((i for i, c in enumerate(cells) if c["locator"] == label), None)
    if hit is None:
        return {"kind": "lines", "columns": [], "rows": []}
    window = cells[max(0, hit - LINES_AROUND) : hit + LINES_AROUND + 1]
    return {
        "kind": "lines",
        "columns": [],
        "rows": [
            {"no": index, "text": c["text"], "hit": c["locator"] == label, "locator": c["locator"]}
            for index, c in enumerate(window, start=max(1, hit - LINES_AROUND + 1))
        ],
    }


def _column_index(col: str) -> int:
    value = 0
    for char in col:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value
