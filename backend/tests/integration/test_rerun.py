"""⑤ #7 再実行。打ち切りで終わった案件だけ、1回まで（② FUNC-07）。"""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import AgentRun, Inquiry, InquiryInput
from app.services import agent_run_service, rerun_service
from app.services.dev_fixtures import register_d1


@pytest.fixture
async def unreadable():
    """タイムアウトで打ち切られた案件（実行記録1件）。"""
    async with AsyncSessionLocal() as session:
        inquiry = await register_d1(session)
        inquiry.status = "unreadable"
        inquiry.unreadable_reason = "timeout"
        session.add(
            AgentRun(
                run_id=uuid.uuid4(),
                inquiry_id=inquiry.id,
                attempt_no=1,
                model="claude-sonnet-5",
                max_turns=30,
                status="finished",
                stop_reason="inner_timeout",
                started_at=datetime.now(timezone.utc),
                finished_at=datetime.now(timezone.utc),
                trace_path="traces/dummy.jsonl",
            )
        )
        await session.commit()
        yield inquiry.id
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


async def _set(inquiry_id: uuid.UUID, **fields) -> None:
    async with AsyncSessionLocal() as session:
        inquiry = await session.get(Inquiry, inquiry_id)
        for key, value in fields.items():
            setattr(inquiry, key, value)
        await session.commit()


@pytest.mark.parametrize(
    ("reason", "expected"),
    [("illegible", "illegible"), ("no_items", "no_items")],
)
async def test_not_retryable_reasons(unreadable, reason, expected) -> None:
    """判読不能・明細なしは読み直しても変わらないので再実行させない。"""
    await _set(unreadable, unreadable_reason=reason)
    async with AsyncSessionLocal() as session:
        with pytest.raises(rerun_service.RerunError) as excinfo:
            await rerun_service.start_rerun(session, unreadable)
    assert (excinfo.value.code, excinfo.value.reason) == ("RETRY_NOT_ALLOWED", expected)


async def test_already_retried(unreadable) -> None:
    """再実行は1回まで（実行記録が2件あるともう始められない）。"""
    async with AsyncSessionLocal() as session:
        session.add(
            AgentRun(
                run_id=uuid.uuid4(),
                inquiry_id=unreadable,
                attempt_no=2,
                model="claude-sonnet-5",
                max_turns=30,
                status="finished",
                stop_reason="inner_timeout",
                started_at=datetime.now(timezone.utc),
                trace_path="traces/dummy2.jsonl",
            )
        )
        await session.commit()
    async with AsyncSessionLocal() as session:
        with pytest.raises(rerun_service.RerunError) as excinfo:
            await rerun_service.start_rerun(session, unreadable)
    assert (excinfo.value.code, excinfo.value.reason) == ("RETRY_NOT_ALLOWED", "already_retried")


async def test_run_in_progress(unreadable) -> None:
    async with AsyncSessionLocal() as session:
        run = (
            await session.execute(select(AgentRun).where(AgentRun.inquiry_id == unreadable))
        ).scalar_one()
        run.status = "running"
        await session.commit()
    async with AsyncSessionLocal() as session:
        with pytest.raises(rerun_service.RerunError) as excinfo:
            await rerun_service.start_rerun(session, unreadable)
    assert excinfo.value.code == "RUN_IN_PROGRESS"


async def test_confirmed_is_rejected(unreadable) -> None:
    await _set(unreadable, status="confirmed")
    async with AsyncSessionLocal() as session:
        with pytest.raises(rerun_service.RerunError) as excinfo:
            await rerun_service.start_rerun(session, unreadable)
    assert excinfo.value.code == "ALREADY_CONFIRMED"


async def test_timeout_starts_a_second_attempt(unreadable, monkeypatch) -> None:
    """タイムアウトなら再実行できる。案件と入力の状態は投入直後に戻る。"""
    started: dict = {}

    async def _fake_start(prompt, *, system_prompt, inquiry_id=None, attempt_no=1, scenario=None):
        started.update(inquiry_id=inquiry_id, attempt_no=attempt_no)
        return str(uuid.uuid4())

    monkeypatch.setattr("app.services.inquiry_intake_service.jobs.start_agent_job", _fake_start)
    async with AsyncSessionLocal() as session:
        inputs = (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == unreadable))
        ).scalars()
        for i in inputs:
            i.status = "unreadable"
            i.unreadable_reason = "illegible"
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await rerun_service.start_rerun(session, unreadable)
    assert result["attempt_no"] == 2
    assert started["attempt_no"] == 2

    async with AsyncSessionLocal() as session:
        inquiry = await session.get(Inquiry, unreadable)
        inputs = list(
            (
                await session.execute(
                    select(InquiryInput).where(InquiryInput.inquiry_id == unreadable)
                )
            ).scalars()
        )
    assert (inquiry.status, inquiry.unreadable_reason) == ("received", None)
    assert all(i.status == "pending" and i.unreadable_reason is None for i in inputs)


async def test_inquiry_is_kept_when_start_fails(unreadable, monkeypatch) -> None:
    """再実行の起動に失敗しても、**案件は消さない**（投入のときとは違う）。"""

    async def _boom(*args, **kwargs):
        raise RuntimeError("起動できない")

    monkeypatch.setattr("app.services.inquiry_intake_service.jobs.start_agent_job", _boom)
    async with AsyncSessionLocal() as session:
        with pytest.raises(RuntimeError):
            await rerun_service.start_rerun(session, unreadable)
    async with AsyncSessionLocal() as session:
        assert await session.get(Inquiry, unreadable) is not None


@pytest.mark.parametrize(
    ("stop_reason", "expected"),
    [("max_turns", "max_turns"), ("inner_timeout", "timeout"), ("failed", "timeout")],
)
async def test_finish_run_marks_unreadable(stop_reason, expected) -> None:
    """打ち切り（と予期しない失敗）は案件を「読み取り不可」にする。

    `agent.md` の停止理由の表どおりに理由を付ける。**読み取り中のまま残さない**
    （残ると一覧と処理状況が永遠に「読み取り中」に見える）。
    """
    run_id = uuid.uuid4()
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
                trace_path="traces/dummy.jsonl",
            )
        )
        await session.commit()
        inquiry_id = inquiry.id

    await agent_run_service.finish_run(run_id=str(run_id), stop_reason=stop_reason, turns=3)

    async with AsyncSessionLocal() as session:
        saved = await session.get(Inquiry, inquiry_id)
        assert (saved.status, saved.unreadable_reason) == ("unreadable", expected)
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
        await session.commit()
