"""Slice 0-3 の確認: ④ の8テーブルが存在し、固定ユーザーが1件いる（DB 起動が前提）。"""
import pytest
from sqlalchemy import text

from app.core.database import AsyncSessionLocal
from app.models import Base

EXPECTED_TABLES = {
    "users",
    "inquiries",
    "inquiry_inputs",
    "item_rows",
    "item_values",
    "value_clues",
    "agent_runs",
    "item_list_exports",
}


def test_metadata_has_eight_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.asyncio
async def test_tables_exist_in_database() -> None:
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text("select table_name from information_schema.tables where table_schema='public'")
        )
        names = {r[0] for r in rows}
    assert EXPECTED_TABLES <= names


@pytest.mark.asyncio
async def test_fixed_user_exists() -> None:
    async with AsyncSessionLocal() as session:
        count = (await session.execute(text("select count(*) from users"))).scalar_one()
    assert count == 1
