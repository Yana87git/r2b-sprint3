"""エージェント定義。docs/requirements/agent.md「実行設定」の写し。

このファイルの値は設計書の写しであり、変更するときは agent.md 側も更新する。
3つのタイムアウトと最大ターン数は、評価（⑥ TEST-17・18）のときだけ環境変数で下げられる。
**本番の既定値は下のとおり。下げたまま戻し忘れないこと。**
"""
import os

__all__ = [
    "MODEL",
    "MAX_TURNS",
    "INACTIVITY_TIMEOUT_S",
    "INNER_TIMEOUT_S",
    "OUTER_TIMEOUT_S",
]


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


# --- モデル（agent.md 実行設定。上げるときは agent.md を先に変える）---
MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-5")

# --- 強制停止（agent.md の「完了条件・停止条件」の強制停止行に対応）---
MAX_TURNS = _env_int("MAX_TURNS", 30)

# --- タイムアウトの2層構造（必ず 無応答 < 内側 < 外側 を守る）---
# 内側 = エージェント自身の停止条件。発火したらトレースに記録して整然と終了する
# 外側 = ジョブ層（jobs.py）のフェイルセーフ。内側がハング等で発火できないときの最後の砦
#
# 評価（⑥ TEST-18）は INNER_TIMEOUT_S だけを下げる。そのとき明示していない側は
# 大小関係を保つように自動で寄せる（明示した値はそのまま使う）。
_DEFAULT_INACTIVITY, _DEFAULT_INNER, _DEFAULT_OUTER = 60, 300, 360

INNER_TIMEOUT_S = _env_int("INNER_TIMEOUT_S", _DEFAULT_INNER)
INACTIVITY_TIMEOUT_S = _env_int(
    "INACTIVITY_TIMEOUT_S", min(_DEFAULT_INACTIVITY, max(1, INNER_TIMEOUT_S - 1))
)
OUTER_TIMEOUT_S = _env_int("OUTER_TIMEOUT_S", max(_DEFAULT_OUTER, INNER_TIMEOUT_S + 1))

assert INACTIVITY_TIMEOUT_S < INNER_TIMEOUT_S < OUTER_TIMEOUT_S, (
    "タイムアウトは 無応答 < 内側 < 外側 の順でなければならない。"
    "外側が先に発火すると、トレースに停止理由を記録できないまま実行が破棄される。"
    f"（現在: {INACTIVITY_TIMEOUT_S} / {INNER_TIMEOUT_S} / {OUTER_TIMEOUT_S}）"
)

# 停止理由（トレースの run_end と 04 の agent_runs.stop_reason に対応）
STOP_REASONS = (
    "completed",
    "failed",
    "max_turns",
    "inner_timeout",
    "inactivity_timeout",
    "outer_timeout",
)
