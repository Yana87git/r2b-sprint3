"""品目リスト（Excel）の出力（⑤ #17）。確定した行だけを1枚のシートに書く。"""
import uuid
from pathlib import Path

from openpyxl import Workbook

from app.models import ItemRow, ItemValue

HEADERS = ["No", "品目名", "型番", "数量", "単位", "納期", "備考", "状態"]
PENDING_LABEL = "顧客回答待ち"


def _due_text(value: ItemValue | None) -> str:
    """納期の値域 (a)(b)(c) を人が読む形にする（② FUNC-02）。"""
    if value is None:
        return ""
    if value.due_kind == "fixed_date" and value.due_start:
        return value.due_start.isoformat()
    if value.due_kind == "month_range" and value.due_start and value.due_end:
        return f"{value.due_start.isoformat()}〜{value.due_end.isoformat()}"
    if value.due_kind == "needs_confirmation" or value.state == "needs_confirmation":
        return PENDING_LABEL
    return value.value_text or ""


def _text(value: ItemValue | None) -> str:
    if value is None:
        return ""
    if value.state == "needs_confirmation":
        return PENDING_LABEL
    return value.value_text or value.raw_text or ""


def build_workbook(
    title: str, rows: list[ItemRow], values_by_row: dict[uuid.UUID, list[ItemValue]]
) -> tuple[Workbook, int]:
    """品目リストを作り、「顧客回答待ち」の行数も返す。"""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "品目リスト"
    sheet.append([title])
    sheet.append([])
    sheet.append(HEADERS)

    pending = 0
    for index, row in enumerate(rows, start=1):
        by_field = {v.field: v for v in values_by_row.get(row.id, [])}
        is_pending = any(v.state == "needs_confirmation" for v in by_field.values())
        pending += 1 if is_pending else 0
        quantity = by_field.get("quantity")
        sheet.append(
            [
                index,
                _text(by_field.get("item_name")),
                _text(by_field.get("model_no")),
                float(quantity.quantity_value)
                if quantity is not None and quantity.quantity_value is not None
                else _text(quantity),
                _text(by_field.get("unit")),
                _due_text(by_field.get("due_date")),
                _text(by_field.get("note")),
                PENDING_LABEL if is_pending else "",
            ]
        )

    for column, width in zip("ABCDEFGH", (5, 28, 20, 10, 8, 24, 24, 14), strict=True):
        sheet.column_dimensions[column].width = width
    return workbook, pending


def save(workbook: Workbook, directory: Path, inquiry_id: uuid.UUID) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"品目リスト_{inquiry_id}.xlsx"
    workbook.save(path)
    return path
