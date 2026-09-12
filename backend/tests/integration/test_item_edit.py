"""⑤ #10 行の修正。人が直した値は確信が高くなり、手がかりが消え、行は確認済みになる。"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput, ItemRow, ItemValue, ValueClue
from app.services.dev_fixtures import register_d1
from app.services.item_draft_service import replace_rows
from app.services.item_edit_service import EditError, update_row
from tests.integration.test_check_completion import _good_row, _v


@pytest.fixture
async def row():
    """型番の確信が低い（H2）行を1つ持つ案件。"""
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
        draft = _good_row(excel.id)
        draft["values"]["part_no"] = _v(
            "BRG-62O5-2RS", excel.id, "明細!C10", confidence="low", clues=["H2"]
        )
        await replace_rows(session, inquiry.id, [draft])
        await session.commit()
        item = (
            await session.execute(select(ItemRow).where(ItemRow.inquiry_id == inquiry.id))
        ).scalar_one()
        yield inquiry.id, item.id
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


async def _values(row_id: uuid.UUID) -> dict[str, ItemValue]:
    async with AsyncSessionLocal() as session:
        return {
            v.field: v
            for v in (
                await session.execute(select(ItemValue).where(ItemValue.item_row_id == row_id))
            ).scalars()
        }


async def test_edit_raises_confidence_and_clears_clues(row) -> None:
    inquiry_id, row_id = row
    before = await _values(row_id)
    assert (before["model_no"].confidence, before["model_no"].value_text) == (
        "low",
        "BRG-62O5-2RS",
    )

    async with AsyncSessionLocal() as session:
        result = await update_row(
            session, inquiry_id, row_id, {"model_no": {"value": "BRG-6205-2RS"}}
        )
        await session.commit()
    assert result["classification"] == "high_confidence"
    assert result["check_state"] == "checked"

    after = await _values(row_id)
    value = after["model_no"]
    assert (value.value_text, value.confidence) == ("BRG-6205-2RS", "high")
    assert value.edited_at is not None
    # 原文は残す（何と書いてあったかが分からなくなるため）
    assert value.raw_text == "BRG-62O5-2RS"
    assert value.source_input_id is not None
    async with AsyncSessionLocal() as session:
        clues = (
            (await session.execute(select(ValueClue).where(ValueClue.item_value_id == value.id)))
            .scalars()
            .all()
        )
    assert clues == []


async def test_needs_confirmation_makes_the_row_needs_confirmation(row) -> None:
    inquiry_id, row_id = row
    async with AsyncSessionLocal() as session:
        result = await update_row(
            session, inquiry_id, row_id, {"quantity": {"state": "needs_confirmation"}}
        )
        await session.commit()
    assert result["classification"] == "needs_confirmation"
    after = await _values(row_id)
    assert (after["quantity"].state, after["quantity"].value_text) == ("needs_confirmation", None)


async def test_month_range_is_saved(row) -> None:
    inquiry_id, row_id = row
    async with AsyncSessionLocal() as session:
        await update_row(
            session,
            inquiry_id,
            row_id,
            {
                "due_date": {
                    "kind": "month_range",
                    "start_date": "2026-10-21",
                    "end_date": "2026-10-31",
                }
            },
        )
        await session.commit()
    value = (await _values(row_id))["due_date"]
    assert (value.due_kind, value.value_text) == ("month_range", "2026-10-21〜2026-10-31")


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"quantity": {"value": "たくさん"}}, "QUANTITY_NOT_NUMERIC"),
        ({"item_name": {"value": "   "}}, "REQUIRED_FIELD_EMPTY"),
        ({"due_date": {"kind": "そのうち", "start_date": "2026-10-21"}}, "DUE_DATE_OUT_OF_DOMAIN"),
        (
            {
                "due_date": {
                    "kind": "month_range",
                    "start_date": "2026-10-21",
                    "end_date": "2026-11-05",
                }
            },
            "DUE_RANGE_INVALID",
        ),
        (
            {
                "due_date": {
                    "kind": "month_range",
                    "start_date": "2026-10-31",
                    "end_date": "2026-10-21",
                }
            },
            "DUE_RANGE_INVALID",
        ),
    ],
)
async def test_validation(row, payload, code) -> None:
    inquiry_id, row_id = row
    async with AsyncSessionLocal() as session:
        with pytest.raises(EditError) as excinfo:
            await update_row(session, inquiry_id, row_id, payload)
    assert excinfo.value.code == code

    # 弾かれた行は確認済みにならない
    async with AsyncSessionLocal() as session:
        item = await session.get(ItemRow, row_id)
        assert item.check_state == "unchecked"


async def test_note_can_be_emptied(row) -> None:
    inquiry_id, row_id = row
    async with AsyncSessionLocal() as session:
        await update_row(session, inquiry_id, row_id, {"note": {"value": ""}})
        await session.commit()
    assert (await _values(row_id))["note"].value_text is None


async def test_row_of_another_inquiry_is_not_found(row) -> None:
    inquiry_id, row_id = row
    async with AsyncSessionLocal() as session:
        assert await update_row(session, uuid.uuid4(), row_id, {}) is None
