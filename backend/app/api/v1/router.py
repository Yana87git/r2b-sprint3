"""/api/v1 のルーター。"""
from fastapi import APIRouter

from app.api.v1.endpoints import inquiries, runs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(inquiries.router)
api_router.include_router(runs.router)
