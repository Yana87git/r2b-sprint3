"""⑤ の API 5本（#4・#8・#9・#11・#17）。エージェントの起動は差し替えて動かす。"""
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.main import app
from app.models import AgentRun, Inquiry, InquiryInput, ItemRow
from app.services import agent_run_service, dev_fixtures, inquiry_intake_service
from app.services.item_draft_service import replace_rows
from tests.integration.test_check_completion import _good_row

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
async def api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def fake_agent(monkeypatch):
    """本物のエージェントは動かさず、実行記録だけ本物と同じ手順で作る。"""
    started: list[str] = []

    async def _start(prompt, *, system_prompt, inquiry_id=None, attempt_no=1, scenario=None):
        run_id = str(uuid.uuid4())
        await agent_run_service.create_run(
            run_id=run_id,
            inquiry_id=uuid.UUID(inquiry_id),
            attempt_no=attempt_no,
            model="claude-sonnet-5",
            max_turns=30,
            trace_path=f"traces/{run_id}.jsonl",
        )
        started.append(run_id)
        return run_id

    monkeypatch.setattr(inquiry_intake_service.jobs, "start_agent_job", _start)
    return started


@pytest.fixture
async def created(api, fake_agent):
    """D1 の Excel を投入して案件を1件作る（後始末つき）。"""
    content = (FIXTURES / "d1" / "normal_excel.xlsx").read_bytes()
    response = await api.post(
        "/api/v1/inquiries",
        files={"files": ("normal_excel.xlsx", content, "application/vnd.ms-excel")},
    )
    assert response.status_code == 202
    body = response.json()
    yield body
    await _delete_inquiry(uuid.UUID(body["inquiry_id"]))


async def _delete_inquiry(inquiry_id: uuid.UUID) -> None:
    """案件と、保管した原本・出力 Excel を消す（テストが積み残しを作らない）。"""
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
        await session.commit()
    shutil.rmtree(inquiry_intake_service.storage_root() / str(inquiry_id), ignore_errors=True)


# --- #4 投入 ---------------------------------------------------------------


async def test_create_inquiry_starts_agent(created) -> None:
    assert created["inputs"][0]["message"] == "Excel形式として受け付けました"
    async with AsyncSessionLocal() as session:
        run = (
            await session.execute(
                select(AgentRun).where(AgentRun.run_id == uuid.UUID(created["run_id"]))
            )
        ).scalar_one()
        assert (run.attempt_no, run.status, run.stop_reason) == (1, "running", None)


async def test_create_inquiry_saves_original(created) -> None:
    async with AsyncSessionLocal() as session:
        input_ = (
            await session.execute(
                select(InquiryInput).where(
                    InquiryInput.inquiry_id == uuid.UUID(created["inquiry_id"])
                )
            )
        ).scalar_one()
        assert Path(input_.storage_path).exists()


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"files": ("list.csv", b"a,b", "text/csv")}, "UNSUPPORTED_FORMAT"),
        ({"files": ("old.xls", b"x", "application/vnd.ms-excel")}, "UNSUPPORTED_FORMAT"),
    ],
)
async def test_create_inquiry_rejects_format(api, fake_agent, payload, code) -> None:
    response = await api.post("/api/v1/inquiries", files=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == code


async def test_create_inquiry_requires_input(api, fake_agent) -> None:
    response = await api.post("/api/v1/inquiries", data={"mail_body": "   "})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "NO_INPUT"


async def test_create_inquiry_accepts_mail_body_only(api, fake_agent) -> None:
    response = await api.post("/api/v1/inquiries", data={"mail_body": "お見積のお願い\n以上"})
    assert response.status_code == 202
    body = response.json()
    assert body["inputs"][0]["message"] == "メール本文として受け付けました"
    await _delete_inquiry(uuid.UUID(body["inquiry_id"]))


# --- #8 進み具合 -----------------------------------------------------------


async def test_run_status_while_running(api, created) -> None:
    response = await api.get(f"/api/v1/runs/{created['run_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["run_status"] == "running"
    assert (body["inputs_done"], body["inputs_total"]) == (0, 1)
    assert body["eta_seconds"] > 0
    assert body["stop_reason"] is None


async def test_run_status_after_finish(api, created) -> None:
    await agent_run_service.finish_run(run_id=created["run_id"], stop_reason="completed", turns=7)
    response = await api.get(f"/api/v1/runs/{created['run_id']}")
    body = response.json()
    assert (body["run_status"], body["stop_reason"], body["eta_seconds"]) == (
        "finished",
        "completed",
        0,
    )


async def test_run_status_timeout_marks_inquiry_unreadable(api, created) -> None:
    """強制停止はエージェントが記録できないので、サーバー側が案件に付ける。"""
    await agent_run_service.finish_run(
        run_id=created["run_id"], stop_reason="inner_timeout", turns=None
    )
    body = (await api.get(f"/api/v1/runs/{created['run_id']}")).json()
    assert (body["status"], body["unreadable_reason"]) == ("unreadable", "timeout")


async def test_run_status_not_found(api) -> None:
    response = await api.get(f"/api/v1/runs/{uuid.uuid4()}")
    assert response.status_code == 404


# --- #9 / #11 / #17 -------------------------------------------------------


@pytest.fixture
async def reviewable():
    """D1 に品目行を1行入れ、確認待ちにした案件。"""
    async with AsyncSessionLocal() as session:
        inquiry = await dev_fixtures.register_d1(session)
        await session.commit()
        excel = (
            await session.execute(
                select(InquiryInput).where(
                    InquiryInput.inquiry_id == inquiry.id, InquiryInput.format == "excel"
                )
            )
        ).scalar_one()
        await replace_rows(session, inquiry.id, [_good_row(excel.id)])
        inquiry.status = "awaiting_review"
        await session.commit()
        yield inquiry.id
    await _delete_inquiry(inquiry.id)


async def test_get_items_records_review_start_once(api, reviewable) -> None:
    first = (await api.get(f"/api/v1/inquiries/{reviewable}/items")).json()
    assert first["review_started_at"] is not None
    assert first["summary"]["unchecked_rows"] == 1
    assert first["rows"][0]["values"]["item_name"]["value_text"] == "深溝玉軸受"
    assert first["rows"][0]["values"]["item_name"]["source"]["locator"] is not None

    # 2回目は何も変えない（表現は DB 由来で変わりうるので、時刻そのものを比べる）
    second = (await api.get(f"/api/v1/inquiries/{reviewable}/items")).json()
    assert datetime.fromisoformat(second["review_started_at"]) == datetime.fromisoformat(
        first["review_started_at"]
    )


async def test_check_row_reduces_unchecked(api, reviewable) -> None:
    rows = (await api.get(f"/api/v1/inquiries/{reviewable}/items")).json()["rows"]
    row_id = rows[0]["row_id"]
    response = await api.post(f"/api/v1/inquiries/{reviewable}/items/{row_id}/check")
    assert response.status_code == 200
    body = response.json()
    assert (body["check_state"], body["summary"]["unchecked_rows"]) == ("checked", 0)


async def test_check_row_of_another_inquiry_is_404(api, reviewable) -> None:
    response = await api.post(
        f"/api/v1/inquiries/{reviewable}/items/{uuid.uuid4()}/check",
    )
    assert response.status_code == 404


async def test_confirm_requires_checked_rows(api, reviewable) -> None:
    response = await api.post(f"/api/v1/inquiries/{reviewable}/confirm")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert (detail["code"], detail["unchecked_rows"]) == ("UNCHECKED_ROWS_REMAIN", 1)


async def test_confirm_reports_unreadable_input_first(api, reviewable) -> None:
    """未確認も読み取り不可も残っているときは、読み取り不可を先に返す。"""
    async with AsyncSessionLocal() as session:
        pdf = (
            await session.execute(
                select(InquiryInput).where(
                    InquiryInput.inquiry_id == reviewable, InquiryInput.format == "pdf"
                )
            )
        ).scalar_one()
        pdf.status = "unreadable"
        pdf.unreadable_reason = "illegible"
        await session.commit()
    response = await api.post(f"/api/v1/inquiries/{reviewable}/confirm")
    assert response.json()["detail"]["code"] == "UNREADABLE_INPUT_REMAINS"


async def test_confirm_outputs_excel(api, reviewable) -> None:
    rows = (await api.get(f"/api/v1/inquiries/{reviewable}/items")).json()["rows"]
    await api.post(f"/api/v1/inquiries/{reviewable}/items/{rows[0]['row_id']}/check")

    response = await api.post(f"/api/v1/inquiries/{reviewable}/confirm")
    assert response.status_code == 200
    body = response.json()
    assert (body["row_count"], body["pending_row_count"]) == (1, 0)
    assert body["download_path"].endswith("/export")

    async with AsyncSessionLocal() as session:
        inquiry = await session.get(Inquiry, reviewable)
        assert inquiry.status == "confirmed"
        assert inquiry.confirmed_at is not None

    again = await api.post(f"/api/v1/inquiries/{reviewable}/confirm")
    assert again.json()["detail"]["code"] == "ALREADY_CONFIRMED"


async def test_check_row_after_confirm_is_rejected(api, reviewable) -> None:
    rows = (await api.get(f"/api/v1/inquiries/{reviewable}/items")).json()["rows"]
    row_id = rows[0]["row_id"]
    await api.post(f"/api/v1/inquiries/{reviewable}/items/{row_id}/check")
    await api.post(f"/api/v1/inquiries/{reviewable}/confirm")

    response = await api.post(f"/api/v1/inquiries/{reviewable}/items/{row_id}/check")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ALREADY_CONFIRMED"


async def test_rows_are_deleted_with_inquiry(api, created) -> None:
    """後始末が効いていること（テストが積み残しを作らない）。"""
    async with AsyncSessionLocal() as session:
        count = len(
            (
                await session.execute(
                    select(ItemRow).where(ItemRow.inquiry_id == uuid.UUID(created["inquiry_id"]))
                )
            )
            .scalars()
            .all()
        )
    assert count == 0
