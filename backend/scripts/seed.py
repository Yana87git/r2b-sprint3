"""初期データ投入。認証を作らないため、固定の営業事務ユーザーを1件だけ入れる（① 6章）。

  uv run python scripts/seed.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import User  # noqa: E402
from app.repositories import FIXED_LOGIN_ID  # noqa: E402

# 認証は未実装なので、パスワードは使わない。列が NOT NULL なので印だけ入れる
PLACEHOLDER_HASH = "not-used-auth-is-out-of-scope"


async def main() -> None:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        existing = (
            await session.execute(select(User).where(User.login_id == FIXED_LOGIN_ID))
        ).scalar_one_or_none()
        if existing:
            print(f"固定ユーザーは作成済み: {existing.login_id} / {existing.id}")
        else:
            user = User(
                login_id=FIXED_LOGIN_ID,
                password_hash=PLACEHOLDER_HASH,
                display_name="中村（営業事務）",
                role="sales_clerk",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"固定ユーザーを作成: {user.login_id} / {user.id}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
