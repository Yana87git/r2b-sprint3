"""確定（⑤ #17）のスキーマ。"""
from pydantic import BaseModel, Field


class ConfirmResponse(BaseModel):
    inquiry_id: str
    confirmed_at: str
    row_count: int
    pending_row_count: int = Field(description="「顧客回答待ち」として出力した行数")
    download_path: str
