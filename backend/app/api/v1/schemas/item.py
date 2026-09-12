"""品目リスト案（⑤ #9・#11）のスキーマ。"""
from typing import Any

from pydantic import BaseModel, Field


class ValueSource(BaseModel):
    input_id: str | None
    locator: dict[str, Any] | None = Field(description="形式ごとの位置（④ item_values.locator）")


class ValueClueOut(BaseModel):
    clue: str = Field(description="H1〜H4")
    detail: str | None


class ItemValueOut(BaseModel):
    value_id: str
    state: str = Field(description="extracted / needs_confirmation")
    confidence: str = Field(description="high / low")
    raw_text: str | None
    value_text: str | None
    quantity_value: float | None
    due_kind: str | None
    due_start: str | None
    due_end: str | None
    source: ValueSource | None
    clues: list[ValueClueOut]


class ItemRowOut(BaseModel):
    row_id: str
    row_no: int
    classification: str = Field(description="needs_confirmation / low_confidence / high_confidence")
    check_state: str
    excluded: bool
    source_opened: bool
    values: dict[str, ItemValueOut]


class ItemSummary(BaseModel):
    total_rows: int
    excluded_rows: int
    unchecked_rows: int
    sampled_rows: int = Field(description="読み取り元を開いた行の数（一括確認の抜き取り判定）")
    by_classification: dict[str, int]
    unreadable_input_count: int = 0


class ItemListResponse(BaseModel):
    inquiry_id: str
    status: str
    review_started_at: str | None
    rows: list[ItemRowOut]
    summary: ItemSummary


class RowCheckResponse(BaseModel):
    row_id: str
    check_state: str
    checked_at: str | None
    summary: ItemSummary
