"""実行記録（agent_runs）とトレースの後始末。

サーバーが落ちると runner は `run_end` を書けない。起動時の回収（`close_orphaned_runs`）が
**DB とトレースの両方**を閉じることを固定する（⑥ 3章はトレースだけを見て停止理由を判定する）。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete

from app.agent.trace import TraceRecorder
from app.core.database import AsyncSessionLocal
from app.models import AgentRun, Inquiry
from app.services import agent_run_service
from app.services.dev_fixtures import register_d1


async def test_close_orphaned_runs_writes_run_end() -> None:
    run_id = uuid.uuid4()
    trace = TraceRecorder(run_id=str(run_id))
    trace.record_run_start(attempt_no=1, model="claude-sonnet-5", max_turns=30)

    async with AsyncSessionLocal() as session:
        inquiry = await register_d1(session)
        inquiry.status = "reading"
        session.add(
            AgentRun(
                run_id=run_id,
                inquiry_id=inquiry.id,
                attempt_no=1,
                model="claude-sonnet-5",
                max_turns=30,
                status="running",
                started_at=datetime.now(timezone.utc),
                trace_path=str(trace.path),
            )
        )
        await session.commit()
        inquiry_id = inquiry.id

    try:
        assert await agent_run_service.close_orphaned_runs() >= 1

        ends = [r for r in TraceRecorder(run_id=str(run_id)).read() if r["event"] == "run_end"]
        assert len(ends) == 1
        assert ends[0]["stop_reason"] == "failed"

        async with AsyncSessionLocal() as session:
            saved = await session.get(Inquiry, inquiry_id)
            assert (saved.status, saved.unreadable_reason) == ("unreadable", "timeout")
    finally:
        trace.path.unlink(missing_ok=True)
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
            await session.commit()
