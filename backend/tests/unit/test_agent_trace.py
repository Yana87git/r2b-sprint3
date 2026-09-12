"""Slice 0-7: トレースの形式と、秘密情報・原本を残さないこと（agent.md ガードレール）。"""
from app.agent.trace import TraceRecorder


def test_events_and_redaction(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.agent.trace.TRACES_DIR", tmp_path)
    t = TraceRecorder(inquiry_id="inq-1", scenario="unit")
    t.path = tmp_path / f"{t.run_id}.jsonl"

    t.record_run_start(attempt_no=1, model="claude-sonnet-5", max_turns=30)
    t.record_tool_call("read_file_content", {"input_id": "x", "api_key": "sk-ant-secret"})
    t.record_tool_result(
        "read_file_content",
        {
            "summary": {"file": "見積依頼.xlsx", "range": "明細!A10:G22", "rows": 13},
            "content": "原本" * 500,
        },
    )
    t.record_run_end("completed", turns=3, elapsed_s=1.23)

    records = t.read()
    assert [r["event"] for r in records] == ["run_start", "tool_call", "tool_result", "run_end"]
    # API キーは伏せる
    assert records[1]["input"]["api_key"] == "***"
    # read_file_content の結果は要約だけ。原本の中身は残さない
    assert records[2]["summary"]["rows"] == 13
    assert "content" not in records[2]
    assert records[3]["stop_reason"] == "completed"
