"""agent_runs のデータアクセス。"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun
from app.repositories.base import BaseRepository


class AgentRunRepository(BaseRepository[AgentRun]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentRun)

    async def get_by_run_id(self, run_id: uuid.UUID) -> AgentRun | None:
        return await self.session.get(AgentRun, run_id)

    async def count_for_inquiry(self, inquiry_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(AgentRun).where(AgentRun.inquiry_id == inquiry_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def latest_for_inquiry(self, inquiry_id: uuid.UUID) -> AgentRun | None:
        stmt = (
            select(AgentRun)
            .where(AgentRun.inquiry_id == inquiry_id)
            .order_by(AgentRun.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
