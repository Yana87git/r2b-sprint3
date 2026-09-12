"""品目リスト案（⑤ #9・#11）のスキーマ。"""
from typing import Any

from pydantic import BaseModel, Field


class ValueSource(BaseModel):
    input_id: str
    input_name: str = Field(description="入力の表示名（例「見積依頼.xlsx」）")
    locator: dict[str, Any] | None = Field(description="形式ごとの位置（④ item_values.locator）")
    locator_label: str = Field(description="画面に出す位置（例「明細!C12」「p.2/14」）")


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


class InputOut(BaseModel):
    input_id: str
    display_name: str
    format: str
    status: str = Field(description="pending / read / read_no_items / unreadable")
    unreadable_reason: str | None
    row_count: int
    excluded: bool


class ItemListResponse(BaseModel):
    inquiry_id: str
    title: str
    status: str
    review_started_at: str | None
    confirmed_at: str | None = None
    confirmed_by_name: str | None = None
    pending_row_count: int | None = Field(default=None, description="「顧客回答待ち」の行数")
    export_row_count: int | None = Field(default=None, description="出力した行数")
    inputs: list[InputOut]
    rows: list[ItemRowOut]
    summary: ItemSummary


class RowCheckResponse(BaseModel):
    row_id: str
    check_state: str
    checked_at: str | None
    summary: ItemSummary


class ExcerptCell(BaseModel):
    col: str
    text: str
    hit: bool


class ExcerptRow(BaseModel):
    no: int
    text: str | None = None
    hit: bool | None = None
    locator: str | None = None
    cells: list[ExcerptCell] | None = None


class Excerpt(BaseModel):
    kind: str = Field(description="grid（Excel の表）/ lines（PDF・Word・メール本文）")
    columns: list[str]
    rows: list[ExcerptRow]


class Sampling(BaseModel):
    sampled_rows: int = Field(description="読み取り元を開いた行の数")
    required_samples: int = Field(description="一括確認に必要な抜き取り min(3, N)")
    confident_rows: int = Field(description="N = 確信が高く、除外していない行")
    opened_now: bool = Field(description="この呼び出しで抜き取りとして記録したか")


class ValueSourceResponse(BaseModel):
    value_id: str
    row_id: str
    row_no: int
    field: str
    state: str
    confidence: str
    raw_text: str | None
    value_text: str | None
    due_kind: str | None
    due_start: str | None
    due_end: str | None
    clues: list[ValueClueOut]
    source: dict[str, str] | None
    excerpt: Excerpt | None
    sampling: Sampling


class BulkCheckResponse(BaseModel):
    checked_rows: int = Field(description="この操作で確認済みにした行数")
    summary: ItemSummary


class ItemValueUpdate(BaseModel):
    state: str = Field(default="extracted", description="extracted / needs_confirmation")
    value: str | None = Field(default=None, description="品目名・型番・数量・単位・備考の値")
    kind: str | None = Field(default=None, description="納期の種別 fixed_date / month_range")
    start_date: str | None = None
    end_date: str | None = None


class ItemRowUpdate(BaseModel):
    values: dict[str, ItemValueUpdate] = Field(
        description="直す項目と値。必須5項目は値か「要確認」のどちらか"
    )


class ItemRowUpdateResponse(BaseModel):
    row_id: str
    row_no: int
    classification: str
    check_state: str
    edited_fields: list[str]
