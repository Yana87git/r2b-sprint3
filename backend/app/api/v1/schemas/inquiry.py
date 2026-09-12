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
