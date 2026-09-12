"""users のデータアクセス。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.base import BaseRepository

# 認証は今回未実装（① 6章）。この1件を常に使う
FIXED_LOGIN_ID = "nakamura"


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_login_id(self, login_id: str) -> User | None:
        stmt = select(User).where(User.login_id == login_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_fixed_user(self) -> User | None:
        """固定の営業事務ユーザー。submitted_by / confirmed_by はこの ID を使う。"""
        return await self.get_by_login_id(FIXED_LOGIN_ID)
