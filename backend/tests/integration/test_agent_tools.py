"""ツール（list_input_files / read_file_content）を、DB を通して確かめる。"""
import json
import uuid

import pytest
from sqlalchemy import delete

from app.agent.context import set_current_inquiry_id
from app.agent.tools import list_input_files, read_file_content
from app.core.database import AsyncSessionLocal
from app.models import Inquiry
from app.services.dev_fixtures import register_d1


@pytest.fixture
async def d1_inquiry_id() -> uuid.UUID:
    """D1（Excel ＋ PDF）を案件として登録し、終わったら消す。"""
    async with AsyncSessionLocal() as session:
        inquiry = await register_d1(session)
        await session.commit()
        inquiry_id = inquiry.id
    yield inquiry_id
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
        await session.commit()


def _payload(result: dict) -> dict:
    return json.loads(result["content"][0]["text"])


async def test_list_input_files_returns_two_inputs(d1_inquiry_id: uuid.UUID) -> None:
    set_current_inquiry_id(d1_inquiry_id)
    payload = _payload(await list_input_files.handler({}))
    formats = sorted(i["format"] for i in payload["inputs"])
    assert formats == ["excel", "pdf"]
    assert all(i["size_bytes"] > 0 for i in payload["inputs"])


async def test_read_file_content_returns_locators(d1_inquiry_id: uuid.UUID) -> None:
    set_current_inquiry_id(d1_inquiry_id)
    inputs = _payload(await list_input_files.handler({}))["inputs"]
    excel = next(i for i in inputs if i["format"] == "excel")

    payload = _payload(
        await read_file_content.handler({"input_id": excel["input_id"], "start": 9, "limit": 3})
    )
    assert payload["has_readable_text"] is True
    assert any(c["locator"].startswith("明細!") for c in payload["cells"])
    assert payload["has_more"] is True and payload["next"]["start"] == 12


async def test_other_inquiry_input_is_not_readable(d1_inquiry_id: uuid.UUID) -> None:
    """他の案件の入力は読めない（agent.md ガードレール）。"""
    set_current_inquiry_id(uuid.uuid4())  # 別の案件のふり
    inputs_payload = _payload(await list_input_files.handler({}))
    assert inputs_payload["inputs"] == []

    set_current_inquiry_id(d1_inquiry_id)
    real_id = _payload(await list_input_files.handler({}))["inputs"][0]["input_id"]
    set_current_inquiry_id(uuid.uuid4())
    result = _payload(await read_file_content.handler({"input_id": real_id}))
    assert "error" in result
