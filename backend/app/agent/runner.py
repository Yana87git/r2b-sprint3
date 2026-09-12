"""エージェント実行ループ（内側タイムアウト・無応答検知・トレース記録）。

タイムアウトの責務分担（docs/build/agent-implementation-spec.md §5）:
- 内側（このファイル）: INNER_TIMEOUT_S（実行全体）と INACTIVITY_TIMEOUT_S（無応答＝ハング検知）。
  発火したらトレースに stop_reason を記録して整然と終了する
- 外側（jobs.py）: OUTER_TIMEOUT_S。内側が機能しなかったときの最後の砦

直接呼ばない: 起動は必ず jobs.start_agent_job() 経由（バックグラウンド実行＋外側タイムアウト）。
どの停止でも、保存済みの品目リスト案と読めた範囲は破棄しない。
"""
import asyncio
import time
from dataclasses import dataclass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

from app.agent import definition
from app.agent.tools import ALLOWED_TOOL_NAMES, agent_server
from app.agent.trace import TraceRecorder


@dataclass
class AgentRunResult:
    run_id: str
    stop_reason: str = "failed"
    turns: int | None = None
    elapsed_s: float | None = None
    output: str | None = None


def _build_options(system_prompt: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=definition.MODEL,
        max_turns=definition.MAX_TURNS,
        mcp_servers={"app": agent_server},
        allowed_tools=ALLOWED_TOOL_NAMES,
        # ガードレール: 組み込みツールは使わせない（agent.md「してはいけない操作」）
        disallowed_tools=[
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "WebFetch",
            "WebSearch",
            "Task",
            # ToolSearch は SDK 組み込みのツール探索。許可すると、設計にないツール呼び出しが
            # トレースに残り、⑥ のガードレール判定（設計どおりのツールだけを使ったか）が濁る
            "ToolSearch",
        ],
        permission_mode="bypassPermissions",
    )


async def run_agent(
    prompt: str,
    *,
    system_prompt: str,
    attempt_no: int = 1,
    trace: TraceRecorder | None = None,
) -> AgentRunResult:
    """1実行。trace は jobs.py が run_id を先に確定させるために注入する。"""
    trace = trace or TraceRecorder()
    result = AgentRunResult(run_id=trace.run_id)
    started = time.monotonic()

    trace.record_run_start(
        attempt_no=attempt_no, model=definition.MODEL, max_turns=definition.MAX_TURNS
    )
    trace.record_input(prompt)

    options = _build_options(system_prompt)
    turn = 0
    tool_names: dict[str, str] = {}  # tool_use_id → ツール名（結果の記録に使う）
    try:
        # 内側タイムアウト: 実行全体の上限
        async with asyncio.timeout(definition.INNER_TIMEOUT_S):
            stream = query(prompt=prompt, options=options).__aiter__()
            while True:
                try:
                    # 無応答タイムアウト: 次のメッセージが来るまでの上限（ハング検知）
                    message = await asyncio.wait_for(
                        stream.__anext__(), definition.INACTIVITY_TIMEOUT_S
                    )
                except StopAsyncIteration:
                    break
                except TimeoutError:
                    result.stop_reason = "inactivity_timeout"
                    trace.record_run_end(
                        "inactivity_timeout",
                        turns=turn,
                        elapsed_s=time.monotonic() - started,
                        detail=f"{definition.INACTIVITY_TIMEOUT_S}s 無応答",
                    )
                    result.elapsed_s = time.monotonic() - started
                    return result

                if isinstance(message, AssistantMessage):
                    turn += 1
                    trace.record_turn(turn)
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            trace.record_decision(block.text)
                        elif isinstance(block, ToolUseBlock):
                            tool_names[block.id] = block.name
                            trace.record_tool_call(block.name, block.input)
                elif isinstance(message, UserMessage):
                    for block in getattr(message, "content", []) or []:
                        if isinstance(block, ToolResultBlock):
                            trace.record_tool_result(
                                tool_names.get(block.tool_use_id, ""),
                                block.content,
                                is_error=bool(block.is_error),
                            )
                elif isinstance(message, ResultMessage):
                    if message.num_turns and message.num_turns >= definition.MAX_TURNS:
                        result.stop_reason = "max_turns"
                    else:
                        result.stop_reason = "completed" if not message.is_error else "failed"
                    result.turns = message.num_turns
                    result.output = message.result
    except TimeoutError:
        # 内側タイムアウト発火（agent.md の強制停止）。記録してから返す
        result.stop_reason = "inner_timeout"
        result.elapsed_s = time.monotonic() - started
        trace.record_run_end(
            "inner_timeout",
            turns=turn,
            elapsed_s=result.elapsed_s,
            detail=f"{definition.INNER_TIMEOUT_S}s 超過",
        )
        return result

    result.elapsed_s = time.monotonic() - started
    trace.record_run_end(result.stop_reason, turns=result.turns or turn, elapsed_s=result.elapsed_s)
    return result
