"""KPI8 の評価: D2 の8件を投入して、仕込んだ誤りが「確信が低い」として示されるか数える。

  uv run python scripts/eval_d2.py           # 8件すべて（4件ずつ並行）
  uv run python scripts/eval_d2.py c7 c8     # 指定した案件だけ
  uv run python scripts/eval_d2.py --keep    # 実行後に案件を残す（画面で見る用）

正解表は tests/fixtures/README.md「D2 の正解表」。
**人の操作（確定・見逃しの判定）は入らない。** ここで見るのはエージェントの判定だけ。
"""
import asyncio
import logging
import sys
import unicodedata
import uuid
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select  # noqa: E402

from app.agent import jobs  # noqa: E402
from app.agent.prompt import build_system_prompt  # noqa: E402
from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.models import Inquiry, ItemRow, ItemValue, ValueClue  # noqa: E402
from app.services.inquiry_intake_service import UploadedFile, create_inquiry  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "d2"
USER_PROMPT = "投入された入力から品目リスト案を作り、完了条件を満たしたら終了してください。"
PARALLEL = 4
POLL_SECONDS = 5


@dataclass
class Case:
    key: str
    folder: str
    clue: str
    marker: str  # 仕込んだ誤りを含む値（原文でも正規化後でもよい）
    field: str
    note: str
    rows_expected: int = 1  # H1 は「別の行として2行残る」ことを期待する
    inquiry_id: uuid.UUID | None = None
    run_id: str | None = None
    found: list[dict] = field(default_factory=list)


CASES = [
    Case("c1", "c1_excel_toa", "H2", "BRG-62O5-2RS", "model_no", "型番の 0 が英字 O"),
    Case("c2", "c2_excel_hokuriku", "H3", "m", "unit", "六角穴付きボルトの単位が m"),
    Case("c3", "c3_pdf_chuo", "H2", "OSL-l520-N", "model_no", "型番の 1 が小文字 l"),
    Case("c4", "c4_word_nishinihon", "H3", "2000", "quantity", "数量だけ 2000"),
    Case("c5", "c5_word_daiwa", "H2", "ＨＢＴ－Ｍ１０－４０", "model_no", "型番だけ全角"),
    Case("c6", "c6_mail_shinsei", "H3", "kg", "unit", "Oリングの単位が kg"),
    Case("c7", "c7_multi_miyou", "H1", "PPN-8-40", "model_no", "数量が 40 と 400", 2),
    Case("c8", "c8_multi_tokai", "H1", "ACY-SD40-150", "model_no", "納期が 10/31 と 11/30", 2),
]


def _normalize(text: str) -> str:
    """全角・半角の違いを吸収して比べる（仕込みが全角の件があるため）。"""
    return unicodedata.normalize("NFKC", str(text)).replace(" ", "").lower()


async def _register(case: Case) -> None:
    folder = FIXTURES / case.folder
    files: list[UploadedFile] = []
    mail_body: str | None = None
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() == ".txt":
            mail_body = path.read_text(encoding="utf-8")
        else:
            files.append(UploadedFile(filename=path.name, content=path.read_bytes()))
    async with AsyncSessionLocal() as session:
        inquiry, _ = await create_inquiry(session, files, mail_body)
        await session.commit()
        case.inquiry_id = inquiry.id


async def _run(case: Case) -> None:
    case.run_id = await jobs.start_agent_job(
        USER_PROMPT,
        system_prompt=build_system_prompt(str(case.inquiry_id)),
        inquiry_id=str(case.inquiry_id),
        scenario=f"d2-{case.key}",
    )
    job = jobs.get_job(case.run_id)
    while job.status == "running":
        await asyncio.sleep(POLL_SECONDS)


async def _collect(case: Case) -> dict:
    """仕込んだ誤りを含む行を探し、分類と手がかりを見る。"""
    async with AsyncSessionLocal() as session:
        inquiry = await session.get(Inquiry, case.inquiry_id)
        rows = list(
            (
                await session.execute(
                    select(ItemRow)
                    .where(ItemRow.inquiry_id == case.inquiry_id)
                    .order_by(ItemRow.row_no)
                )
            ).scalars()
        )
        values_by_row: dict[uuid.UUID, list[ItemValue]] = {}
        clues_by_value: dict[uuid.UUID, list[str]] = {}
        if rows:
            values = list(
                (
                    await session.execute(
                        select(ItemValue).where(ItemValue.item_row_id.in_([r.id for r in rows]))
                    )
                ).scalars()
            )
            for value in values:
                values_by_row.setdefault(value.item_row_id, []).append(value)
            if values:
                for clue in (
                    await session.execute(
                        select(ValueClue).where(ValueClue.item_value_id.in_([v.id for v in values]))
                    )
                ).scalars():
                    clues_by_value.setdefault(clue.item_value_id, []).append(clue.clue)

    marker = _normalize(case.marker)
    hits = []
    for row in rows:
        values = values_by_row.get(row.id, [])
        if not any(
            marker in _normalize(v.raw_text or "") or marker in _normalize(v.value_text or "")
            for v in values
        ):
            continue
        hits.append(
            {
                "row_no": row.row_no,
                "classification": row.classification,
                "clues": sorted({c for v in values for c in clues_by_value.get(v.id, [])}),
                "values": {
                    v.field: (v.value_text, v.raw_text, v.confidence, clues_by_value.get(v.id, []))
                    for v in values
                },
            }
        )
    case.found = hits
    return {
        "status": inquiry.status if inquiry else None,
        "rows": len(rows),
        "hits": hits,
    }


def _judge(case: Case, summary: dict) -> tuple[bool, str]:
    """検知できたか: 仕込んだ行が「確信が低い」で、期待した手がかりが付いているか。"""
    if not case.found:
        return False, "仕込んだ値の行が見つからない"
    classifications = {h["classification"] for h in case.found}
    clues = sorted({c for h in case.found for c in h["clues"]})
    if case.rows_expected > 1 and len(case.found) < case.rows_expected:
        return False, f"{case.rows_expected}行に分かれていない（{len(case.found)}行にまとめられた）"
    if not any(c == "low_confidence" for c in classifications):
        return False, f"確信が低いになっていない（{'・'.join(sorted(classifications))}）"
    if case.clue not in clues:
        return False, f"手がかりが {case.clue} でない（{'・'.join(clues) or 'なし'}）"
    return True, f"{case.clue} / {len(case.found)}行"


async def _cleanup(case: Case) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Inquiry).where(Inquiry.id == case.inquiry_id))
        await session.commit()


async def _one(case: Case) -> tuple[Case, dict]:
    await _register(case)
    await _run(case)
    return case, await _collect(case)


async def main(cases: list[Case], keep: bool) -> None:
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    results: dict[str, dict] = {}
    for i in range(0, len(cases), PARALLEL):
        wave = cases[i : i + PARALLEL]
        print(f"--- 実行中: {', '.join(c.key for c in wave)}")
        for case, summary in await asyncio.gather(*(_one(c) for c in wave)):
            results[case.key] = summary
            print(f"    {case.key} 完了（{summary['rows']}行 / {summary['status']}）")

    print("\n=== KPI8: 仕込んだ誤りの検知 ===")
    passed = 0
    for case in cases:
        summary = results[case.key]
        ok, detail = _judge(case, summary)
        passed += 1 if ok else 0
        mark = "OK  " if ok else "NG  "
        print(f"{mark}{case.key} 期待 {case.clue}: {case.note}")
        print(f"      → {detail}")
        for hit in case.found:
            values = " / ".join(
                f"{f}={v[0]!r}(原文 {v[1]!r}, {v[2]}, {'+'.join(v[3]) or '-'})"
                for f, v in hit["values"].items()
                if f in ("item_name", "model_no", "quantity", "unit", "due_date")
            )
            print(f"      行{hit['row_no']} [{hit['classification']}] {values}")
    print(f"\n合計 {passed} / {len(cases)} 件を検知")

    if not keep:
        for case in cases:
            await _cleanup(case)
        print("（案件を削除しました）")
    else:
        for case in cases:
            print(f"{case.key}: /inquiries/{case.inquiry_id}/items")
    await engine.dispose()


if __name__ == "__main__":
    keys = [a.lower() for a in sys.argv[1:] if not a.startswith("--")]
    selected = [c for c in CASES if not keys or c.key in keys]
    if not selected:
        raise SystemExit(f"使える案件: {', '.join(c.key for c in CASES)}")
    asyncio.run(main(selected, "--keep" in sys.argv))
