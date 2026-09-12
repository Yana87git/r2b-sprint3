"""⑤ #14 読み取り元の取得。**この GET は抜き取りを記録する**（同じ行は1回だけ）。"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput, ItemRow, ItemValue
from app.services.dev_fixtures import register_d1
from app.services.item_draft_service import replace_rows
from app.services.source_excerpt_service import get_source
from tests.integration.test_check_completion import _good_row


@pytest.fixture
async def reviewable():
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
        await replace_rows(session, inquiry.id, [_good_row(excel.id)])
        await session.commit()
        yield inquiry.id
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


async def _value_id(inquiry_id: uuid.UUID, field: str) -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        rows = (
            (await session.execute(select(ItemRow).where(ItemRow.inquiry_id == inquiry_id)))
            .scalars()
            .all()
        )
        value = (
            await session.execute(
                select(ItemValue).where(
                    ItemValue.item_row_id.in_([r.id for r in rows]), ItemValue.field == field
                )
            )
        ).scalar_one()
        return value.id


async def test_returns_locator_and_excerpt(reviewable) -> None:
    value_id = await _value_id(reviewable, "model_no")
    async with AsyncSessionLocal() as session:
        payload = await get_source(session, reviewable, value_id)
        await session.commit()

    assert payload["source"]["locator_label"] == "明細!C10"
    assert payload["source"]["input_name"] == "normal_excel.xlsx"
    excerpt = payload["excerpt"]
    assert excerpt["kind"] == "grid"
    # 位置のセルに印が付き、前後の行も入っている
    hits = [
        (row["no"], cell["col"], cell["text"])
        for row in excerpt["rows"]
        for cell in row["cells"]
        if cell["hit"]
    ]
    assert hits == [(10, "C", "BRG-6205-2RS")]
    # 前後2行ぶんの窓（原本に無い空行はそもそも返らない）
    numbers = [row["no"] for row in excerpt["rows"]]
    assert 10 in numbers and min(numbers) >= 8 and max(numbers) <= 12
    assert len(numbers) >= 3


async def test_records_sampling_once(reviewable) -> None:
    value_id = await _value_id(reviewable, "item_name")
    async with AsyncSessionLocal() as session:
        first = await get_source(session, reviewable, value_id)
        await session.commit()
    assert first["sampling"] == {
        "sampled_rows": 1,
        "required_samples": 1,
        "confident_rows": 1,
        "opened_now": True,
    }

    async with AsyncSessionLocal() as session:
        again = await get_source(session, reviewable, value_id)
        await session.commit()
    # 2回目は記録しない（時刻も動かさない）
    assert again["sampling"]["opened_now"] is False
    assert again["sampling"]["sampled_rows"] == 1


async def test_value_of_another_inquiry_is_rejected(reviewable) -> None:
    value_id = await _value_id(reviewable, "item_name")
    async with AsyncSessionLocal() as session:
        assert await get_source(session, uuid.uuid4(), value_id) is None
        assert await get_source(session, reviewable, uuid.uuid4()) is None
