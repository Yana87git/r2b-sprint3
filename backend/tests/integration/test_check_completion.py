"""check_completion の判定（§4）。失敗条件を先に見る／incomplete では状態を変えない。"""
import uuid

import pytest
from sqlalchemy import delete, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput
from app.services.completion_service import check
from app.services.dev_fixtures import register_d1
from app.services.item_draft_service import replace_rows


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


def _v(text: str, iid: uuid.UUID, loc: str, **over):
    payload = {
        "raw_text": text,
        "value": text,
        "state": "extracted",
        "confidence": "high",
        "clues": [],
        "source": {"input_id": str(iid), "locator": loc},
    }
    payload.update(over)
    return payload


def _good_row(iid: uuid.UUID, row_no: int = 1):
    """D1 の Excel 10行目の実データと一致する行（照合が通る）。"""
    return {
        "row_no": row_no,
        "source_input_id": str(iid),
        "values": {
            "item_name": _v("深溝玉軸受", iid, "明細!B10"),
            "part_no": _v("BRG-6205-2RS", iid, "明細!C10"),
            "quantity": _v("20", iid, "明細!D10"),
            "unit": _v("個", iid, "明細!E10"),
            "due_date": {
                "raw_text": "2026-10-15",
                "kind": "fixed",
                "start_date": "2026-10-15",
                "state": "extracted",
                "confidence": "high",
                "clues": [],
                "source": {"input_id": str(iid), "locator": "明細!F10"},
            },
        },
    }


async def test_all_inputs_unreadable_fails_first(d1) -> None:
    """失敗条件を先に見る: すべての入力が判読不能なら failed_illegible。"""
    inquiry_id, inputs = d1
    async with AsyncSessionLocal() as session:
        for i in inputs.values():
            db_input = await session.get(InquiryInput, i.id)
            db_input.status = "unreadable"
            db_input.unreadable_reason = "illegible"
        result = await check(session, inquiry_id)
        await session.commit()
        assert result["result"] == "failed_illegible"
        inquiry = await session.get(Inquiry, inquiry_id)
        assert inquiry.status == "unreadable" and inquiry.unreadable_reason == "illegible"


async def test_no_items_fails(d1) -> None:
    """読み取れた入力があるのに品目行が0件 → failed_no_items。"""
    inquiry_id, inputs = d1
    async with AsyncSessionLocal() as session:
        db_input = await session.get(InquiryInput, inputs["excel"].id)
        db_input.status = "read_no_items"
        result = await check(session, inquiry_id)
        await session.commit()
        assert result["result"] == "failed_no_items"
        inquiry = await session.get(Inquiry, inquiry_id)
        assert inquiry.unreadable_reason == "no_items"


async def test_incomplete_does_not_change_status(d1) -> None:
    """未達のときは案件の状態を変えない。"""
    inquiry_id, inputs = d1
    excel = inputs["excel"].id
    async with AsyncSessionLocal() as session:
        # 1行だけ保存（PDF の状態が未確定なので①未達）
        await replace_rows(session, inquiry_id, [_good_row(excel)])
        result = await check(session, inquiry_id)
        await session.commit()
        assert result["result"] == "incomplete"
        assert any(u["condition"] == "①" for u in result["unmet"])
        inquiry = await session.get(Inquiry, inquiry_id)
        assert inquiry.status != "awaiting_review"


async def test_completed_sets_awaiting_review(d1) -> None:
    """①〜⑥がそろえば completed。案件は確認待ちになる。"""
    inquiry_id, inputs = d1
    excel, pdf = inputs["excel"].id, inputs["pdf"].id
    async with AsyncSessionLocal() as session:
        await replace_rows(session, inquiry_id, [_good_row(excel)])
        # PDF は明細なしとして確定させる（set_file_status 相当）
        db_pdf = await session.get(InquiryInput, pdf)
        db_pdf.status = "read_no_items"
        result = await check(session, inquiry_id)
        await session.commit()
        assert result["result"] == "completed", result["unmet"]
        inquiry = await session.get(Inquiry, inquiry_id)
        assert inquiry.status == "awaiting_review"


async def test_mismatch_is_reported_as_condition_4(d1) -> None:
    """原文が位置と合わなければ④未達。"""
    inquiry_id, inputs = d1
    excel, pdf = inputs["excel"].id, inputs["pdf"].id
    row = _good_row(excel)
    row["values"]["part_no"] = _v("BRG-9999", excel, "明細!C10")  # 実際は BRG-6205-2RS
    async with AsyncSessionLocal() as session:
        await replace_rows(session, inquiry_id, [row])
        db_pdf = await session.get(InquiryInput, pdf)
        db_pdf.status = "read_no_items"
        result = await check(session, inquiry_id)
        await session.commit()
        assert result["result"] == "incomplete"
        assert any(u["condition"] == "④" and "BRG-9999" in u["message"] for u in result["unmet"])


async def test_low_confidence_without_clue_is_condition_5(d1) -> None:
    inquiry_id, inputs = d1
    excel, pdf = inputs["excel"].id, inputs["pdf"].id
    row = _good_row(excel)
    row["values"]["unit"] = _v("個", excel, "明細!E10", confidence="low", clues=[])
    async with AsyncSessionLocal() as session:
        await replace_rows(session, inquiry_id, [row])
        db_pdf = await session.get(InquiryInput, pdf)
        db_pdf.status = "read_no_items"
        result = await check(session, inquiry_id)
        await session.commit()
        assert any(u["condition"] == "⑤" for u in result["unmet"])
