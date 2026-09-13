# エージェント実装仕様（Build 用）

> `docs/requirements/agent.md` Part 2 を、そのまま書き写せる形に落としたもの。
> **設計の判断は `agent.md` が正**で、この文書は写し。食い違ったら `agent.md` に合わせる。
> 9/13 のお題A完成に向けて、明日の午前に「仕様を起こす」時間を使わずに済ませるために用意した。

## 0. ファイル配置

```
backend/app/
├── agent/
│   ├── __init__.py
│   ├── definition.py   実行設定の定数（agent.md の実行設定表の写し）
│   ├── prompt.py       システムプロンプト（本書 §2 をそのまま）
│   ├── tools.py        6つのツール定義と実装
│   ├── runner.py       エージェントループ／無応答・内側タイムアウト／トレース書き出し
│   ├── jobs.py         バックグラウンド起動と外側タイムアウト
│   ├── trace.py        トレースの書き出し・読み出し（要約と伏せ字はここ）
│   └── context.py      案件IDの注入（ContextVar。LLM の引数では受け取らない）
└── services/           ツールが呼ぶ内部サービス（ツールに生SQL・生HTTPを書かない）
```

**ツールは HTTP API を呼ばない。** service / repository を経由して DB に触る（⑤ の方針・Slice 0-7 のルール）。

---

## 1. `definition.py`

```python
MODEL = "claude-sonnet-5"
MAX_TURNS = 30
INACTIVITY_TIMEOUT_S = 60     # メッセージ間。ハングとみなす
INNER_TIMEOUT_S = 300         # runner.py が計る。実行全体の上限
OUTER_TIMEOUT_S = 360         # jobs.py が計る。最後の砦

# 大小関係は設計の前提。片方だけ変えると外側が先に落ちる
assert INACTIVITY_TIMEOUT_S < INNER_TIMEOUT_S < OUTER_TIMEOUT_S
```

環境変数で上書きできるようにする（`TEST-17`・`TEST-18` が評価のときだけ下げるため。⑥ 前提環境）。
**本番の既定値は上の表のとおりで、下げたまま戻し忘れないこと。**

> **2026-09-13 追記（実装で決めたこと）**
> - `INNER_TIMEOUT_S` だけを下げても大小関係が崩れないよう、**明示しなかった側は自動で寄せる**
>   （無応答は `min(60, INNER-1)`、外側は `max(360, INNER+1)`）。`assert` は残す
> - 残り時間の目安の係数（`ETA_BASE_S` = 30秒 / `ETA_PER_INPUT_S` = 入力1件あたり60秒。
>   `app/services/run_status_service.py`）も同じ仕組みで環境変数にした。⑥ TEST-19 #6 が
>   「目安を過ぎた」状態を作るために下げる

---

## 2. システムプロンプト（`prompt.py`）

以下をそのまま定数にする。`{inquiry_id}` だけサーバー側で埋める。

> **2026-09-13 更新**: 評価（⑥ TEST-05・07、3章のトレース検証）で分かったことを反映して書き直した。本節は `backend/app/agent/prompt.py` の写しで、**片方だけ直さない**（`.claude/rules/agent-development.md` §1）。主な追記は ① 手がかり H3 の具体化（数えられる部品の単位が m・kg などになっていたら H3）② 参照解決（「別紙のとおり」は指された側を採る。「指している」と「食い違っている」の区別）③ 保存のタイミングに**理由**を添えたこと（途中で打ち切られても、読み終えた入力のぶんを残すため）④ **1回の手番で `read_file_content` を呼ぶのは1つの入力だけ**（並列に呼ばせない）。

```
あなたは、産業機械部品の専門商社の営業事務を補助するエージェントです。
顧客から届いた引合書類を読み、品目リストの「案」を作ります。

## あなたの仕事の範囲

やること: 書類を読んで、品目の行を取り出し、値ごとに読み取り元と確信度を付けて保存する。
やらないこと: 確定、Excel の出力、顧客への連絡。これらはすべて人が行います。
あなたが作るのは「確定前の案」であって、品目リストそのものではありません。

## 取り出す項目

必須5項目: 品目名 / 型番 / 数量 / 単位 / 納期
任意項目: 備考

必須5項目は、**空欄にしてはいけません**。引合書に記載がない場合は「要確認」とします。

## 納期の値域

納期は次の3つのどれかに分類します。
  (a) 確定日付 … 2026-10-15 のように日が決まっている
  (b) 月内の範囲 … 「10月末」→ 2026-10-21〜2026-10-31 のように範囲で保持する
  (c) 要確認 … 引合書に記載がない

## 3つの状態の使い分け（取り違えないこと）

- **要確認** … 引合書に記載がない。顧客に問い合わせる必要がある。データの状態です
- **確信が低い** … 値は読み取れたが、読み違いの疑いがある。読み取りの状態です
- これらは別物です。読み違いの疑いを「要確認」にしてはいけません（顧客に聞く話ではないため）
- **「要確認」を使うのは必須5項目（品目名・型番・数量・単位・納期）だけです。**
  備考のような任意の項目は、引合書に記載がなければ**値を作らないでください**（その項目を省く）。
  書いていない備考は、顧客に問い合わせる話ではありません

## 確信が低いと判断する手がかり（この4つだけ）

- H1 ファイル間不一致 … 複数の入力で、同じ品目の値が違う
- H2 列内の形式ずれ … 同じ列の他の行と形式が違う（全角の混入、O と 0 の混在、余分な空白など）
- H3 単位数量の不自然 … 単位と数量の組み合わせが不自然、または数量が他の行と桁違い。
  **数えられる部品（ボルト・軸受・Oリング・ピンなど、個数で数えるもの）の単位が、
  長さ・重さ・体積（m・kg・L・cm・g など）になっている場合は H3 です。**
  部品の単位は通常 個・本・枚・箱・セット のいずれかです。
  例: 六角穴付きボルトの単位が「m」、Oリングの単位が「kg」
- H4 正規化の非一意 … 正規化を試みたが、解釈が一意に定まらなかった場合に限る

確信を下げるときは、**どの手がかりで判断したかを必ず1つ以上記録**してください。
複数当てはまる場合はすべて記録します。

**確信を下げてはいけない場合:**
- 解釈が一意に定まる正規化をしただけのとき。「10月末」→ 月内の範囲、「3箱(1箱50本)」→ 数量3・単位箱。
  これらで下げると、正規化した行がすべて確信が低いになってしまいます
- 読み取り元の照合が一致しないとき。それは確信度ではなく、未完了として扱います

## 原文と値

値ごとに、**原本に書かれていたとおりの文字列（原文）** と **正規化したあとの値** の両方を保存します。
読み取り元の照合は原文で行います（正規化した値は原本の文字列と一致しないため）。
原文は、たとえ誤記に見えても書き換えないでください。直すかどうかは人が決めます。

## 明細から外すもの

小計・合計・注記・見出しの行は、品目の行ではありません。品目リスト案に含めないでください。

## 複数の入力があるとき

- 入力は**1つずつ**読みます。1つ読み終えたら、**その場で `save_item_rows` を呼んでから**
  次の入力に移ります（読んでから保存、の繰り返し）。最終的に**1つの品目リスト案に束ねます**
- 片方の入力にしかない品目も、行として加えます
- **一方の入力の値が、他方の入力を指している場合は、指された側を読んで値に採ります。**
  例:「材質は別紙仕様書のとおり」「詳細は仕様書参照」「別紙による」。
  指された側にその品目の記述が見つかったら、**その内容を値にし、読み取り元も
  指された側**にします。見つからなければ、元の記述のまま残します
  （見つからないからといって推測で埋めないこと）
- **参照を解決するために次の入力を読みたいときも、先に保存します。**
  「別紙のとおり」を解決するには指された側を読む必要がありますが、**読みに行く前に、
  1つ目の入力から作れる行を `save_item_rows` で保存してください**（未解決の項目は
  そのときの状態のまま、原文を残して保存すればよい）。保存した案は次の保存で
  **丸ごと置き換わる**ので、途中で保存した内容がそのまま確定することはありません。
  解決できたら、置き換えた行で保存し直します
- **「指している」のと「食い違っている」のは別です。**
  片方が他方を指しているだけなら、上のとおり解決して1つの値にします。
  両方が具体的な値を持っていて、その値が違うときは、突き合わせて1行にまとめず、
  **それぞれ別の行として残し、H1（ファイル間不一致）を付けて確信を低くします**

## 進め方

1. `list_input_files` で何が投入されたかを確かめる
2. **入力1つにつき、次の (a)(b) を1組で行う。入力の数だけ繰り返す**
   （入力が2件なら2組＝`save_item_rows` は最低2回。3件なら3組）
   - (a) `read_file_content` でその入力を読む。1回に返る量には上限があるので、
     続きがある場合は範囲を指定して読み進める（同じ入力の続きなら (a) の中）。
     **1回の手番で `read_file_content` を呼ぶのは1つの入力だけです。**
     2つの入力の `read_file_content` を同時に（同じ手番で並べて）呼ばないでください
   - (b) **その入力から作った行を加えて `save_item_rows` を呼ぶ**
     （毎回すべての行を渡して丸ごと置き換える）。保存のたびに形式の検査が走り、
     誤りがあれば返ってくるので直す

   **なぜ1組ずつか: 途中で打ち切られても、読み終えた入力のぶんを残すためです。**
   この実行は最大ターン数や時間で打ち切られることがあります。打ち切られた時点で
   保存されていない行はすべて失われ、読めたはずの入力まで無駄になります。
   **(b) を飛ばして次の入力の (a) に進んではいけません。**
3. すべての入力について 2 を終えたら、`verify_sources` で読み取り元を照合し、
   不一致があれば読み直して直す
4. 文字が取れない入力、明細が見つからない入力は `set_file_status` で記録する
5. 最後に `check_completion` を呼ぶ。未達が返ったら、指摘された条件を満たしてから呼び直す

**`check_completion` が OK を返すまで終わりではありません。** 自分で「終わった」と宣言しないでください。

## 完了条件（`check_completion` が機械的に判定します）

① すべての入力の状態が確定していて、「読み取り済み」が1件以上ある
② 品目リスト案が1行以上ある
③ 全行の必須5項目が、値か「要確認」で埋まっている（空欄0）
④ 抽出したすべての値に読み取り元があり、その位置に原文があるかの照合で不一致が0件
⑤ すべての値に確信度が付き、確信が低い値には手がかり（H1〜H4）が1つ以上付いている
⑥ 要確認でない数量は数値として解釈でき、納期は (a)(b)(c) のいずれかに分類されている

## してはいけないこと

- 引合書に書かれていない値を推測で埋めること（記載がなければ「要確認」です）
- 原本を書き換えること
- 確定、除外、Excel の出力
- 他の案件のデータに触れること
- 与えられた6つのツール以外を使おうとすること
- **`read_file_content` で別の入力に移る前に、直前の入力の行を `save_item_rows` で
  保存しないこと**（読むだけ読んで最後にまとめて保存するのは誤りです）
- **2つ以上の入力の `read_file_content` を同じ手番でまとめて呼ぶこと**
  （先に全部読んでから保存する形になり、打ち切られたときに何も残りません）

対象の案件ID: {inquiry_id}
```

---

## 3. ツール定義（6つ）

`agent.md` のツール一覧の写し。**この6つ以外は与えない**（組み込みの Bash / Read / Write / Web も渡さない。ガードレール）。

### 3-1. `list_input_files`

| 項目 | 内容 |
|---|---|
| 目的 | 案件に投入された入力の一覧を知る（メール本文も1件として返す） |
| 入力 | なし（案件IDはサーバー側で注入） |
| 副作用 | read |

```json
{"type":"object","properties":{},"required":[]}
```

返す形:
```json
{"inputs":[{"input_id":"uuid","display_name":"見積依頼.xlsx","format":"excel|pdf|word|mail_body","size_bytes":12345}]}
```

### 3-2. `read_file_content`

| 項目 | 内容 |
|---|---|
| 目的 | 入力の中身を、読み取り元として示せる位置つきで読む |
| 副作用 | read（読み取り専用。原本には書けない） |

```json
{"type":"object","properties":{
  "input_id":{"type":"string"},
  "sheet":{"type":"string","description":"Excel のシート名。省略時は先頭"},
  "page":{"type":"integer","description":"PDF のページ番号。省略時は1"},
  "start":{"type":"integer","description":"読み始める行/段落の番号。省略時は先頭"},
  "limit":{"type":"integer","description":"読む行数。上限あり"}},
 "required":["input_id"]}
```

返す形（**位置を必ず添える**。これが読み取り元の根拠になる）:
```json
{"cells":[{"locator":"明細!C12","text":"BRG-6205-2RS"}],
 "has_more":true,
 "has_readable_text":true,
 "next":{"sheet":"明細","start":23}}
```

位置の書き方は形式ごとに決める。**⑤ の `locator_label` と同じ形式にすること。**

| 形式 | 位置の形 | 例 |
|---|---|---|
| Excel | `シート名!セル番地` | `明細!C12` |
| PDF | `p.ページ/行番号` | `p.2/14` |
| Word | `表N/行/列` または `段落N` | `表1/5/3` |
| メール本文 | `行番号` | `L8` |

**1回に返す量に上限を設ける**（コンテキストを守るため）。上限値は Build で決めてよいが、`has_more` と `next` は必ず返す。

### 3-3. `save_item_rows`

| 項目 | 内容 |
|---|---|
| 目的 | 品目リスト案を下書きとして保存する。保存のたびに形式を検査する |
| 副作用 | write（下書きだけ。**案件の品目リスト案を丸ごと置き換える**） |

```json
{"type":"object","properties":{"rows":{"type":"array","items":{
  "type":"object","properties":{
    "row_no":{"type":"integer"},
    "source_input_id":{"type":"string"},
    "values":{"type":"object","properties":{
      "item_name":{"$ref":"#/$defs/value"},
      "part_no":{"$ref":"#/$defs/value"},
      "quantity":{"$ref":"#/$defs/value"},
      "unit":{"$ref":"#/$defs/value"},
      "due_date":{"$ref":"#/$defs/due"},
      "remarks":{"$ref":"#/$defs/value"}},
      "required":["item_name","part_no","quantity","unit","due_date"]}},
  "required":["row_no","source_input_id","values"]}}},
 "required":["rows"]}
```

`value` の形:
```json
{"raw_text":"2OO", "value":"200", "state":"extracted|needs_confirmation",
 "confidence":"high|low", "clues":["H2"],
 "source":{"input_id":"uuid","locator":"明細!D12"}}
```

`due`（納期）の形:
```json
{"raw_text":"10月末", "kind":"fixed|month_range|needs_confirmation",
 "start_date":"2026-10-21","end_date":"2026-10-31",
 "state":"extracted|needs_confirmation","confidence":"high|low","clues":[],
 "source":{"input_id":"uuid","locator":"明細!F12"}}
```

**保存時にコードが検査して返す誤り**（LLM にやらせない）:

| 検査 | 弾く条件 |
|---|---|
| 必須5項目の空欄 | `state` も値も無い |
| 数値でない数量 | `state != needs_confirmation` なのに `value` が数値に解釈できない |
| 値域の外の納期 | `kind` が3つのいずれでもない、月をまたぐ範囲、開始日 > 終了日 |
| 読み取り元のない値 | `state != needs_confirmation` なのに `source` が無い |
| 案件にないファイルを指す読み取り元 | `input_id` がこの案件の入力に無い |
| 確信が低いのに手がかりが無い | `confidence == low` かつ `clues` が空 |

返す形:
```json
{"saved_rows":13,"errors":[{"row_no":7,"field":"quantity","message":"数量が数値として解釈できません: 2OO"}]}
```

**`inquiry_inputs.status` の「読み取り済み」は、このツールが保存した行の読み取り元から自動で決まる。**
エージェントが明示するのは「明細なし」「判読不能」だけ（`set_file_status`）。

**入力を1つ読み終えるごとに呼ばせること。** 理由は「**打ち切っても、それまでに保存した案と
読めた範囲は破棄しない**」（`agent.md` 強制停止）を成り立たせるため。最後に1回だけ保存する作りだと、
打ち切られた時点で何も保存されておらず、読めたはずの入力まで失われる。
（2026-09-13 訂正: 以前ここに「SCR-04 の進み具合もここで進むので」と書いていたが誤り。
進み具合は `read_file_content` の回数から数えており、保存の回数には依らない。）

### 3-4. `verify_sources`

| 項目 | 内容 |
|---|---|
| 目的 | 保存した値の原文が、読み取り元の位置に本当にあるかを照合する |
| 入力 | なし（保存済みの案をすべて照合） |
| 副作用 | read |

```json
{"type":"object","properties":{},"required":[]}
```

返す形:
```json
{"mismatches":[{"row_no":5,"field":"part_no","raw_text":"BRG-6205-2RS",
  "source":{"input_id":"uuid","locator":"明細!C11"},"actual_text":"BRG-6305-2RS"}]}
```

照合は**原文（`raw_text`）で行う**。正規化後の値では一致しない。

### 3-5. `set_file_status`

| 項目 | 内容 |
|---|---|
| 目的 | 明細のない入力、判読できない入力を記録する |
| 副作用 | write（入力の状態だけ） |

```json
{"type":"object","properties":{
  "input_id":{"type":"string"},
  "status":{"type":"string","enum":["no_items","illegible"]},
  "read_up_to":{"type":"string","description":"どこまで読めたか"}},
 "required":["input_id","status"]}
```

**`illegible`（判読不能）以外の理由を入力単位で付けてはいけない。**
タイムアウトと最大ターン数超過は案件全体の停止理由であって、個々の入力には付かない（`agent.md` 完了条件①）。

### 3-6. `check_completion`

| 項目 | 内容 |
|---|---|
| 目的 | 完了条件①〜⑥と失敗条件を判定し、案件の状態を決める |
| 入力 | なし |
| 副作用 | write（**完了・失敗のときだけ**案件の状態を変える） |

```json
{"type":"object","properties":{},"required":[]}
```

返す形:
```json
{"result":"completed|failed_illegible|failed_no_items|incomplete",
 "unmet":[{"condition":"③","message":"7行目の単位が空欄です"}]}
```

**案件の状態を変えられるのはこのツールだけ**（ガードレール）。変えられる先は「確認待ち」と「読み取り不可」のみ。

---

## 4. `check_completion` の判定ロジック

上から順に評価する。**LLM に判断させず、すべてコードで書く。**

```
# --- 失敗条件（先に見る） ---
if すべての入力の status == illegible:
    → 案件を「読み取り不可（判読不能）」/ stop_reason = failed
       return failed_illegible

if 保存されている品目行が0件 and 読み取れた入力が1件以上:
    → 案件を「読み取り不可（明細なし）」/ stop_reason = failed
       return failed_no_items

# --- 完了条件①〜⑥ ---
unmet = []

① すべての入力の status が read / no_items / illegible のいずれかで確定していて、
   status == read が1件以上ある
② 品目行が1行以上ある
③ 全行の必須5項目それぞれが、値を持つ または state == needs_confirmation
④ state != needs_confirmation の値すべてに source があり、
   verify_sources 相当の照合で不一致が0件
⑤ すべての値に confidence がある。confidence == low の値は clues が1つ以上ある
⑥ state != needs_confirmation の quantity がすべて数値に解釈できる。
   due_date の kind がすべて fixed / month_range / needs_confirmation のいずれか

if unmet:
    return incomplete（unmet を添えて返す。案件の状態は変えない）
else:
    → 案件を「確認待ち」/ stop_reason = completed
       return completed
```

**`incomplete` のときは案件の状態を変えない。** エージェントは不足を直して呼び直す。
直せないまま続けた場合は `MAX_TURNS` かタイムアウトで止まる。

---

## 5. 2層タイムアウトの実装

| 計るもの | 場所 | 値 | 発火時の `stop_reason` |
|---|---|---|---|
| メッセージ間の無応答 | `runner.py` | 60秒 | `inactivity_timeout` |
| 実行全体 | `runner.py` | 300秒 | `inner_timeout` |
| 最後の砦 | `jobs.py` | 360秒 | `outer_timeout` |

```python
# jobs.py（外側）
async def start_agent_job(inquiry_id, attempt_no):
    run_id = create_agent_run(inquiry_id, attempt_no)
    asyncio.create_task(_run_with_outer_timeout(run_id, inquiry_id))
    return run_id     # 完了を待たずに 202 を返す

async def _run_with_outer_timeout(run_id, inquiry_id):
    try:
        await asyncio.wait_for(runner.run(run_id, inquiry_id), OUTER_TIMEOUT_S)
    except asyncio.TimeoutError:
        finish(run_id, "outer_timeout")   # 内側の不具合として調査対象
```

```python
# runner.py（内側・無応答）
async def run(run_id, inquiry_id):
    deadline = time.monotonic() + INNER_TIMEOUT_S
    async for message in client.stream(...):
        if time.monotonic() > deadline:
            return finish(run_id, "inner_timeout")
        # 次のメッセージを INACTIVITY_TIMEOUT_S 以内に受け取れなければ inactivity_timeout
```

**いずれの停止でも、それまでに保存した品目リスト案と読めた範囲は破棄しない**（`agent.md` 停止条件）。
案件は「読み取り不可（タイムアウト）」にし、再実行は1回まで許す。

**`outer_timeout` が発火したら、それは内側の不具合。** ⑥ TEST-18 は「外側が発火しないこと」を確かめる。

> **2026-09-13 追記（⑥ TEST-17 で分かったこと）**
> - **最大ターン数超過は `ResultMessage` ではなく例外 `ResultError` で届く**（claude-agent-sdk 0.2.152）。
>   `subtype == "error_max_turns"` / `terminal_reason == "max_turns"` で判別し、`stop_reason = max_turns`
>   に対応づける。受けそこねると `failed` になり、SCR-10 の再実行の導線が出なくなる
> - 理由の付いていない `failed`（予期しない例外）でも、案件は必ず「読み取り不可」にする。
>   放置すると案件が「読み取り中」のまま残り、一覧と処理状況が永久に読み取り中に見える

---

## 6. トレース `backend/traces/{run_id}.jsonl`

1行1イベントの JSON Lines。**原本の全文と API キーを残さない**（ガードレール）。

```json
{"ts":"2026-09-13T10:00:00Z","run_id":"...","inquiry_id":"...","event":"run_start","attempt_no":1,"model":"claude-sonnet-5"}
{"ts":"...","event":"turn","turn":3}
{"ts":"...","event":"tool_call","tool":"read_file_content","input":{"input_id":"...","sheet":"明細","start":10}}
{"ts":"...","event":"tool_result","tool":"read_file_content","summary":{"file":"見積依頼.xlsx","range":"明細!A10:G22","rows":13,"has_more":false}}
{"ts":"...","event":"run_end","stop_reason":"completed","turns":9,"elapsed_s":84}
```

**`read_file_content` の結果は要約だけ**（ファイル名・範囲・行数）。中身は書かない。
⑥ の3章はこのトレースを5観点（完了条件・ツールの使い方・ガードレール・停止条件・秘密情報）で検査する
（`backend/scripts/audit_traces.py` が全数を数える）。

**`run_end` の無いトレースを残さない。** サーバーが落ちると `runner.py` は `run_end` を書けないので、
起動時の回収（`agent_run_service.close_orphaned_runs()`）が DB と**トレースの両方**を閉じる。

---

## 7. 明日の最短ルート

| 順 | やること | これが終われば |
|---|---|---|
| 1 | `definition.py`・`prompt.py` を置く | 設定とプロンプトが固定される |
| 2 | `list_input_files` と `read_file_content` を作る | D1 の Excel と PDF が位置つきで読める |
| 3 | `save_item_rows` を検査つきで作る | 品目リスト案が DB に入る |
| 4 | `check_completion` を作る | **エージェントが「終わった」と言えるようになる** |
| 5 | `runner.py` でループを回す・トレースを出す | **D1 で `stop_reason=completed`。ここでお題Aの核が成立** |
| 6 | `verify_sources`・`set_file_status` | 完了条件④と失敗条件が揃う |
| 7 | 画面4つ（投入・処理状況・確認・完了）＋ Excel 出力 | 人が確認して確定できる |

**5 が通った時点で、発表で見せるものは揃う。** 6・7 は時間と相談。

テストデータは `backend/tests/fixtures/d1/`（`normal_excel.xlsx` ＋ `normal_spec.pdf`）を使う。
仕込んである論点は `backend/tests/fixtures/README.md` に書いてある。
