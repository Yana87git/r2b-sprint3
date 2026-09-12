"""案件と入力に関する業務ロジック。ツールは必ずこの層を経由して DB に触る。"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InquiryInput


async def list_inputs(session: AsyncSession, inquiry_id: uuid.UUID) -> list[InquiryInput]:
    """案件に投入された入力（ファイルとメール本文）を登録順に返す。"""
    stmt = (
        select(InquiryInput)
        .where(InquiryInput.inquiry_id == inquiry_id)
        .order_by(InquiryInput.created_at, InquiryInput.display_name)
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_input(
    session: AsyncSession, inquiry_id: uuid.UUID, input_id: uuid.UUID
) -> InquiryInput | None:
    """入力を1件返す。**他の案件の入力は返さない**（ガードレール）。"""
    stmt = select(InquiryInput).where(
        InquiryInput.id == input_id, InquiryInput.inquiry_id == inquiry_id
    )
    return (await session.execute(stmt)).scalar_one_or_none()
