"""エージェント実行の API（⑤ #8）。実行の型は「POST 202 → GET でポーリング」。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import api_error
from app.api.v1.schemas import RunStatusResponse
from app.core.dependencies import get_db
from app.services import run_status_service

router = APIRouter(prefix="/runs", tags=["Runs"])


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run(run_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> RunStatusResponse:
    payload = await run_status_service.get_status(session, run_id)
    if payload is None:
        raise api_error(404, "NOT_FOUND", "実行が見つかりません")
    return RunStatusResponse(**payload)
