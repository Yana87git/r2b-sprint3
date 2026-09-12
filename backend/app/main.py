"""FastAPI アプリケーションの入口。"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.v1.router import api_router
from app.core.dependencies import get_db
from app.models import Base, User

app = FastAPI(
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
