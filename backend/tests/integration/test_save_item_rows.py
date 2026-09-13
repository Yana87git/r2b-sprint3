"""save_item_rows の6つの検査と、丸ごと置き換え（§3-3）。"""
import uuid

import pytest
from sqlalchemy import delete, func, select

from app.core.database import AsyncSessionLocal
from app.models import Inquiry, InquiryInput, ItemRow, ItemValue, ValueClue
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
        excel = next(i for i in inputs if i.format == "excel")
        yield inquiry.id, excel.id
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
        await session.commit()


def _value(text: str, input_id: uuid.UUID, locator: str, **over):
    payload = {
        "raw_text": text,
        "value": text,
        "state": "extracted",
        "confidence": "high",
        "clues": [],
        "source": {"input_id": str(input_id), "locator": locator},
    }
    payload.update(over)
    return payload


def _row(input_id: uuid.UUID, row_no: int = 1, **over):
    values = {
        "item_name": _value("深溝玉軸受", input_id, "明細!B10"),
        "part_no": _value("BRG-6205-2RS", input_id, "明細!C10"),
        "quantity": _value("40", input_id, "明細!D10"),
        "unit": _value("個", input_id, "明細!E10"),
        "due_date": {
            "raw_text": "2026-10-20",
            "kind": "fixed",
            "start_date": "2026-10-20",
            "state": "extracted",
            "confidence": "high",
            "clues": [],
            "source": {"input_id": str(input_id), "locator": "明細!F10"},
        },
    }
    values.update(over)
    return {"row_no": row_no, "source_input_id": str(input_id), "values": values}


async def test_saves_rows_and_marks_input_read(d1) -> None:
    inquiry_id, input_id = d1
    async with AsyncSessionLocal() as session:
        result = await replace_rows(session, inquiry_id, [_row(input_id), _row(input_id, 2)])
        await session.commit()
        assert result == {"saved_rows": 2, "errors": []}
        rows = (
            await session.execute(
                select(func.count()).select_from(ItemRow).where(ItemRow.inquiry_id == inquiry_id)
            )
        ).scalar_one()
        assert rows == 2
        input_ = await session.get(InquiryInput, input_id)
        # 「読み取り済み」は保存した行の読み取り元から自動で決まる
        assert input_.status == "read" and input_.row_count > 0


async def test_replaces_previous_draft(d1) -> None:
    """丸ごと置き換え。直した内容で上書きされる。"""
    inquiry_id, input_id = d1
    async with AsyncSessionLocal() as session:
        await replace_rows(session, inquiry_id, [_row(input_id), _row(input_id, 2)])
        await session.commit()
    async with AsyncSessionLocal() as session:
        result = await replace_rows(session, inquiry_id, [_row(input_id)])
        await session.commit()
        assert result["saved_rows"] == 1
        remaining = (
            await session.execute(
                select(func.count()).select_from(ItemRow).where(ItemRow.inquiry_id == inquiry_id)
            )
        ).scalar_one()
        assert remaining == 1


async def test_errors_are_returned_but_rows_are_still_saved(d1) -> None:
    """誤りが出ても保存する（check_completion が③〜⑥を返せるように）。"""
    inquiry_id, input_id = d1
    bad_quantity = _value("2OO", input_id, "明細!D10")
    async with AsyncSessionLocal() as session:
        result = await replace_rows(session, inquiry_id, [_row(input_id, quantity=bad_quantity)])
        await session.commit()
        assert result["saved_rows"] == 1
        assert any(e["field"] == "quantity" and "2OO" in e["message"] for e in result["errors"])
        # 値そのものは保存されている（数値だけ入らない）
        stored = (
            await session.execute(
                select(ItemValue)
                .join(ItemRow, ItemValue.item_row_id == ItemRow.id)
                .where(ItemRow.inquiry_id == inquiry_id, ItemValue.field == "quantity")
            )
        ).scalar_one()
        assert stored.value_text == "2OO" and stored.quantity_value is None


async def test_six_checks(d1) -> None:
    inquiry_id, input_id = d1
    other_input = uuid.uuid4()
    rows = [
        # 1. 必須5項目の空欄
        _row(input_id, 1, unit={}),
        # 2. 数値でない数量 → 上のテストで確認済み。ここでは月をまたぐ納期
        _row(
            input_id,
            2,
            due_date={
                "raw_text": "10月末",
                "kind": "month_range",
                "start_date": "2026-10-21",
                "end_date": "2026-11-05",
                "state": "extracted",
                "confidence": "high",
                "clues": [],
                "source": {"input_id": str(input_id), "locator": "明細!F11"},
            },
        ),
        # 3. 読み取り元のない値
        _row(
            input_id,
            3,
            part_no={"raw_text": "X", "value": "X", "state": "extracted", "confidence": "high"},
        ),
        # 4. 案件にないファイルを指す読み取り元
        _row(input_id, 4, item_name=_value("A", other_input, "明細!B12")),
        # 5. 確信が低いのに手がかりが無い
        _row(input_id, 5, unit=_value("個", input_id, "明細!E13", confidence="low")),
    ]
    async with AsyncSessionLocal() as session:
        result = await replace_rows(session, inquiry_id, rows)
        await session.commit()

    messages = {(e["row_no"], e["field"]): e["message"] for e in result["errors"]}
    assert "必須項目" in messages[(1, "unit")]
    assert "同じ月" in messages[(2, "due_date")]
    assert "読み取り元" in messages[(3, "part_no")]
    assert "この案件に無い入力" in messages[(4, "item_name")]
    assert "手がかり" in messages[(5, "unit")]


async def test_classification_and_clues(d1) -> None:
    inquiry_id, input_id = d1
    low = _value("BRG-62O5-2RS", input_id, "明細!C10", confidence="low", clues=["H2"])
    needs = {"state": "needs_confirmation", "confidence": "high", "clues": []}
    async with AsyncSessionLocal() as session:
        await replace_rows(
            session,
            inquiry_id,
            [
                _row(input_id, 1, part_no=low),
                _row(input_id, 2, unit=needs),
            ],
        )
        await session.commit()
        rows = (
            (
                await session.execute(
                    select(ItemRow).where(ItemRow.inquiry_id == inquiry_id).order_by(ItemRow.row_no)
                )
            )
            .scalars()
            .all()
        )
        assert [r.classification for r in rows] == ["low_confidence", "needs_confirmation"]
        clues = (
            (
                await session.execute(
                    select(ValueClue)
                    .join(ItemValue, ValueClue.item_value_id == ItemValue.id)
                    .join(ItemRow, ItemValue.item_row_id == ItemRow.id)
                    .where(ItemRow.inquiry_id == inquiry_id)
                )
            )
            .scalars()
            .all()
        )
        assert [c.clue for c in clues] == ["H2"]


async def test_accepts_flat_row_shape(d1) -> None:
    """values の下でなく、行の直下に値が並ぶ形も受ける（モデルがこの形で送ることがある）。"""
    inquiry_id, input_id = d1
    row = _row(input_id)
    flat = {"row_no": row["row_no"], "source_input_id": row["source_input_id"], **row["values"]}
    async with AsyncSessionLocal() as session:
        result = await replace_rows(session, inquiry_id, [flat])
        await session.commit()
    assert result == {"saved_rows": 1, "errors": []}


async def test_row_count_counts_rows_not_values(d1) -> None:
    """入力の「N 行を読み取りました」は**行の数**（値の数ではない）。"""
    inquiry_id, excel_id = d1
    async with AsyncSessionLocal() as session:
        await replace_rows(session, inquiry_id, [_row(excel_id, n) for n in range(1, 4)])
        await session.commit()
        saved = await session.get(InquiryInput, excel_id)
    # 3行 × 5項目 = 15値だが、数えるのは3行
    assert saved.row_count == 3
