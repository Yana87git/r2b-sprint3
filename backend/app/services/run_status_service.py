"""実行の進み具合（⑤ #8）。agent_runs と入力の状態から段階・残り時間・停止理由を返す。"""
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.trace import TraceRecorder
from app.models import Inquiry, InquiryInput
from app.repositories.agent_run_repository import AgentRunRepository


def _env_int(name: str, default: int) -> int:
    """評価のときだけ環境変数で上書きする（app/agent/definition.py と同じ考え方）。"""
    raw = os.getenv(name)
    return default if raw is None or raw.strip() == "" else int(raw)


SETTLED_STATUSES = ("read", "read_no_items", "unreadable")
# 残り時間の目安（③ SCR-04「あと約2分」）。D1（入力2件）で約140秒だった実測に合わせる。
# **評価（⑥ TEST-19 #6「目安を過ぎた」）のときだけ環境変数で下げられる。**
# 本番の既定値は 30 秒 ＋ 入力1件あたり 60 秒。下げたまま戻し忘れないこと
ETA_BASE_S = _env_int("ETA_BASE_S", 30)
ETA_PER_INPUT_S = _env_int("ETA_PER_INPUT_S", 60)


async def get_status(session: AsyncSession, run_id: uuid.UUID) -> dict[str, Any] | None:
    run = await AgentRunRepository(session).get_by_run_id(run_id)
    if run is None:
        return None
    inquiry = await session.get(Inquiry, run.inquiry_id)
    inputs = list(
        (
            await session.execute(
                select(InquiryInput).where(InquiryInput.inquiry_id == run.inquiry_id)
            )
        ).scalars()
    )
    # 入力の状態が決まるのは保存のときなので、それだけ見ると読んでいる間ずっと 0 のままになる。
    # トレースの read_file_content（has_more=false = 読み終えた）も数えて、進みを先に見せる。
    # **inquiry_inputs.status は触らない**（状態を変えてよいのは設計どおり check_completion だけ）
    settled = {str(i.id) for i in inputs if i.status in SETTLED_STATUSES}
    done = min(len(settled | _read_finished(str(run.run_id))), len(inputs))

    return {
        "run_id": str(run.run_id),
        "inquiry_id": str(run.inquiry_id),
        "attempt_no": run.attempt_no,
        "run_status": run.status,
        "status": inquiry.status if inquiry else None,
        "inputs_done": done,
        "inputs_total": len(inputs),
        "eta_seconds": eta_seconds(run.status, run.started_at, len(inputs)),
        "stop_reason": run.stop_reason,
        "unreadable_reason": inquiry.unreadable_reason if inquiry else None,
    }


def eta_seconds(run_status: str, started_at: datetime, inputs_total: int) -> int:
    """残り時間の目安。終わっていれば 0、目安を過ぎても 0（画面はそこで文面を切り替える）。"""
    if run_status != "running":
        return 0
    estimate = ETA_BASE_S + ETA_PER_INPUT_S * max(inputs_total, 1)
    elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
    return max(0, int(estimate - elapsed))


def _read_finished(run_id: str) -> set[str]:
    """トレースから「最後まで読み終えた入力のID」を集める。トレースが無ければ空。

    read_file_content の呼び出しと結果は順番に並ぶので、直前の呼び出しの input_id と
    結果の has_more を組にして数える。
    """
    finished: set[str] = set()
    try:
        records = TraceRecorder(run_id=run_id).read()
    except Exception:  # noqa: BLE001 進捗の表示のためにジョブを落とさない
        return finished

    pending_input_id: str | None = None
    for record in records:
        if "read_file_content" not in str(record.get("tool", "")):
            continue
        if record.get("event") == "tool_call":
            pending_input_id = str((record.get("input") or {}).get("input_id") or "") or None
        elif record.get("event") == "tool_result" and pending_input_id:
            summary = record.get("summary")
            if isinstance(summary, dict) and summary.get("has_more") is False:
                finished.add(pending_input_id)
            pending_input_id = None
    return finished
