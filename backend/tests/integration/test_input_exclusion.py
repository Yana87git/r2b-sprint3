"""⑤ #15 入力の除外。除外は「読み取り不可の入力に対する判断」で、確定の判定に効く。"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput
from app.services import confirm_service, input_exclusion_service
from app.services.dev_fixtures import register_d1
from app.services.item_draft_service import replace_rows
from tests.integration.test_check_completion import _good_row


@pytest.fixture
async def with_unreadable():
    """Excel は読めて、PDF は判読不能だった案件（全行確認済み）。"""
    async with AsyncSessionLocal() as session:
        inquiry = await register_d1(session)
        await session.commit()
        inputs = {
            i.format: i
            for i in (
                await session.execute(
                    select(InquiryInput).where(InquiryInput.inquiry_id == inquiry.id)
                )
            ).scalars()
        }
        await replace_rows(session, inquiry.id, [_good_row(inputs["excel"].id)])
        inputs["pdf"].status = "unreadable"
        inputs["pdf"].unreadable_reason = "illegible"
        inquiry.status = "awaiting_review"
        await session.commit()
        rows = (
            await session.execute(select(InquiryInput).where(InquiryInput.inquiry_id == inquiry.id))
        ).scalars()
        ids = {i.format: i.id for i in rows}
        # 行は確認済みにしておく（確定を止めるのが「読み取り不可」だけになるように）
        from app.services.item_list_service import check_row
        from app.models import ItemRow

        row = (
            await session.execute(select(ItemRow).where(ItemRow.inquiry_id == inquiry.id))
        ).scalar_one()
        await check_row(session, inquiry.id, row.id)
        await session.commit()
        yield inquiry.id, ids
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


async def test_readable_input_cannot_be_excluded(with_unreadable) -> None:
    inquiry_id, ids = with_unreadable
    async with AsyncSessionLocal() as session:
        with pytest.raises(input_exclusion_service.ExclusionError) as excinfo:
            await input_exclusion_service.exclude(session, inquiry_id, ids["excel"])
    assert excinfo.value.code == "INPUT_NOT_EXCLUDABLE"


async def test_exclusion_unblocks_confirm(with_unreadable) -> None:
    inquiry_id, ids = with_unreadable
    # 除外する前は確定できない
    async with AsyncSessionLocal() as session:
        with pytest.raises(confirm_service.ConfirmError) as excinfo:
            await confirm_service.confirm(session, inquiry_id)
    assert excinfo.value.code == "UNREADABLE_INPUT_REMAINS"

    async with AsyncSessionLocal() as session:
        payload = await input_exclusion_service.exclude(session, inquiry_id, ids["pdf"])
        await session.commit()
    assert payload["excluded"] is True

    # 除外した入力は「読み取れなかった入力」に数えない
    async with AsyncSessionLocal() as session:
        result = await confirm_service.confirm(session, inquiry_id)
        await session.commit()
    assert result["row_count"] == 1


async def test_cancel_brings_it_back(with_unreadable) -> None:
    inquiry_id, ids = with_unreadable
    async with AsyncSessionLocal() as session:
        await input_exclusion_service.exclude(session, inquiry_id, ids["pdf"])
        await session.commit()
    async with AsyncSessionLocal() as session:
        payload = await input_exclusion_service.cancel(session, inquiry_id, ids["pdf"])
        await session.commit()
    assert payload["excluded"] is False

    async with AsyncSessionLocal() as session:
        with pytest.raises(confirm_service.ConfirmError) as excinfo:
            await confirm_service.confirm(session, inquiry_id)
    assert excinfo.value.code == "UNREADABLE_INPUT_REMAINS"


async def test_confirmed_inquiry_is_rejected(with_unreadable) -> None:
    inquiry_id, ids = with_unreadable
    async with AsyncSessionLocal() as session:
        await input_exclusion_service.exclude(session, inquiry_id, ids["pdf"])
        await session.commit()
        await confirm_service.confirm(session, inquiry_id)
        await session.commit()
    async with AsyncSessionLocal() as session:
        with pytest.raises(input_exclusion_service.ExclusionError) as excinfo:
            await input_exclusion_service.cancel(session, inquiry_id, ids["pdf"])
    assert excinfo.value.code == "ALREADY_CONFIRMED"


async def test_input_of_another_inquiry_is_not_found(with_unreadable) -> None:
    inquiry_id, _ = with_unreadable
    async with AsyncSessionLocal() as session:
        assert await input_exclusion_service.exclude(session, inquiry_id, uuid.uuid4()) is None
