"""投入（⑤ #4）のスキーマ。型の SSOT はここ（OpenAPI 経由で orval に渡る）。"""
from pydantic import BaseModel, Field


class AcceptedInput(BaseModel):
    input_id: str
    display_name: str
    format: str = Field(description="excel / pdf / word / mail_body")
    message: str = Field(description="「Excel形式として受け付けました」に相当する文言")


class InquiryCreateResponse(BaseModel):
    inquiry_id: str
    inputs: list[AcceptedInput]
    run_id: str = Field(description="自動で始めたエージェント実行のID（attempt_no = 1）")


class InquiryListItem(BaseModel):
    inquiry_id: str
    title: str
    status: str
    unreadable_reason: str | None
    submitted_at: str
    submitted_by_name: str
    formats: list[str]
    total_rows: int
    unchecked_rows: int
    unreadable_input_count: int
    pending_row_count: int | None = Field(description="確定済みの案件の「顧客回答待ち」の行数")
    latest_run_id: str | None = Field(description="最後の実行（SCR-04 へ進むときに使う）")


class InquiryListResponse(BaseModel):
    counts: dict[str, int] = Field(description="状況ごとの件数（タブの数字）")
    inquiries: list[InquiryListItem]


class InputExclusionResponse(BaseModel):
    input_id: str
    display_name: str
    status: str
    unreadable_reason: str | None
    excluded: bool = Field(description="除外したか（確定の判定で数えない）")
