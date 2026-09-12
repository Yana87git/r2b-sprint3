"""カスタムツール。

**本番の6つのツール（list_input_files / read_file_content / save_item_rows /
verify_sources / set_file_status / check_completion）は明日実装する。**
Slice 0-7 では、ループとトレースの疎通を確かめるための `ping` だけを置く。

- ツールは docs/requirements/agent.md「ツール一覧」と1対1で対応させる
- ツールに生 SQL・生 HTTP を書かない（service / repository を経由する）
- ツール名は mcp__app__{tool_name} の形式で allowed_tools に列挙する
"""
from typing import Any

from claude_agent_sdk import create_sdk_mcp_server, tool


@tool("ping", "疎通確認用。受け取った message をそのまま返す", {"message": str})
async def ping(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": f"pong: {args['message']}"}]}


AGENT_TOOLS = [ping]

agent_server = create_sdk_mcp_server(name="app", version="0.1.0", tools=AGENT_TOOLS)

ALLOWED_TOOL_NAMES = ["mcp__app__ping"]
