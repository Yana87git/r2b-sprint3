"""エージェント実行のジョブ管理（Sprint 3 の実行の型）。

- 起動: start_agent_job() が run_id を即返し、実行はバックグラウンドで進む（⑤ #4 は 202 を返す）
- 監視: get_job(run_id) と read_progress(run_id)。進捗の実体はトレースそのもの
- **外側タイムアウトはこの層が持つ。** trace を先に作るので、外側発火もトレースに残る
- ジョブ一覧はプロセス内保持。永続化は 04 の agent_runs（明日のツール実装と一緒に繋ぐ）
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import uuid as _uuid

from app.agent import definition
from app.agent.context import set_current_inquiry_id
from app.agent.runner import AgentRunResult, run_agent
from app.agent.trace import TraceRecorder


@dataclass
class AgentJob:
    run_id: str
    status: str  # running / completed / failed / max_turns / *_timeout
    started_at: str
    inquiry_id: str | None = None
    attempt_no: int = 1
    result: AgentRunResult | None = None
    task: asyncio.Task | None = field(default=None, repr=False)


_jobs: dict[str, AgentJob] = {}


def start_agent_job(
    prompt: str,
    *,
    system_prompt: str,
    inquiry_id: str | None = None,
    attempt_no: int = 1,
    scenario: str | None = None,
) -> str:
    """バックグラウンドで起動し、run_id を即返す（完了を待たない）。"""
    trace = TraceRecorder(inquiry_id=inquiry_id, scenario=scenario)
    job = AgentJob(
        run_id=trace.run_id,
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        inquiry_id=inquiry_id,
        attempt_no=attempt_no,
    )
    _jobs[trace.run_id] = job
    # タスクを作る前に設定する（作成時のコンテキストが子タスクへ伝わる）
    set_current_inquiry_id(_uuid.UUID(inquiry_id) if inquiry_id else None)
    job.task = asyncio.create_task(_execute(job, prompt, system_prompt=system_prompt, trace=trace))
    return trace.run_id


async def _execute(job: AgentJob, prompt: str, *, system_prompt: str, trace: TraceRecorder) -> None:
    try:
        # 外側タイムアウト: 内側（runner）が機能しなかったときの最後の砦
        result = await asyncio.wait_for(
            run_agent(
                prompt,
                system_prompt=system_prompt,
                attempt_no=job.attempt_no,
                trace=trace,
            ),
            definition.OUTER_TIMEOUT_S,
        )
        job.result = result
        job.status = result.stop_reason
    except TimeoutError:
        # 外側発火 = 内側の異常。握りつぶさずバグとして調査する（⑥ TEST-18 は発火しないことを確かめる）
        trace.record_run_end(
            "outer_timeout", detail=f"{definition.OUTER_TIMEOUT_S}s 超過（内側が機能せず）"
        )
        job.status = "outer_timeout"
    except Exception as e:  # 予期しない例外もジョブとトレースに残す
        trace.record_run_end("failed", detail=repr(e))
        job.status = "failed"


def get_job(run_id: str) -> AgentJob | None:
    return _jobs.get(run_id)


def read_progress(run_id: str, limit: int = 20) -> list[dict[str, Any]]:
    """進捗＝トレースの末尾。ポーリング応答にそのまま載せる。"""
    records = TraceRecorder(run_id=run_id).read()
    return records[-limit:]
