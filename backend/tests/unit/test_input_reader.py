"""read_file_content の読み取り（§3-2）。位置の書き方は ⑤ の locator_label と同じ。"""
from pathlib import Path

import pytest

from app.models import InquiryInput
from app.services.input_reader import InputNotReadableError, read_input

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _file(name: str, fmt: str, path: Path) -> InquiryInput:
    return InquiryInput(kind="file", display_name=name, format=fmt, storage_path=str(path))


def test_excel_returns_sheet_and_cell_locator() -> None:
    r = read_input(
        _file("normal_excel.xlsx", "excel", FIXTURES / "d1" / "normal_excel.xlsx"), start=9, limit=2
    )
    assert r["has_readable_text"] is True
    assert any(c["locator"].startswith("明細!") for c in r["cells"])
    assert r["has_more"] is True and r["next"]["start"] == 11


def test_mail_body_returns_line_locator() -> None:
    text = "1行目\n\n3行目\n4行目\n"
    r = read_input(
        InquiryInput(
            kind="mail_body", display_name="メール本文", format="mail_body", content_text=text
        ),
        limit=3,
    )
    assert [c["locator"] for c in r["cells"]] == ["L1", "L3"]
    assert r["has_more"] is True and r["next"]["start"] == 4


def test_word_returns_paragraph_or_table_locator() -> None:
    docs = sorted(FIXTURES.rglob("*.docx"))
    r = read_input(_file(docs[0].name, "word", docs[0]), limit=5)
    assert all(c["locator"].startswith(("段落", "表")) for c in r["cells"])


def test_pdf_returns_page_and_line_locator() -> None:
    r = read_input(_file("normal_spec.pdf", "pdf", FIXTURES / "d1" / "normal_spec.pdf"), limit=4)
    assert all(c["locator"].startswith("p.1/") for c in r["cells"])


def test_scanned_pdf_has_no_readable_text() -> None:
    """テキストレイヤのないスキャンは判読不能の手がかりになる（② FUNC-07）。"""
    r = read_input(_file("scanned.pdf", "pdf", FIXTURES / "d4" / "scanned.pdf"))
    assert r["has_readable_text"] is False and r["cells"] == []


def test_broken_file_raises() -> None:
    with pytest.raises(InputNotReadableError):
        read_input(_file("broken.pdf", "pdf", FIXTURES / "d6" / "broken.pdf"))


def test_limit_is_capped() -> None:
    """1回に返る量には上限がある（コンテキストを守る）。"""
    r = read_input(
        _file("normal_excel.xlsx", "excel", FIXTURES / "d1" / "normal_excel.xlsx"),
        start=1,
        limit=10_000,
    )
    assert len(r["cells"]) <= 300
