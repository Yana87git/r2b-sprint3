"""set_file_status（§3-5）。入力に付く理由は判読不能のみ。他案件の入力は触れない。"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput
from app.services.dev_fixtures import register_d1
from app.services.input_status_service import set_status
from app.services.item_draft_service import replace_rows
from tests.integration.test_check_completion import _good_row


@pytest.fixture
async def d1():
    async with AsyncSessionLocal() as session:
        inquiry = await register_d1(session)
        await session.commit()
        inputs = (
            (
                await session.execute(
                    select(InquiryInput).where(InquiryInput.inquiry_id == inquiry.id)
                )
            )
            .scalars()
            .all()
        )
        yield inquiry.id, {i.format: i for i in inputs}
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


async def test_no_items_is_recorded(d1) -> None:
    inquiry_id, inputs = d1
    async with AsyncSessionLocal() as session:
        result = await set_status(
            session, inquiry_id, str(inputs["pdf"].id), "no_items", read_up_to="p.3/3"
        )
        await session.commit()
        assert result["ok"] is True
        assert result["status"] == "read_no_items"
        saved = await session.get(InquiryInput, inputs["pdf"].id)
        assert saved.status == "read_no_items"
        assert saved.unreadable_reason is None  # 明細なしは「読めなかった」ではない
        assert saved.read_range == "p.3/3"


async def test_illegible_records_only_that_reason(d1) -> None:
    inquiry_id, inputs = d1
    async with AsyncSessionLocal() as session:
        result = await set_status(session, inquiry_id, str(inputs["pdf"].id), "illegible")
        await session.commit()
        assert result["ok"] is True
        saved = await session.get(InquiryInput, inputs["pdf"].id)
        assert saved.status == "unreadable"
        assert saved.unreadable_reason == "illegible"


@pytest.mark.parametrize("status", ["timeout", "max_turns", "", None])
async def test_other_reasons_are_rejected(d1, status) -> None:
    """タイムアウト・最大ターン数は案件全体の停止理由。入力には付かない。"""
    inquiry_id, inputs = d1
    async with AsyncSessionLocal() as session:
        result = await set_status(session, inquiry_id, str(inputs["pdf"].id), status)
        assert result["ok"] is False
        saved = await session.get(InquiryInput, inputs["pdf"].id)
        assert saved.status == "pending"


async def test_input_of_another_inquiry_is_rejected(d1) -> None:
    inquiry_id, inputs = d1
    async with AsyncSessionLocal() as session:
        result = await set_status(session, uuid.uuid4(), str(inputs["pdf"].id), "illegible")
        assert result["ok"] is False
        assert "この案件" in result["error"]


async def test_unknown_input_id_is_rejected(d1) -> None:
    inquiry_id, _ = d1
    async with AsyncSessionLocal() as session:
        assert (await set_status(session, inquiry_id, "not-a-uuid", "illegible"))["ok"] is False
        assert (await set_status(session, inquiry_id, str(uuid.uuid4()), "illegible"))[
            "ok"
        ] is False


async def test_input_used_as_source_is_rejected(d1) -> None:
    """すでに品目行の読み取り元になっている入力は「明細なし」にできない。"""
    inquiry_id, inputs = d1
    excel = inputs["excel"]
    async with AsyncSessionLocal() as session:
        await replace_rows(session, inquiry_id, [_good_row(excel.id)])
        await session.commit()
        result = await set_status(session, inquiry_id, str(excel.id), "no_items")
        assert result["ok"] is False
        saved = await session.get(InquiryInput, excel.id)
        assert saved.status == "read"
