# -*- coding: utf-8 -*-
import sys, os, glob
from openpyxl import load_workbook
from docx import Document
from pypdf import PdfReader

FX = sys.argv[1]
ok = fail = 0
def chk(label, cond, extra=""):
    global ok, fail
    if cond: ok += 1;  print(f"  OK   {label} {extra}")
    else:    fail += 1; print(f"  FAIL {label} {extra}")

def xlsx_text(p):
    wb = load_workbook(p)
    return "\n".join(str(c.value) for ws in wb for row in ws.iter_rows() for c in row if c.value is not None)
def docx_text(p):
    d = Document(p)
    t = [q.text for q in d.paragraphs]
    for tb in d.tables:
        for r in tb.rows: t += [c.text for c in r.cells]
    return "\n".join(t)
def pdf_text(p):
    return "\n".join((pg.extract_text() or "") for pg in PdfReader(p).pages)

print("== D1 正常系 ==")
t = xlsx_text(f"{FX}/d1/normal_excel.xlsx")
chk("明細12行ぶんの品目がある", t.count("BRG-") + t.count("HBT-") + t.count("ORG-") >= 4)
chk("「3箱(1箱50本)」がある", "3箱(1箱50本)" in t)
chk("「10月末」がある", "10月末" in t)
chk("小計行がある", "小計" in t)
wb = load_workbook(f"{FX}/d1/normal_excel.xlsx"); ws = wb["明細"]
chk("見出しが9行目（agent.md の実行例どおり）", ws.cell(row=9, column=1).value == "No",
    f"→ A9={ws.cell(row=9,column=1).value!r}")
chk("明細+小計が10〜22行目", ws.cell(row=10,column=1).value == 1 and ws.cell(row=22,column=2).value == "小計")
t = pdf_text(f"{FX}/d1/normal_spec.pdf")
chk("仕様書に追加品目1がある", "LMB-15-UU" in t)
chk("仕様書に材質NBRの補足がある", "NBR" in t)

print("== D2 受入8件：仕込んだ誤り ==")
c1 = xlsx_text(f"{FX}/d2/c1_excel_toa/見積依頼_東亜精機.xlsx")
chk("C1 H2 型番の0→英字O", "BRG-62O5-2RS" in c1 and "BRG-6205-2RS" in c1)
c2 = xlsx_text(f"{FX}/d2/c2_excel_hokuriku/RFQ_Hokuriku.xlsx")
chk("C2 H3 ボルトの単位が m", "HBT-M8-25" in c2 and "\nm" in "\n"+c2)
chk("C2 初見の書式（縦持ち・英語見出し）", "Part No." in c2 and "Line 1" in c2)
c3 = pdf_text(f"{FX}/d2/c3_pdf_chuo/見積依頼_中央テクノ.pdf")
chk("C3 H2 型番の1→小文字l", "OSL-l520-N" in c3 and "OSL-1520-N" in c3)
c4 = docx_text(f"{FX}/d2/c4_word_nishinihon/見積依頼_西日本機工.docx")
chk("C4 H3 数量だけ2000", "2000" in c4)
c5 = docx_text(f"{FX}/d2/c5_word_daiwa/部品手配依頼_大和バルブ.docx")
chk("C5 H2 型番だけ全角", "ＨＢＴ－Ｍ１０－４０" in c5 and "HBT-M10-35" in c5)
chk("C5 初見の書式（表ではなく箇条書き）", "【1】" in c5 and len(Document(f"{FX}/d2/c5_word_daiwa/部品手配依頼_大和バルブ.docx").tables) == 0)
c6 = open(f"{FX}/d2/c6_mail_shinsei/mail_shinsei.txt", encoding="utf-8").read()
chk("C6 H3 Oリングの単位が kg", "単位 kg" in c6)
c7x = xlsx_text(f"{FX}/d2/c7_multi_miyou/見積依頼_三葉工業.xlsx")
c7p = pdf_text(f"{FX}/d2/c7_multi_miyou/仕様書_三葉工業.pdf")
chk("C7 H1 数量が Excel 40 / PDF 400 で食い違う",
    "PPN-8-40" in c7x and "PPN-8-40" in c7p and "40" in c7x and "400" in c7p)
c8m = open(f"{FX}/d2/c8_multi_tokai/mail_tokai.txt", encoding="utf-8").read()
c8w = docx_text(f"{FX}/d2/c8_multi_tokai/部品依頼書_東海精密.docx")
chk("C8 H1 納期が メール10/31 / Word 11/30 で食い違う",
    "2026-10-31" in c8m and "2026-11-30" in c8w and "ACY-SD40-150" in c8m and "ACY-SD40-150" in c8w)

print("== D2 構成（4形式が各2回以上・複数入力2件）==")
counts = {"Excel": 0, "PDF": 0, "Word": 0, "メール本文": 0}
for d in sorted(glob.glob(f"{FX}/d2/*")):
    for f in glob.glob(f"{d}/*"):
        e = os.path.splitext(f)[1]
        counts["Excel" if e == ".xlsx" else "PDF" if e == ".pdf" else "Word" if e == ".docx" else "メール本文"] += 1
multi = sum(1 for d in glob.glob(f"{FX}/d2/*") if len(glob.glob(f"{d}/*")) > 1)
chk("案件が8件", len(glob.glob(f"{FX}/d2/*")) == 8)
chk("複数入力が2件", multi == 2)
for k, v in counts.items():
    chk(f"{k} が2回以上", v >= 2, f"→ {v}回")

print("== D3〜D7 ==")
m = sorted(glob.glob(f"{FX}/d3/*"))
chk("D3 が10件", len(m) == 10)
lack = 0
for p in m:
    e = os.path.splitext(p)[1]
    t = xlsx_text(p) if e == ".xlsx" else pdf_text(p) if e == ".pdf" else docx_text(p) if e == ".docx" else open(p, encoding="utf-8").read()
    if "（未定）" in t or e in (".xlsx", ".pdf", ".docx"): lack += 1
chk("D3 全件が読める", lack == 10)
sc = f"{FX}/d4/scanned.pdf"
chk("D4 にテキストレイヤが無い", pdf_text(sc).strip() == "", f"→ 抽出文字数 {len(pdf_text(sc).strip())}")
chk("D4 のページ数が1", len(PdfReader(sc).pages) == 1)
g = open(f"{FX}/d5/greeting_mail.txt", encoding="utf-8").read()
chk("D5 に明細らしい行が無い", not any(k in g for k in ["数量", "型番", "単位"]))
try:
    pdf_text(f"{FX}/d6/broken.pdf"); chk("D6 が読めない", False, "→ 読めてしまった")
except Exception as ex:
    chk("D6 が読めない", True, f"→ {type(ex).__name__}")
chk("D7 対応外拡張子 .csv がある", os.path.exists(f"{FX}/d7/unsupported.csv"))
chk("D7 old.xls が OLE2 署名を持つ",
    open(f"{FX}/d7/old.xls","rb").read(8) == bytes([0xD0,0xCF,0x11,0xE0,0xA1,0xB1,0x1A,0xE1]))
chk("D7 11件目ぶんのファイルがある", len(glob.glob(f"{FX}/d7/many/*.pdf")) == 11)
big = max(os.path.getsize(p) for p in glob.glob(f"{FX}/**/*", recursive=True) if os.path.isfile(p))
chk("最大ファイルが1MB未満（リポジトリに置ける）", big < 1_000_000, f"→ {big/1024:.0f}KB")
print(f"\n合計: OK {ok} / FAIL {fail}")
sys.exit(1 if fail else 0)
