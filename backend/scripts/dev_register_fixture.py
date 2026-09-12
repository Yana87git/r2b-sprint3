"""開発用: fixtures（D1 / D4 / D5）を案件として登録する。

  uv run python scripts/dev_register_fixture.py d5
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import InquiryInput  # noqa: E402
from app.services import dev_fixtures  # noqa: E402

REGISTERS = {
    "d1": dev_fixtures.register_d1,
    "d4": dev_fixtures.register_d4,
    "d5": dev_fixtures.register_d5,
}


async def main(name: str) -> None:
    async with AsyncSessionLocal() as session:
        inquiry = await REGISTERS[name](session)
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
    fixture = sys.argv[1].lower() if len(sys.argv) > 1 else "d1"
    if fixture not in REGISTERS:
        raise SystemExit(f"使える fixture: {', '.join(REGISTERS)}")
    asyncio.run(main(fixture))
