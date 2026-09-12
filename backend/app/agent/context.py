"""実行中の案件IDを、ツールにサーバー側から渡すための入れ物。

**案件IDは LLM の引数では受け取らない**（agent.md ガードレール「他の案件のデータに触れない」）。
jobs.py が実行の前にここへ設定し、ツールはここから読む。
"""
import uuid
from contextvars import ContextVar

_current_inquiry_id: ContextVar[uuid.UUID | None] = ContextVar("current_inquiry_id", default=None)


def set_current_inquiry_id(inquiry_id: uuid.UUID | None) -> None:
    _current_inquiry_id.set(inquiry_id)


def current_inquiry_id() -> uuid.UUID:
    value = _current_inquiry_id.get()
    if value is None:
        raise RuntimeError("案件IDが設定されていない（jobs.start_agent_job から起動すること）")
    return value
