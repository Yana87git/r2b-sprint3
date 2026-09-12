"""開発・テスト用: fixtures の引合書を案件として登録する。

投入API（⑤ #4）はまだ無いので、ツールが読むデータをここで用意する。
原本はコピーせず、`storage_path` が fixtures の実ファイルを指す。
"""
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Inquiry, InquiryInput, User
from app.repositories import FIXED_LOGIN_ID

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
RETENTION_DAYS = 90

# 拡張子 → ② FUNC-01 の形式
FORMAT_BY_SUFFIX = {".xlsx": "excel", ".pdf": "pdf", ".docx": "word"}


async def _fixed_user(session: AsyncSession) -> User:
    user = (
        await session.execute(select(User).where(User.login_id == FIXED_LOGIN_ID))
    ).scalar_one_or_none()
    if user is None:
        raise RuntimeError("固定ユーザーがいない。先に uv run python scripts/seed.py を実行する")
    return user


async def register_inquiry_from_files(
    session: AsyncSession,
    *,
    title: str,
    files: list[Path],
    mail_body: str | None = None,
) -> Inquiry:
    """ファイル（と任意のメール本文）を1件の案件として登録する。"""
    user = await _fixed_user(session)
    inquiry = Inquiry(
        title=title,
        status="received",
        submitted_by=user.id,
        retention_until=date.today() + timedelta(days=RETENTION_DAYS),
    )
    session.add(inquiry)
    await session.flush()

    for path in files:
        suffix = path.suffix.lower()
        if suffix not in FORMAT_BY_SUFFIX:
            raise ValueError(f"対応しない拡張子: {path.name}（対応: .xlsx .pdf .docx）")
        session.add(
            InquiryInput(
                inquiry_id=inquiry.id,
                kind="file",
                display_name=path.name,
                format=FORMAT_BY_SUFFIX[suffix],
                byte_size=path.stat().st_size,
                storage_path=str(path.resolve()),
            )
        )

    if mail_body is not None:
        session.add(
            InquiryInput(
                inquiry_id=inquiry.id,
                kind="mail_body",
                display_name="メール本文",
                format="mail_body",
                content_text=mail_body,
            )
        )

    await session.flush()
    return inquiry


async def register_d1(session: AsyncSession) -> Inquiry:
    """D1（Excel の明細 ＋ PDF の仕様書）を1件の案件として登録する。"""
    d1 = FIXTURES_DIR / "d1"
    return await register_inquiry_from_files(
        session,
        title="見積依頼.xlsx ほか1件（D1）",
        files=[d1 / "normal_excel.xlsx", d1 / "normal_spec.pdf"],
    )
