# -*- coding: utf-8 -*-
import sys, os, random, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_common import *
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1]
D = lambda *p: os.path.join(OUT, *p)
random.seed(20260912)

# ---------------------------------------------------------------- D3 欠落10件
# 各件に「納期が空」または「数量が空」の行を1つ以上含める。形式は散らす。
MISSING = [
    ("m01_excel_asahi.xlsx", "excel", "旭工機株式会社", "納期",
     [[1, "深溝玉軸受", "BRG-6206-2RS", 18, "個", "2026-11-06"],
      [2, "オイルシール", "OSL-2542-N", 24, "個", ""],
      [3, "止め輪", "SNP-C-25", 40, "個", "2026-11-06"]]),
    ("m02_excel_kitami.xlsx", "excel", "北見製作所株式会社", "数量",
     [[1, "リニアガイド", "LGR-15-250", "", "本", "2026-11-13"],
      [2, "ボールねじ", "BSC-1605-300", 2, "本", "2026-11-13"]]),
    ("m03_pdf_sakura.pdf", "pdf", "さくら機械工業株式会社", "納期",
     [[1, "カップリング", "CPL-D25-6-8", 10, "個", ""],
      [2, "軸受ユニット", "UCF-204", 6, "個", "2026-11-20"]]),
    ("m04_pdf_nagano.pdf", "pdf", "長野精工株式会社", "数量",
     [[1, "六角穴付きボルト", "HBT-M6-20", 250, "本", "2026-11-10"],
      [2, "平座金", "WSH-M6-F", "", "枚", "2026-11-10"],
      [3, "六角ナット", "NUT-M6-1", 250, "個", "2026-11-10"]]),
    ("m05_word_ryukyu.docx", "word", "琉球機材株式会社", "納期",
     [[1, "エアシリンダ", "ACY-SD25-75", 4, "個", ""],
      [2, "ソレノイドバルブ", "SLV-4V110-06", 4, "個", "2026-11-17"]]),
    ("m06_word_echigo.docx", "word", "越後工業株式会社", "数量",
     [[1, "Vベルト", "VBL-A-40", 6, "本", "2026-11-24"],
      [2, "プーリー", "PLY-A2-100", "", "個", "2026-11-24"]]),
    ("m07_mail_hinode.txt", "mail", "日の出商事株式会社", "納期",
     [[1, "グリースニップル", "GNP-A-M8", 60, "個", ""],
      [2, "ガスケット", "GSK-JIS10K-40A", 15, "枚", "2026-11-27"]]),
    ("m08_mail_kaimon.txt", "mail", "開門産業株式会社", "数量",
     [[1, "平行ピン", "PPN-6-25", "", "本", "2026-12-01"],
      [2, "キー材", "KEY-6-6-80", 20, "本", "2026-12-01"]]),
    ("m09_excel_tsurumi.xlsx", "excel", "鶴見テクノ株式会社", "納期",
     [[1, "Oリング", "ORG-P20", 30, "個", ""],
      [2, "Oリング", "ORG-P24", 30, "個", ""],
      [3, "Vリング", "VRG-V-30A", 12, "個", "2026-12-04"]]),
    ("m10_pdf_oita.pdf", "pdf", "大分機工株式会社", "数量",
     [[1, "スプリングピン", "SPN-6-30", 45, "本", "2026-12-08"],
      [2, "全ねじボルト", "FTB-M8-1000", "", "本", "2026-12-08"],
      [3, "止め輪", "SNP-E-8", 100, "個", "2026-12-08"]]),
]
HEAD = ["No", "品目名", "型番", "数量", "単位", "希望納期"]
for fname, kind, company, lack, rows in MISSING:
    meta = ["株式会社ミナト精機 御中", "発行日: 2026-10-16", f"発注元: {company} 購買担当", ""]
    p = D("d3", fname)
    if kind == "excel":
        xlsx_table(p, ["見積依頼書", ""] + meta[:3], HEAD, rows, header_row=7,
                   col_widths=[6, 26, 20, 10, 8, 16])
    elif kind == "pdf":
        pdf_doc(p, "見積依頼書", meta, headers=HEAD, rows=rows,
                col_x=[50, 90, 240, 360, 410, 460])
    elif kind == "word":
        docx_table(p, "見積依頼書", meta, HEAD, rows)
    else:
        lines = [f"{r[0]}. {r[1]} / {r[2]} / 数量 {r[3] or '（未定）'} / 単位 {r[4]} / 納期 {r[5] or '（未定）'}"
                 for r in rows]
        write_text(p, f"""From: {company} 購買担当 <buyer@example.co.jp>
To: 株式会社ミナト精機 営業部 <eigyo@minato-seiki.example.co.jp>
Subject: 見積依頼の件
Date: 2026-10-16

ミナト精機 営業部 御中

お世話になっております。{company}です。
下記についてお見積りをお願いいたします。

""" + "\n".join(lines) + "\n\nよろしくお願いいたします。\n")

# ---------------------------------------------------------------- D4 スキャン
# テキストレイヤを持たない画像だけのPDF（手書き・FAX由来を模す）
W, H = 1240, 1754                       # A4 150dpi
img = Image.new("L", (W, H), 255)
dr = ImageDraw.Draw(img)
f_big = ImageFont.truetype(FONT, 46)
f_mid = ImageFont.truetype(FONT, 30)
f_sml = ImageFont.truetype(FONT, 26)
dr.text((360, 90), "御 見 積 依 頼 書", font=f_big, fill=40)
for i, line in enumerate(["株式会社ミナト精機 御中", "発行日  2026年10月19日",
                          "発注元  丸美鉄工所  受注係"]):
    dr.text((110, 200 + i * 44), line, font=f_mid, fill=45)
y = 380
cols = [110, 200, 560, 820, 950, 1080]
for x, h in zip(cols, ["No", "品目名", "型番", "数量", "単位", "納期"]):
    dr.text((x, y), h, font=f_sml, fill=45)
dr.line((100, y + 40, 1150, y + 40), fill=60, width=3)
rows = [[1, "深溝玉軸受", "BRG-6204", 12, "個", "11/6"],
        [2, "オイルシール", "OSL-2035", 8, "個", "11/6"],
        [3, "六角ボルト", "HBT-M8-25", 100, "本", "11/13"]]
for r_i, row in enumerate(rows):
    yy = y + 70 + r_i * 52
    for x, v in zip(cols, row):
        dr.text((x, yy), str(v), font=f_sml, fill=50)
dr.text((110, 700), "※ 手書き分は別紙のとおり", font=f_sml, fill=55)
# FAX らしい劣化: 傾き・かすれ・走査ノイズ・黒帯
img = img.rotate(-1.1, resample=Image.BICUBIC, fillcolor=255, expand=False)
px = img.load()
for _ in range(240000):
    x, y2 = random.randrange(W), random.randrange(H)
    px[x, y2] = 255 if px[x, y2] < 128 else random.choice([0, 40, 90, 255, 255])
for _ in range(70):                      # 走査線
    yy = random.randrange(H)
    dr2 = ImageDraw.Draw(img)
    dr2.line((0, yy, W, yy), fill=random.choice([120, 170, 200]), width=1)
dr2 = ImageDraw.Draw(img)
dr2.rectangle((0, 0, W, 14), fill=30)    # 上端の黒帯
img = img.convert("1")                   # 2値化（FAX相当）
os.makedirs(D("d4"), exist_ok=True)
img.save(D("d4", "scanned.pdf"), "PDF", resolution=150.0)

# ---------------------------------------------------------------- D5 あいさつのみ
write_text(D("d5", "greeting_mail.txt"), """From: 株式会社ミナト精機 営業部 高橋 <takahashi@minato-seiki.example.co.jp>
To: 営業事務 <jimu@minato-seiki.example.co.jp>
Subject: Fwd: ご挨拶と今後のお取引について
Date: 2026-10-20

中村さん

お世話になります。高橋です。
下記、新規のお客様から届いたメールを転送します。
引合の中身はこれから送られてくるとのことですが、
念のため先に登録しておいてください。

---------- 転送メッセージ ----------
From: 甲州マシナリー株式会社 営業部 <sales@koshu-machinery.example.co.jp>
Subject: ご挨拶と今後のお取引について

株式会社ミナト精機
営業部 ご担当者様

はじめてご連絡いたします。
甲州マシナリー株式会社の営業部 渡辺と申します。

このたび弊社の生産設備更新にあたり、
貴社のお取り扱い部品について幅広くご相談させていただきたく、
ご挨拶かたがたご連絡差し上げました。

つきましては、近日中に必要部品のリストをお送りいたしますので、
お見積りのご対応をお願いできればと存じます。

まずは書面にてご挨拶申し上げます。
今後ともどうぞよろしくお願いいたします。

--
甲州マシナリー株式会社 営業部 渡辺
""")

# ---------------------------------------------------------------- D6 破損PDF
pdf_doc(D("d6", "_tmp_src.pdf"), "見積依頼書",
        ["株式会社ミナト精機 御中", "発行日: 2026-10-21", "発注元: 甲信電機株式会社", ""],
        headers=HEAD, rows=[[1, "リニアブッシュ", "LMB-20-UU", 10, "個", "2026-11-30"]],
        col_x=[50, 90, 240, 360, 410, 460])
raw = open(D("d6", "_tmp_src.pdf"), "rb").read()
cut = raw[: int(len(raw) * 0.40)]                       # 末尾（xref・trailer）が無い
ba = bytearray(cut)
for i in range(len(ba) // 3, len(ba) // 3 + 512):       # 途中のストリームも破壊
    ba[i] = (ba[i] + 137) % 256
open(D("d6", "broken.pdf"), "wb").write(bytes(ba))
os.remove(D("d6", "_tmp_src.pdf"))

# ---------------------------------------------------------------- D7 拒否される入力
write_text(D("d7", "unsupported.csv"),
           "No,品目名,型番,数量,単位,希望納期\n"
           "1,深溝玉軸受,BRG-6205-2RS,20,個,2026-11-30\n"
           "2,Oリング,ORG-P22,50,個,2026-11-30\n")
# .xls（旧 Excel 形式）: OLE2 複合ファイルのシグネチャを持つダミー
os.makedirs(D("d7"), exist_ok=True)
ole = bytes([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1]) + bytes(504) + b"Workbook" + bytes(3584)
open(D("d7", "old.xls"), "wb").write(ole)
# 11件目のファイル（10件の上限を超えさせるための小さなPDF）
for i in range(1, 12):
    pdf_doc(D("d7", "many", f"part_{i:02d}.pdf"), f"見積依頼書（分割 {i}/11）",
            ["株式会社ミナト精機 御中", "発行日: 2026-10-22", "発注元: 試験用ダミー", ""],
            headers=HEAD, rows=[[1, "平行ピン", f"PPN-6-{20 + i}", 10, "本", "2026-11-30"]],
            col_x=[50, 90, 240, 360, 410, 460])
print("D3-D7 generated")
