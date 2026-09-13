"""エージェント実行の記録（agent_runs）。0-7 でプロセス内に持っていた分を DB に落とす。

`jobs.py` から呼ぶ。実行はリクエストとは別のタスクで進むので、**自前のセッション**を使う。
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.agent.trace import TraceRecorder
from app.core.database import AsyncSessionLocal
from app.models import AgentRun, Inquiry
from app.repositories.agent_run_repository import AgentRunRepository

MAX_ATTEMPTS = 2
# 案件に付く「読み取り不可の理由」のうち、実行の止まり方から決まるもの（④ UNREADABLE_REASONS）
STOP_REASON_TO_UNREADABLE = {
    "max_turns": "max_turns",
    "inner_timeout": "timeout",
    "inactivity_timeout": "timeout",
    "outer_timeout": "timeout",
}
# agent_runs.failure_reason に入れてよいのは判定由来の2つだけ
RUN_FAILURE_REASONS = ("illegible", "no_items")


async def next_attempt_no(inquiry_id: uuid.UUID) -> int:
    """既存の実行回数 + 1（上限2。⑤ #7）。"""
    async with AsyncSessionLocal() as session:
        used = await AgentRunRepository(session).count_for_inquiry(inquiry_id)
    return min(used + 1, MAX_ATTEMPTS)


async def create_run(
    *,
    run_id: str,
    inquiry_id: uuid.UUID,
    attempt_no: int,
    model: str,
    max_turns: int,
    trace_path: str,
) -> None:
    """実行の開始を記録する。**タスクを作る前に書く**ので、#8 は直後から読める。"""
    async with AsyncSessionLocal() as session:
        session.add(
            AgentRun(
                run_id=uuid.UUID(run_id),
                inquiry_id=inquiry_id,
                attempt_no=attempt_no,
                model=model,
                max_turns=max_turns,
                status="running",
                started_at=datetime.now(timezone.utc),
                trace_path=trace_path,
            )
        )
        await session.commit()


async def finish_run(*, run_id: str, stop_reason: str, turns: int | None) -> None:
    """実行の終了を記録する。止まり方から決まる「読み取り不可」も案件に付ける。"""
    async with AsyncSessionLocal() as session:
        run = await AgentRunRepository(session).get_by_run_id(uuid.UUID(run_id))
        if run is None:
            return
        run.status = "finished"
        run.stop_reason = stop_reason
        run.turns = turns
        run.finished_at = datetime.now(timezone.utc)

        inquiry = await session.get(Inquiry, run.inquiry_id)
        if inquiry is not None:
            if inquiry.unreadable_reason in RUN_FAILURE_REASONS:
                # check_completion が付けた失敗理由をそのまま実行にも残す
                run.failure_reason = inquiry.unreadable_reason
            unreadable = STOP_REASON_TO_UNREADABLE.get(stop_reason)
            if unreadable is None and stop_reason == "failed":
                # `failed` は本来 check_completion が理由（判読不能・明細なし）を付けて終わる。
                # 付いていないのは予期しない例外で落ちた場合で、**放っておくと案件が
                # 「読み取り中」のまま残る**（close_orphaned_runs と同じ症状）。打ち切りと同じ扱いにし、
                # 再実行できるようにする（④ の理由は illegible / no_items / timeout / max_turns の4つ）
                unreadable = "timeout"
            if unreadable and inquiry.status in ("received", "reading"):
                # 強制停止はエージェントが自分で記録できないので、サーバー側で付ける
                inquiry.status = "unreadable"
                inquiry.unreadable_reason = unreadable
        await session.commit()


async def close_orphaned_runs() -> int:
    """プロセスが落ちた・再起動したときに残る「実行中」の記録を閉じる。

    実行はプロセス内の asyncio タスクなので、サーバーが再起動すると続きは走らない。
    記録だけ running のまま残ると、一覧と処理状況が永遠に「読み取り中」に見える。
    起動時に1度だけ呼び、**failed として閉じる**（案件は読み取り不可にする）。
    """
    async with AsyncSessionLocal() as session:
        runs = list(
            (await session.execute(select(AgentRun).where(AgentRun.status == "running"))).scalars()
        )
        for run in runs:
            run.status = "finished"
            run.stop_reason = "failed"
            run.finished_at = datetime.now(timezone.utc)
            # トレースにも終わりを残す（`.claude/rules/agent-development.md` §3
            # 「すべての実行を記録する」。プロセスが死ぬと runner は run_end を書けないため、
            # ここで書かないと**停止理由の無いトレース**が残り、⑥ 3章で評価できない）
            TraceRecorder(run_id=str(run.run_id)).record_run_end(
                "failed", detail="サーバーが停止したため実行が中断された（起動時に回収）"
            )
            inquiry = await session.get(Inquiry, run.inquiry_id)
            if inquiry is not None and inquiry.status in ("received", "reading"):
                inquiry.status = "unreadable"
                inquiry.unreadable_reason = "timeout"
        await session.commit()
    return len(runs)
