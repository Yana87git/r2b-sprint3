"""カスタムツール。

**本番の6つのツール（list_input_files / read_file_content / save_item_rows /
verify_sources / set_file_status / check_completion）は明日実装する。**
Slice 0-7 では、ループとトレースの疎通を確かめるための `ping` だけを置く。

- ツールは docs/requirements/agent.md「ツール一覧」と1対1で対応させる
- ツールに生 SQL・生 HTTP を書かない（service / repository を経由する）
- ツール名は mcp__app__{tool_name} の形式で allowed_tools に列挙する
"""
import json
import uuid
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool

from app.agent.context import current_inquiry_id
from app.core.database import AsyncSessionLocal
from app.services import completion_service, inquiry_service, item_draft_service
from app.services import source_verify_service
from app.services.input_reader import DEFAULT_LIMIT, InputNotReadableError, read_input


@tool("ping", "疎通確認用。受け取った message をそのまま返す", {"message": str})
async def ping(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"pong: {args['message']}"}]}


@tool(
    "list_input_files",
    "案件に投入された入力（ファイルとメール本文）の一覧を返す",
    {},
)
async def list_input_files(args: dict[str, Any]) -> dict[str, Any]:
    """§3-1。案件IDはサーバー側で注入する（LLM からは指定できない）。"""
    inquiry_id = current_inquiry_id()
    async with AsyncSessionLocal() as session:
        inputs = await inquiry_service.list_inputs(session, inquiry_id)
    payload = {
        "inputs": [
            {
                "input_id": str(i.id),
                "display_name": i.display_name,
                "format": i.format,
                "size_bytes": i.byte_size
                if i.byte_size is not None
                else len((i.content_text or "").encode("utf-8")),
                "status": i.status,
            }
            for i in inputs
        ]
    }
    return {"content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]}


@tool(
    "read_file_content",
    "入力の中身を、読み取り元として示せる位置つきで読む。1回に返る量には上限があり、"
    "続きがある場合は has_more と next が返る",
    {
        "input_id": str,
        "sheet": str,
        "page": int,
        "start": int,
        "limit": int,
    },
)
async def read_file_content(args: dict[str, Any]) -> dict[str, Any]:
    """§3-2。位置の書き方は ⑤ の locator_label と同じ（明細!C12 / p.2/14 / 表1/5/3 / L8）。"""
    inquiry_id = current_inquiry_id()
    try:
        input_uuid = uuid.UUID(str(args["input_id"]))
    except (KeyError, ValueError):
        return _error("input_id が不正です")

    async with AsyncSessionLocal() as session:
        # 他の案件の入力は取れない（サーバー側で案件IDを固定している）
        input_ = await inquiry_service.get_input(session, inquiry_id, input_uuid)
    if input_ is None:
        return _error("この案件に、その input_id の入力はありません")

    try:
        result = read_input(
            input_,
            sheet=args.get("sheet") or None,
            page=int(args.get("page") or 1),
            start=int(args.get("start") or 1),
            limit=int(args.get("limit") or DEFAULT_LIMIT),
        )
    except InputNotReadableError as e:
        # 判読不能の手がかり。set_file_status で記録するのはエージェントの判断
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "cells": [],
                            "has_more": False,
                            "has_readable_text": False,
                            "error": str(e),
                        },
                        ensure_ascii=False,
                    ),
                }
            ]
        }

    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


def _error(message: str) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps({"error": message}, ensure_ascii=False)}],
        "is_error": True,
    }


@tool(
    "save_item_rows",
    "品目リスト案を下書きとして保存する。案件のぶんを丸ごと置き換える。"
    "保存のたびに形式を検査し、誤りがあれば {row_no, field, message} の一覧を返す。"
    "rows の各要素は "
    '{"row_no":1,"source_input_id":"<入力ID>","values":{'
    '"item_name":{"raw_text":"深溝玉軸受","value":"深溝玉軸受","state":"extracted",'
    '"confidence":"high","clues":[],"source":{"input_id":"<入力ID>","locator":"明細!B10"}},'
    '"part_no":{...},"quantity":{...},"unit":{...},'
    '"due_date":{"raw_text":"10月末","kind":"fixed|month_range|needs_confirmation",'
    '"start_date":"2026-10-21","end_date":"2026-10-31","state":"extracted",'
    '"confidence":"high","clues":[],"source":{...}},"remarks":{...}}} の形。'
    "必須は item_name / part_no / quantity / unit / due_date の5つ。"
    "記載がない項目は state を needs_confirmation にし、source は付けない",
    {"rows": list},
)
async def save_item_rows(args: dict[str, Any]) -> dict[str, Any]:
    """§3-3。**検査で誤りが出ても保存する**（直して同じ行を送り直す前提）。"""
    inquiry_id = current_inquiry_id()
    rows = args.get("rows")
    if not isinstance(rows, list):
        return _error("rows は配列です")

    async with AsyncSessionLocal() as session:
        result = await item_draft_service.replace_rows(session, inquiry_id, rows)
        await session.commit()
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


@tool(
    "verify_sources",
    "保存した値の原文が、読み取り元の位置に本当にあるかを照合し、不一致の一覧を返す",
    {},
)
async def verify_sources(args: dict[str, Any]) -> dict[str, Any]:
    """§3-4。照合の実体は SourceVerifyService（check_completion の④と同じ処理）。"""
    inquiry_id = current_inquiry_id()
    async with AsyncSessionLocal() as session:
        mismatches = await source_verify_service.verify_all(session, inquiry_id)
    return {
        "content": [
            {"type": "text", "text": json.dumps({"mismatches": mismatches}, ensure_ascii=False)}
        ]
    }


@tool(
    "check_completion",
    "完了条件①〜⑥と失敗条件を判定し、案件の状態を決める。"
    "未達があれば incomplete と不足の一覧を返す",
    {},
)
async def check_completion(args: dict[str, Any]) -> dict[str, Any]:
    """§3-6・§4。案件の状態を変えられるのはこのツールだけ。"""
    inquiry_id = current_inquiry_id()
    async with AsyncSessionLocal() as session:
        result = await completion_service.check(session, inquiry_id)
        await session.commit()
    return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]}


AGENT_TOOLS = [
    ping,
    list_input_files,
    read_file_content,
    save_item_rows,
    verify_sources,
    check_completion,
]

agent_server = create_sdk_mcp_server(name="app", version="0.1.0", tools=AGENT_TOOLS)

ALLOWED_TOOL_NAMES = [
    "mcp__app__ping",
    "mcp__app__list_input_files",
    "mcp__app__read_file_content",
    "mcp__app__save_item_rows",
    "mcp__app__verify_sources",
    "mcp__app__check_completion",
]
