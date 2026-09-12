"""⑤ #12 一括確認。抜き取りが min(3, N) に足りなければサーバー側で拒否する。"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput, ItemRow, ItemValue
from app.services.dev_fixtures import register_d1
from app.services.item_list_service import SamplingNotEnoughError, bulk_check
from app.services.item_draft_service import replace_rows
from app.services.source_excerpt_service import get_source
from tests.integration.test_check_completion import _good_row


@pytest.fixture
async def five_rows():
    """確信が高い行を5行持つ案件（N=5 なので必要な抜き取りは3行）。"""
    async with AsyncSessionLocal() as session:
        inquiry = await register_d1(session)
        await session.commit()
        excel = (
            await session.execute(
                select(InquiryInput).where(
                    InquiryInput.inquiry_id == inquiry.id, InquiryInput.format == "excel"
                )
            )
        ).scalar_one()
        await replace_rows(session, inquiry.id, [_good_row(excel.id, n) for n in range(1, 6)])
        await session.commit()
        yield inquiry.id
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


async def _open_sources(inquiry_id: uuid.UUID, count: int) -> None:
    """読み取り元を count 行ぶん開く（#14 と同じ経路で抜き取りを記録する）。"""
    async with AsyncSessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(ItemRow).where(ItemRow.inquiry_id == inquiry_id).order_by(ItemRow.row_no)
                )
            )
            .scalars()
            .all()
        )
        for row in rows[:count]:
            value = (
                await session.execute(
                    select(ItemValue).where(
                        ItemValue.item_row_id == row.id, ItemValue.field == "item_name"
                    )
                )
            ).scalar_one()
            await get_source(session, inquiry_id, value.id)
        await session.commit()


async def test_rejects_when_sampling_is_not_enough(five_rows) -> None:
    await _open_sources(five_rows, 2)
    async with AsyncSessionLocal() as session:
        with pytest.raises(SamplingNotEnoughError) as excinfo:
            await bulk_check(session, five_rows)
    assert (excinfo.value.sampled, excinfo.value.required) == (2, 3)

    async with AsyncSessionLocal() as session:
        rows = (
            (await session.execute(select(ItemRow).where(ItemRow.inquiry_id == five_rows)))
            .scalars()
            .all()
        )
    assert all(r.check_state == "unchecked" for r in rows)


async def test_checks_all_confident_rows(five_rows) -> None:
    await _open_sources(five_rows, 3)
    async with AsyncSessionLocal() as session:
        result = await bulk_check(session, five_rows)
        await session.commit()
    assert result["checked_rows"] == 5
    assert result["summary"]["unchecked_rows"] == 0


async def test_required_samples_follow_row_count(five_rows) -> None:
    """N が3行未満なら必要な抜き取りも N 行（min(3, N)）。"""
    async with AsyncSessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(ItemRow).where(ItemRow.inquiry_id == five_rows).order_by(ItemRow.row_no)
                )
            )
            .scalars()
            .all()
        )
        for row in rows[2:]:
            await session.delete(row)
        await session.commit()

    await _open_sources(five_rows, 2)
    async with AsyncSessionLocal() as session:
        result = await bulk_check(session, five_rows)
        await session.commit()
    assert result["checked_rows"] == 2
