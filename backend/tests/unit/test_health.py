"""ヘルスチェックの単体テスト（Slice 0-1 の疎通確認）。"""
from fastapi.testclient import TestClient


def test_health_returns_healthy(client: TestClient) -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_root_returns_message(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert "message" in res.json()
