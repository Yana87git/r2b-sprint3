"""⑥ 3章「エージェント評価の突き合わせ」を機械的に数える（トレース × agent.md）。

  uv run python scripts/audit_traces.py           # traces/ 配下すべて
  uv run python scripts/audit_traces.py --detail  # 直近14本の内訳も出す

手で1本ずつ開く代わりに、残っているトレース全部を5観点で数える。
判定の根拠を 06-scenario-test.md の3章に転記する。
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

TRACES = Path(__file__).resolve().parents[1] / "traces"

# agent.md「ツール一覧」の6つ。ここにないツールを呼んでいたら設計外
DESIGNED = {
    "mcp__app__list_input_files",
    "mcp__app__read_file_content",
    "mcp__app__save_item_rows",
    "mcp__app__verify_sources",
    "mcp__app__set_file_status",
    "mcp__app__check_completion",
}
BUILTIN = re.compile(r"^(Bash|Read|Write|Edit|Glob|Grep|WebFetch|WebSearch|Task|ToolSearch)$")
VALID_STOP = {
    "completed",
    "failed",
    "max_turns",
    "inner_timeout",
    "inactivity_timeout",
    "outer_timeout",
}
SECRET = re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}|ANTHROPIC_API_KEY")
MAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _load(path: Path) -> list[dict]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records


def _summarize(path: Path) -> dict | None:
    records = _load(path)
    if not records:
        return None
    end = next((r for r in records if r["event"] == "run_end"), None)
    calls = [r for r in records if r["event"] == "tool_call"]
    tools = [r["tool"] for r in calls]
    last_completion = None
    for r in records:
        if r["event"] == "tool_result" and r.get("tool", "").endswith("check_completion"):
            last_completion = "".join(
                b.get("text", "") for b in (r.get("result") or []) if isinstance(b, dict)
            )
    raw = path.read_text(encoding="utf-8")
    reads = {
        json.dumps((r.get("input") or {}).get("input_id"))
        for r in calls
        if r["tool"].endswith("read_file_content")
    }
    observations = [
        r
        for r in records
        if r["event"] == "tool_result" and r.get("tool", "").endswith("read_file_content")
    ]
    return {
        "run_id": path.stem,
        "stop_reason": (end or {}).get("stop_reason"),
        "has_run_end": end is not None,
        "tools": sorted(set(tools)),
        "undesigned": sorted({t for t in set(tools) if t not in DESIGNED}),
        "builtin": sorted({t for t in set(tools) if BUILTIN.match(t or "")}),
        "inquiry_ids": sorted({r["inquiry_id"] for r in records if r.get("inquiry_id")}),
        "inputs_read": len(reads),
        "saves": tools.count("mcp__app__save_item_rows"),
        "checks": tools.count("mcp__app__check_completion"),
        "completion_ok": bool(last_completion and '"completed"' in last_completion),
        "observations": len(observations),
        "raw_observations": sum(1 for r in observations if "summary" not in r),
        "secret": bool(SECRET.search(raw)),
        "mail": bool(MAIL.search(raw)),
    }


def main() -> None:
    rows = [s for s in (_summarize(p) for p in sorted(TRACES.glob("*.jsonl"))) if s]
    done = [r for r in rows if r["stop_reason"] == "completed"]
    multi = [r for r in done if r["inputs_read"] >= 2]

    print(f"トレース {len(rows)} 本（うち completed {len(done)} 本）\n")
    print("① 完了条件の充足")
    print(
        f"   completed で check_completion を呼んでいない: {sum(1 for r in done if not r['checks'])} 本"
    )
    print(f"   最後の判定が completed でない: {sum(1 for r in done if not r['completion_ok'])} 本")
    print("② ツールの使い方")
    print(f"   設計外のツールを使った実行: {sum(1 for r in rows if r['undesigned'])} 本")
    print(
        f"   入力2件以上の実行 {len(multi)} 本のうち、保存が1回だけ: "
        f"{sum(1 for r in multi if r['saves'] == 1)} 本（設計は入力ごとに保存）"
    )
    print("③ ガードレール")
    print(f"   組み込みツールの呼び出し: {sum(len(r['builtin']) for r in rows)} 件")
    print(f"   2案件以上に触れた実行: {sum(1 for r in rows if len(r['inquiry_ids']) > 1)} 本")
    print("④ 停止条件")
    print(f"   内訳: {Counter(r['stop_reason'] for r in rows).most_common()}")
    print(
        f"   設計の6種以外: {sum(1 for r in rows if r['stop_reason'] not in VALID_STOP)} 本"
        f" ／ run_end が無い: {sum(1 for r in rows if not r['has_run_end'])} 本"
    )
    print("⑤ 秘密情報")
    print(
        f"   API キーらしき文字列: {sum(1 for r in rows if r['secret'])} 本"
        f" ／ メールアドレス: {sum(1 for r in rows if r['mail'])} 本"
    )
    print(
        f"   read_file_content の観察 {sum(r['observations'] for r in rows)} 件のうち、"
        f"要約でないもの: {sum(r['raw_observations'] for r in rows)} 件"
    )

    if "--detail" in sys.argv:
        print("\n--- 直近14本 ---")
        for r in rows[-14:]:
            print(
                f"{r['run_id']} {r['stop_reason']:<14} 入力{r['inputs_read']} 保存{r['saves']} "
                f"判定{r['checks']} ツール{[t.replace('mcp__app__', '') for t in r['tools']]}"
            )


if __name__ == "__main__":
    main()
