"""実行の進み具合（⑤ #8）のスキーマ。"""
from pydantic import BaseModel, Field


class RunStatusResponse(BaseModel):
    run_id: str
    inquiry_id: str
    attempt_no: int
    run_status: str = Field(description="running / finished")
    status: str | None = Field(description="案件の段階（受付済み／読み取り中／…）")
    inputs_done: int
    inputs_total: int
    eta_seconds: int = Field(description="残り時間の目安。目安を過ぎたら0")
    stop_reason: str | None
    unreadable_reason: str | None


class RerunResponse(BaseModel):
    run_id: str
    attempt_no: int = Field(description="既存の実行回数 + 1（上限2）")
