"""実行トレース: backend/traces/{run_id}.jsonl に1行1イベントで記録する。

docs/build/agent-implementation-spec.md §6 の形式。
- 記録されない実行は評価できない（.claude/rules/agent-development.md）
- **原本の全文と API キーは絶対に書かない。** read_file_content の結果は要約だけ
  （ファイル名・範囲・行数）。⑥ の3章はこのトレースを5観点で検査する
"""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TRACES_DIR = Path(__file__).resolve().parents[2] / "traces"

# 要約だけを残すツール（観察に原本の中身が入るもの）
SUMMARY_ONLY_TOOLS = {"read_file_content"}
# 値を伏せるキー（保険。キーや本文がツール入出力に紛れ込んでも残さない）
REDACT_KEYS = {"api_key", "anthropic_api_key", "authorization", "password", "content_text"}
MAX_TEXT = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _redact(value: Any) -> Any:
    """秘密情報を伏せ、長すぎるテキストは切り詰める。"""
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in REDACT_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str) and len(value) > MAX_TEXT:
        return value[:MAX_TEXT] + f"…（{len(value)}文字を切り詰め）"
    return value


class TraceRecorder:
    """1実行ぶんのトレース。run_id がそのままファイル名になる。"""

    def __init__(
        self,
        *,
        run_id: str | None = None,
        inquiry_id: str | None = None,
        scenario: str | None = None,
    ) -> None:
        self.run_id = run_id or str(uuid.uuid4())
        self.inquiry_id = inquiry_id
        self.scenario = scenario
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        self.path = TRACES_DIR / f"{self.run_id}.jsonl"

    # --- 書き出し ---
    def _write(self, event: str, **fields: Any) -> None:
        record = {
            "ts": _now(),
            "run_id": self.run_id,
            "event": event,
            **({"inquiry_id": self.inquiry_id} if self.inquiry_id else {}),
            **_redact(fields),
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # --- IPO 拡張表と同型のイベント（agent.md のフロー表に対応）---
    def record_run_start(self, *, attempt_no: int, model: str, max_turns: int) -> None:
        self._write(
            "run_start",
            attempt_no=attempt_no,
            model=model,
            max_turns=max_turns,
            scenario=self.scenario,
        )

    def record_input(self, prompt: str) -> None:
        self._write("input", prompt=prompt)

    def record_turn(self, turn: int) -> None:
        self._write("turn", turn=turn)

    def record_decision(self, text: str) -> None:
        self._write("decision", text=text)

    def record_tool_call(self, tool: str, tool_input: Any) -> None:
        self._write("tool_call", tool=tool, input=tool_input)

    def record_tool_result(self, tool: str, result: Any, *, is_error: bool = False) -> None:
        """要約が必要なツールは、中身ではなく summary を残す。"""
        if tool in SUMMARY_ONLY_TOOLS and isinstance(result, dict):
            self._write(
                "tool_result", tool=tool, summary=result.get("summary", {}), is_error=is_error
            )
        else:
            self._write("tool_result", tool=tool, result=result, is_error=is_error)

    def record_run_end(
        self,
        stop_reason: str,
        *,
        turns: int | None = None,
        elapsed_s: float | None = None,
        detail: str | None = None,
    ) -> None:
        """stop_reason は agent.md の停止条件と対応させる
        （completed / failed / max_turns / inner_timeout / inactivity_timeout / outer_timeout）。"""
        self._write(
            "run_end",
            stop_reason=stop_reason,
            turns=turns,
            elapsed_s=round(elapsed_s, 1) if elapsed_s is not None else None,
            detail=detail,
        )

    # --- 読み出し（進捗表示・評価用）---
    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]
