"""D3（欠落10件）を投入して読み取らせる（⑥ TEST-06）。

  uv run python scripts/run_d3.py          # 10件（4件ずつ並行）
  uv run python scripts/run_d3.py m01 m02  # 指定した件だけ

読み取りまでで止める。確認と確定は人が画面で行い、そのときの時刻差で KPI1 を測る。
"""
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.agent import jobs  # noqa: E402
from app.agent.prompt import build_system_prompt  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import Inquiry, ItemRow, ItemValue  # noqa: E402
from app.services.inquiry_intake_service import UploadedFile, create_inquiry  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "d3"
USER_PROMPT = "投入された入力から品目リスト案を作り、完了条件を満たしたら終了してください。"
PARALLEL = 4
POLL_SECONDS = 5


async def _run_one(path: Path) -> dict:
    files: list[UploadedFile] = []
    mail_body: str | None = None
    if path.suffix.lower() == ".txt":
        mail_body = path.read_text(encoding="utf-8")
    else:
        files.append(UploadedFile(filename=path.name, content=path.read_bytes()))

    async with AsyncSessionLocal() as session:
        inquiry, _ = await create_inquiry(session, files, mail_body)
        await session.commit()
        inquiry_id = inquiry.id

    run_id = await jobs.start_agent_job(
        USER_PROMPT,
        system_prompt=build_system_prompt(str(inquiry_id)),
        inquiry_id=str(inquiry_id),
        scenario=f"d3-{path.stem}",
    )
    job = jobs.get_job(run_id)
    while job.status == "running":
        await asyncio.sleep(POLL_SECONDS)

    async with AsyncSessionLocal() as session:
        saved = await session.get(Inquiry, inquiry_id)
        rows = list(
            (
                await session.execute(
                    select(ItemRow).where(ItemRow.inquiry_id == inquiry_id).order_by(ItemRow.row_no)
                )
            ).scalars()
        )
        values = (
            list(
                (
                    await session.execute(
                        select(ItemValue).where(ItemValue.item_row_id.in_([r.id for r in rows]))
                    )
                ).scalars()
            )
            if rows
            else []
        )
    missing = [
        (v.field, next(r.row_no for r in rows if r.id == v.item_row_id))
        for v in values
        if v.state == "needs_confirmation"
    ]
    return {
        "file": path.name,
        "inquiry_id": str(inquiry_id),
        "status": saved.status,
        "stop_reason": job.status,
        "rows": len(rows),
        "missing": sorted(missing, key=lambda m: (m[1], m[0])),
    }


async def main(paths: list[Path]) -> None:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    results = []
    for i in range(0, len(paths), PARALLEL):
        wave = paths[i : i + PARALLEL]
        print(f"--- 実行中: {', '.join(p.stem for p in wave)}")
        results.extend(await asyncio.gather(*(_run_one(p) for p in wave)))

    print("\n=== D3 の読み取り結果（欠けている項目が「要確認」になっているか）===")
    for r in results:
        missing = "・".join(f"{row_no}行目の{field}" for field, row_no in r["missing"]) or "なし"
        print(f"{r['file']:26} {r['status']:16} {r['rows']}行  要確認: {missing}")
        print(f"    /inquiries/{r['inquiry_id']}/items")
    await engine.dispose()


if __name__ == "__main__":
    keys = [a.lower() for a in sys.argv[1:] if not a.startswith("--")]
    selected = sorted(p for p in FIXTURES.iterdir() if not keys or p.stem.split("_")[0] in keys)
    if not selected:
        raise SystemExit("D3 のファイルが見つからない")
    asyncio.run(main(selected))
