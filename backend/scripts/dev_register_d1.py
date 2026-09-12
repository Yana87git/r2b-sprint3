"""開発用: D1 を案件として登録する。

  uv run python scripts/dev_register_d1.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import InquiryInput  # noqa: E402
from app.services.dev_fixtures import register_d1  # noqa: E402


async def main() -> None:
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
        print(f"案件ID: {inquiry.id}")
        print(f"件名  : {inquiry.title}")
        for i in inputs:
            print(f"  - {i.display_name} / {i.format} / {i.byte_size} bytes / {i.status}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
