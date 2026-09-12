"""Slice 0-7: 実行設定と2層タイムアウトの不変条件（agent.md 実行設定）。"""
import subprocess
import sys

from app.agent import definition as d


def test_defaults_match_design() -> None:
    assert d.MODEL == "claude-sonnet-5"
    assert d.MAX_TURNS == 30
    assert (d.INACTIVITY_TIMEOUT_S, d.INNER_TIMEOUT_S, d.OUTER_TIMEOUT_S) == (60, 300, 360)


def test_ordering_invariant_holds() -> None:
    assert d.INACTIVITY_TIMEOUT_S < d.INNER_TIMEOUT_S < d.OUTER_TIMEOUT_S


def _import_with(env: dict[str, str]) -> subprocess.CompletedProcess:
    code = (
        "from app.agent import definition as d;"
        "print(d.INACTIVITY_TIMEOUT_S, d.INNER_TIMEOUT_S, d.OUTER_TIMEOUT_S)"
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**env})


def test_lowering_inner_keeps_ordering(monkeypatch) -> None:
    """⑥ TEST-18 は INNER だけを下げる。明示しない側は大小関係を保つように寄る。"""
    import os

    res = _import_with({**os.environ, "INNER_TIMEOUT_S": "10"})
    assert res.returncode == 0, res.stderr
    inactivity, inner, outer = (int(x) for x in res.stdout.split())
    assert inactivity < inner < outer and inner == 10


def test_contradictory_override_is_rejected() -> None:
    """無応答 > 内側 のような矛盾した指定は、起動時に落として気づかせる。"""
    import os

    res = _import_with({**os.environ, "INACTIVITY_TIMEOUT_S": "400"})
    assert res.returncode != 0
    assert "無応答 < 内側 < 外側" in res.stderr
