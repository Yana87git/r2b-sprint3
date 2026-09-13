"""実行中の案件IDを、ツールにサーバー側から渡すための入れ物。

**案件IDは LLM の引数では受け取らない**（agent.md ガードレール「他の案件のデータに触れない」）。
jobs.py が実行の前にここへ設定し、ツールはここから読む。
"""
import uuid
from contextvars import ContextVar

_current_inquiry_id: ContextVar[uuid.UUID | None] = ContextVar("current_inquiry_id", default=None)
# check_completion が最後に返した結果。停止理由を決めるのに使う（agent.md 停止条件の表）
_last_completion: ContextVar[str | None] = ContextVar("last_completion", default=None)
_last_completion_fallback: str | None = None


def set_current_inquiry_id(inquiry_id: uuid.UUID | None) -> None:
    _current_inquiry_id.set(inquiry_id)


def current_inquiry_id() -> uuid.UUID:
    value = _current_inquiry_id.get()
    if value is None:
        raise RuntimeError("案件IDが設定されていない（jobs.start_agent_job から起動すること）")
    return value


def set_last_completion(result: str | None) -> None:
    """`check_completion` の結果を控える（失敗なら stop_reason を failed にするため）。"""
    global _last_completion_fallback
    _last_completion_fallback = result
    _last_completion.set(result)


def last_completion() -> str | None:
    """SDK のツールは別タスクで動くので、ContextVar が空ならモジュール変数を見る。"""
    return _last_completion.get() or _last_completion_fallback
