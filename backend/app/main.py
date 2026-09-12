"""FastAPI アプリケーションの入口。"""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.dependencies import get_db
from app.models import Base, User
from app.services import agent_run_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """起動時に、前のプロセスが残した「実行中」を閉じる（再起動で続きは走らないため）。"""
    closed = await agent_run_service.close_orphaned_runs()
    if closed:
        logger.warning("前のプロセスの実行 %d 件を failed として閉じました", closed)
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)


@app.get("/api/v1/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """ヘルスチェック。"""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/")
async def root() -> dict[str, str]:
    """ルート。"""
    return {"message": "FastAPI Backend Ready"}


@app.get("/api/v1/db-schema-test", tags=["Health"])
async def db_schema_test(session: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """スキーマの疎通確認（Slice 0-3）。④ の8テーブルと固定ユーザーを確認する。"""
    user_count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    return {
        "status": "Schema OK",
        "tables": sorted(Base.metadata.tables),
        "users_count": user_count,
    }
