"""pytest 共通設定。DB を使うフィクスチャは Slice 0-3 で追加する。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI のテストクライアント。"""
    return TestClient(app)
