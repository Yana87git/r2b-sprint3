"""開発用: fixtures を1件登録してエージェントを通しで動かし、結果を要約する。

  uv run python scripts/dev_run_agent.py d1          # 登録して実行（案件は残す）
  uv run python scripts/dev_run_agent.py d5 --clean  # 実行後に案件を消す

トレースは backend/traces/{run_id}.jsonl に残る。
"""
import asyncio
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from sqlalchemy import delete, select  # noqa: E402

from app.agent import jobs  # noqa: E402
from app.agent.prompt import build_system_prompt  # noqa: E402
from app.agent.trace import TraceRecorder  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import Inquiry, InquiryInput, ItemRow  # noqa: E402
from app.services import dev_fixtures  # noqa: E402

REGISTERS = {
    "d1": dev_fixtures.register_d1,
    "d4": dev_fixtures.register_d4,
    "d5": dev_fixtures.register_d5,
}
USER_PROMPT = "投入された入力から品目リスト案を作り、完了条件を満たしたら終了してください。"
POLL_SECONDS = 5


async def main(name: str, clean: bool) -> None:
    # SQL のエコー（DEBUG 時）は結果の要約を埋めてしまうので黙らせる
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    async with AsyncSessionLocal() as session:
        inquiry = await REGISTERS[name](session)
        await session.commit()
        inquiry_id = inquiry.id
    print(f"案件: {inquiry_id}（{name}）")

    run_id = jobs.start_agent_job(
        USER_PROMPT,
        system_prompt=build_system_prompt(str(inquiry_id)),
        inquiry_id=str(inquiry_id),
        scenario=name,
    )
    print(f"run_id: {run_id}")
    job = jobs.get_job(run_id)
    while job.status == "running":
        await asyncio.sleep(POLL_SECONDS)
    result = job.result

    records = TraceRecorder(run_id=run_id).read()
    calls = Counter(
        r.get("tool", "").replace("mcp__app__", "")
        for r in records
        if r.get("event") == "tool_call"
    )
    print(f"\n停止理由: {job.status} / ターン: {getattr(result, 'turns', None)}")
    print(f"ツール: {dict(calls)}")

    async with AsyncSessionLocal() as session:
        saved = await session.get(Inquiry, inquiry_id)
        rows = (
            (await session.execute(select(ItemRow).where(ItemRow.inquiry_id == inquiry_id)))
            .scalars()
            .all()
        )
        inputs = (
            (
                await session.execute(
                    select(InquiryInput).where(InquiryInput.inquiry_id == inquiry_id)
                )
            )
            .scalars()
            .all()
        )
        print(f"案件の状態: {saved.status} / 理由: {saved.unreadable_reason} / 行数: {len(rows)}")
        for i in inputs:
            print(
                f"  - {i.display_name}: {i.status} / 理由 {i.unreadable_reason} / {i.row_count}行"
            )
        if clean:
            await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
            await session.commit()
            print("（案件を削除しました）")
    await engine.dispose()


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    fixture = (args[0] if args else "d1").lower()
    if fixture not in REGISTERS:
        raise SystemExit(f"使える fixture: {', '.join(REGISTERS)}")
    asyncio.run(main(fixture, "--clean" in sys.argv))
