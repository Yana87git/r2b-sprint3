# API・IPO一覧（詳細設計）: 引合書整理エージェント

> Vモデル: 詳細設計 / 対応する検証: 単体テスト
> 先にAPIの全体像（一覧・認証）を示し、その上で業務フローごとのデータの流れ（Input/Process/Output）がどのAPIで実現されるかを整理する。

> 認証・認可の方針（認証方式・トークン有効期限・権限モデル）は ② 非機能要件（セキュリティ）で定義する。
> ここでは各APIが「認証を要するか・どの権限が必要か」を詳細設計として整理する。
> Scope 1 のロールは**営業事務**のみ。営業担当ロール（FUNC-08）は Scope 2 で追加する。

## 1. API一覧

すべて `/api/v1` 配下。認証は JWT（アクセストークン 60分）。

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 1 | `/auth/login` | POST | ログイン（FUNC-12） | 不要 | — |
| 2 | `/auth/logout` | POST | ログアウト（FUNC-12） | 要 | 営業事務 |
| 3 | `/users/me` | GET | ログイン中の利用者を返す（FUNC-12） | 要 | 営業事務 |
| 4 | `/inquiries` | POST | 引合の投入。入力の形式判定と受付、**エージェントの自動起動**（FUNC-01 / FUNC-02） | 要 | 営業事務 |
| 5 | `/inquiries` | GET | 引合一覧。状況で絞り込み。**ページネーションは設けず、`submitted_at DESC` で全件返す**（保持期間90日で150〜200件）（FUNC-03） | 要 | 営業事務 |
| 6 | `/inquiries/{inquiry_id}` | GET | 案件の状況と入力の一覧（FUNC-03 / FUNC-07） | 要 | 営業事務 |
| 7 | `/inquiries/{inquiry_id}/runs` | POST | **エージェントの再実行**（FUNC-07）。自動起動に失敗した案件の起動にも使う | 要 | 営業事務 |
| 8 | `/runs/{run_id}` | GET | 実行の進み具合と停止理由（FUNC-03） | 要 | 営業事務 |
| 9 | `/inquiries/{inquiry_id}/items` | GET | 品目リスト案。要確認だけの絞り込みもできる（FUNC-04 / FUNC-05） | 要 | 営業事務 |
| 10 | `/inquiries/{inquiry_id}/items/{row_id}` | PATCH | 行の値の修正（FUNC-05） | 要 | 営業事務 |
| 11 | `/inquiries/{inquiry_id}/items/{row_id}/check` | POST | 行を確認済みにする（FUNC-04） | 要 | 営業事務 |
| 12 | `/inquiries/{inquiry_id}/items/bulk-check` | POST | 確信が高い行をまとめて確認済みにする（FUNC-04） | 要 | 営業事務 |
| 13 | `/inquiries/{inquiry_id}/items/{row_id}/exclusion` | POST / DELETE | 行の除外と取り消し（FUNC-05） | 要 | 営業事務 |
| 14 | `/inquiries/{inquiry_id}/values/{value_id}/source` | GET | 読み取り元と原本の抜粋。抜き取りの記録も兼ねる（FUNC-04） | 要 | 営業事務 |
| 15 | `/inquiries/{inquiry_id}/inputs/{input_id}/exclusion` | POST / DELETE | 読み取れなかった入力の除外と取り消し（FUNC-07） | 要 | 営業事務 |
| 16 | `/inquiries/{inquiry_id}/inputs/{input_id}/original` | GET | 原本のダウンロード（FUNC-07） | 要 | 営業事務 |
| 17 | `/inquiries/{inquiry_id}/confirm` | POST | 確定と品目リスト（Excel）の出力（FUNC-06） | 要 | 営業事務 |
| 18 | `/inquiries/{inquiry_id}/export` | GET | 出力済み Excel のダウンロード（FUNC-06） | 要 | 営業事務 |
| 19 | `/inquiries/{inquiry_id}/inquiry-message` | GET | 顧客への問い合わせ文面【Scope 3・FUNC-09】 | 要 | 営業事務 |

### エージェントのツールとAPIの関係

**エージェントのツールは HTTP API を呼ばない。** ツールは backend 内部で service / repository を経由して DB に触る（Slice 0-7 のルール「ツールに生 SQL・生 HTTP を書かない」）。画面用の API と同じ処理を共有するものは、下表のとおり。

| ツール（`agent.md`） | 呼ぶ内部サービス | 画面用APIで同じ処理を使うもの |
|---------------------|----------------|--------------------------|
| `list_input_files` | `InquiryService.list_inputs` | #6 `GET /inquiries/{id}` |
| `read_file_content` | `InputReaderService.read`（openpyxl / python-docx / PDF） | #14 `GET .../source`（抜粋の取り出しに同じ読み取りを使う） |
| `save_item_rows` | `ItemDraftService.replace_rows` | #9 `GET .../items`（同じデータを読む） |
| `verify_sources` | `SourceVerifyService.verify_all` | #14 `GET .../source` |
| `set_file_status` | `InquiryService.set_input_status` | #6 `GET /inquiries/{id}`（結果の表示） |
| `check_completion` | `CompletionService.check` | #8 `GET /runs/{run_id}`（判定結果が停止理由に出る） |

**エージェントを使うための入口**は #7（起動・再実行）・#8（進み具合）・#9／#6（結果）の3種類。実行の型は「POST → 202 + run_id → GET でポーリング」（`agent.md` ／ Slice 0-7）。

## 2. フローごとのIPO

> フローは「ユースケース（ユーザーが1つの目的を達成する単位）」で切る。開始トリガーから結果が出るまでを1フローとし、画面・APIを複数跨いでよい。

### FLOW-01 ログインする

**対応機能(②)**: FUNC-12

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | ユーザーIDとパスワード（SCR-01） | ハッシュを照合し、アクセストークンを発行する | トークンと利用者情報 | #1 | `users` |
| 2 | トークン | 引合一覧を開く | 案件の一覧（SCR-02） | #5 | `inquiries` |

### FLOW-02 引合書を投入して読み取りを始める

**対応機能(②)**: FUNC-01 / FUNC-02 / FUNC-03

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | ファイル（0〜10件）とメール本文（任意）（SCR-03） | 拡張子・サイズ・件数・合計サイズを検査し、形式を判定する。原本を保管し、入力を登録し、**そのままエージェントをバックグラウンドで起動する**（`jobs.start_agent_job`） | 案件ID・入力ごとの判定結果・run_id | #4 | `inquiries`・`inquiry_inputs`・`agent_runs` |
| 2 | run_id | 一定間隔で進み具合を取る。読み終えた入力の数と残り時間の目安を返す | 段階・残り時間（SCR-04） | #8 | `agent_runs`・`inquiry_inputs` |
| 3 | （エージェント内部） | 入力を1つ読み終えるごとに品目リスト案を保存し、最後に完了条件を判定する | 進み具合が進み、案件が「確認待ち」または「読み取り不可」になる | —（ツール） | `item_rows`・`item_values`・`value_clues`・`inquiry_inputs`・`inquiries` |

### FLOW-03 品目リスト案を確認する

**対応機能(②)**: FUNC-04

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 案件ID | 品目リスト案を、要確認・確信が低い行を先にして返す。入力ごとの状態も返す。**案件が「確認待ち」で `review_started_at` が NULL なら、そのときの時刻を記録する**（KPI1 の起点）。3階層（行・値・手がかり）は1回のクエリでまとめて取る | 行・値・読み取り元・手がかり（SCR-05） | #9・#6 | `item_rows`・`item_values`・`value_clues`・`inquiry_inputs`・`inquiries` |
| 2 | 値ID | 読み取り元の位置と原本の抜粋を返す。**確信が高い行なら抜き取りとして記録する** | 抜粋と位置（SCR-06） | #14 | `item_values`・`inquiry_inputs` |
| 3 | 行ID | その行を確認済みにする | 未確認の数が減る | #11 | `item_rows` |
| 4 | 案件ID | 抜き取りが min(3, N) 行に達しているかを検査し、達していれば確信が高い行をまとめて確認済みにする（N の数え方は ④ を参照） | 未確認の数（不足なら 409） | #12 | `item_rows` |

### FLOW-04 値を直す・行を除外する・要確認をまとめる

**対応機能(②)**: FUNC-05 / FUNC-09（Scope 3）

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 行ID・直した値（SCR-07） | 数量は数値、納期は (a)(b)(c)、必須5項目は値か要確認、を検査して保存する。**保存 → 行の分類を計算し直す → その行を確認済みにする**の順で行う | 更新後の行と分類 | #10 | `item_rows`・`item_values`・`value_clues` |
| 2 | 行ID | 重複や明細でない行を除外する。未確認から外し、出力の対象からも外す | 除外した行（取り消せる） | #13 | `item_rows` |
| 3 | 案件ID・`filter=needs_confirmation` | 要確認の項目だけを返す | 要確認の一覧（SCR-08） | #9 | `item_values`・`item_rows` |
| 4 | 案件ID【Scope 3】 | 要確認の項目から問い合わせ文面を組み立てる（送信はしない） | 文面のテキスト | #19 | `item_values`・`inquiries` |

### FLOW-05 確定して品目リストを受け取る

**対応機能(②)**: FUNC-06

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 案件ID | 読み取れなかった入力が0件か、未確認が0かを検査する（**読み取れなかった入力を先に見る**）。満たさなければ 409 と理由を返す | 確定の可否 | #17 | `item_rows`・`inquiry_inputs` |
| 2 | 案件ID | 除外した行を除いて Excel を生成し、要確認の行に「顧客回答待ち」を付ける。保管して案件を確定済みにする | 出力の記録（SCR-09） | #17 | `item_list_exports`・`inquiries` |
| 3 | 案件ID | 保管済みの Excel を返す（何度でも） | Excel ファイル | #18 | `item_list_exports` |

### FLOW-06 読み取り不可を扱う

**対応機能(②)**: FUNC-07

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | 案件ID | 理由（判読不能／明細なし／タイムアウト／最大ターン数超過）と読めた範囲を返す | SCR-10 の表示 | #6 | `inquiries`・`inquiry_inputs`・`agent_runs` |
| 2 | 案件ID（理由がタイムアウト／最大ターン数超過のとき） | 再実行の回数を検査（`attempt_no` は既存の実行回数 + 1、上限2）し、エージェントを再起動する | 202 と新しい run_id | #7 | `agent_runs` |
| 3 | 入力ID | 原本（ファイル、またはメール本文のテキスト）を返す | ダウンロード | #16 | `inquiry_inputs` |
| 4 | 入力ID（一部の入力だけ読めなかったとき） | その入力を「除外（手作業で補う）」にする。読み取れなかった入力が0件になれば確定に進める | 除外した入力（取り消せる） | #15 | `inquiry_inputs` |

## 3. エンドポイント詳細

> 正確な型・JSON構造・バリデーションは oval スキーマを SSOT とする。ここでは契約の意味（フィールドの意味・エラーの意味論）を定義し、型はスキーマを参照する。
> 共通のエラー: 401 `UNAUTHORIZED`（トークンなし・期限切れ）、403 `FORBIDDEN`（権限なし）、404 `NOT_FOUND`（他の利用者の案件を含む）、500 `INTERNAL_ERROR`。以降の表では、そのAPI固有のものだけを書く。

> **GET で状態を変えるのは #9（`review_started_at`）と #14（`source_opened_at`）の2本だけ。** どちらも1回目だけ記録し、2回目以降は何も変えない。確認作業を始めた時刻と読み取り元を開いた事実は、画面の操作ではなくサーバー側で数える必要があるため（② KPI1・FUNC-04）。

### ログイン

- **Method**: POST ／ **Path**: `/api/v1/auth/login` ／ **目的**: 認証してアクセストークンを得る
- **認証**: 不要 ／ **必要権限**: — ／ **対応テーブル(④)**: `users` ／ **対応フロー**: FLOW-01
- **スキーマ（型のSSOT）**: `schemas/auth_login`（oval）

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| login_id | Yes | ユーザーID |
| password | Yes | パスワード（平文で送り、サーバーでハッシュと照合する） |

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| access_token | アクセストークン（有効期限60分） |
| user | ログインした利用者（表示名・ロール） |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 401 | ユーザーIDかパスワードが違う、または無効化された利用者。**どちらが違うか・利用者が存在するかは返さない**（SCR-01） | `AUTH_FAILED` |

無効化された利用者にだけ別のコード（403）を返すと、**そのユーザーIDが存在することが外から分かる**ため、401 `AUTH_FAILED` に寄せる。

### 引合の投入

- **Method**: POST ／ **Path**: `/api/v1/inquiries` ／ **目的**: 入力を受け付け、案件を作り、**そのままエージェントを起動する**
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `inquiries`・`inquiry_inputs`・`agent_runs` ／ **対応フロー**: FLOW-02
- **スキーマ（型のSSOT）**: `schemas/inquiry_create`（oval）

#### リクエスト（multipart/form-data）

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| files | No | 投入するファイル（.xlsx / .pdf / .docx）。0〜10件 |
| mail_body | No | メール本文のテキスト |

files と mail_body の**少なくとも一方**が必要。合計は入力10件・50MB まで、1ファイル 20MB まで（② FUNC-01・非機能）。

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| inquiry_id | 作った案件のID |
| inputs | 入力ごとの判定結果（表示名・形式・「Excel形式として受け付けました」に相当する内容） |
| run_id | 自動で始めたエージェント実行のID（`attempt_no` = 1）。画面はこの ID で進み具合を取る |

受付が済んだら、**サーバー側が `jobs.start_agent_job()` でエージェントを起動する**（クライアントの操作を待たない）。ブラウザを閉じても読み取りは進み、投入したまま誰も起動しない案件が残らない。

**入力の登録・原本の保管・エージェントの起動は1つの処理として扱い、起動に失敗したら登録と保管も巻き戻す。** これにより「受付済みのまま実行記録が0件」という詰まった状態が発生しない。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 対応しない拡張子（.xls を含む） | `UNSUPPORTED_FORMAT` |
| 400 | 1ファイルが 20MB を超える | `FILE_TOO_LARGE` |
| 400 | 入力が11件以上 | `TOO_MANY_INPUTS` |
| 400 | 合計が 50MB を超える | `TOTAL_SIZE_EXCEEDED` |
| 400 | ファイルも本文もない | `NO_INPUT` |
| 500 | エージェントを起動できなかった。**案件は作られない**ので、投入からやり直せる | `INTERNAL_ERROR` |

### エージェントの再実行

- **Method**: POST ／ **Path**: `/api/v1/inquiries/{inquiry_id}/runs` ／ **目的**: (1) SCR-10 の再実行 (2) 自動起動が失敗して実行記録が1件もない案件の起動
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `agent_runs`・`inquiries` ／ **対応フロー**: FLOW-02・FLOW-06
- **スキーマ（型のSSOT）**: `schemas/agent_run_start`（oval）

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| inquiry_id | Yes | 対象の案件（パス） |

#### レスポンス（成功・202）

| フィールド | 意味 |
|-----------|------|
| run_id | 実行ID。トレース `backend/traces/{run_id}.jsonl` と同じ |
| attempt_no | **既存の実行回数 + 1（上限2）**。自動起動が済んでいれば 2（再実行）、実行記録が1件もなければ 1 |

**完了を待たずに 202 を返す**（Slice 0-7 のルール）。進み具合は `GET /runs/{run_id}` で取る。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | すでに実行中 | `RUN_IN_PROGRESS` |
| 409 | 再実行できない | `RETRY_NOT_ALLOWED`（レスポンスに理由を添える: `illegible` / `no_items` / `already_retried`。SCR-10 はこの理由で文面を出し分ける） |
| 409 | 確定済みの案件 | `ALREADY_CONFIRMED` |

### 実行の進み具合

- **Method**: GET ／ **Path**: `/api/v1/runs/{run_id}` ／ **目的**: 段階・残り時間・停止理由を返す（ポーリング）
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `agent_runs`・`inquiry_inputs`・`inquiries` ／ **対応フロー**: FLOW-02
- **スキーマ（型のSSOT）**: `schemas/agent_run_status`（oval）

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| status | 案件の段階（受付済み／読み取り中／読み取り不可／確認待ち／確定済み） |
| inputs_done / inputs_total | 読み終えた入力の数と全体の数。残り時間の目安の根拠 |
| eta_seconds | 残り時間の目安。目安を過ぎたら 0 を返し、画面は「目安の時間を過ぎています」に切り替える（SCR-04） |
| stop_reason | 終わっている場合の停止理由（`completed` / `failed` / `max_turns` / `inner_timeout` / `inactivity_timeout` / `outer_timeout`） |
| unreadable_reason | 読み取り不可の理由（判読不能／明細なし／タイムアウト／最大ターン数超過） |

### 品目リスト案の取得

- **Method**: GET ／ **Path**: `/api/v1/inquiries/{inquiry_id}/items` ／ **目的**: 行・値・読み取り元・手がかりを返す
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `item_rows`・`item_values`・`value_clues`・`inquiries` ／ **対応フロー**: FLOW-03・FLOW-04
- **スキーマ（型のSSOT）**: `schemas/item_list`（oval）

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| filter | No | `needs_confirmation` を指定すると要確認の項目だけ返す（SCR-08）。**このときは除外した行を返さない**（除外した行は出力されないので、顧客への問い合わせ対象にしない） |
| include_excluded | No | 除外した行も返すか（既定は返す。SCR-05 は最後にまとめて表示するため）。`filter=needs_confirmation` のときは、この指定にかかわらず返さない |

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| rows | 行の一覧。要確認・確信が低い行が先。行ごとに分類・確認状態・除外の有無 |
| rows[].values | 値。原文・正規化後の値・状態・確信度・読み取り元（入力IDと位置）・手がかり（H1〜H4） |
| summary | 未確認の数・全行数・除外した行数・分類ごとの件数・抜き取りの数（画面の集計表示用に、その場で数えた値） |

- **KPI1 の起点**: 案件が「確認待ち」で `inquiries.review_started_at` が NULL のときだけ、そのときの時刻を記録する。2回目以降と、確定済みの案件を見返すときは何も変えない
- **N+1 を避ける**: `item_rows` / `item_values` / `value_clues` は1回のクエリでまとめて取る（1案件は最大30行 × 6項目 = 180値）

### 読み取り元の取得（抜き取りの記録を兼ねる）

- **Method**: GET ／ **Path**: `/api/v1/inquiries/{inquiry_id}/values/{value_id}/source` ／ **目的**: 読み取り元の位置と原本の抜粋を返す
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `item_values`・`inquiry_inputs`・`item_rows` ／ **対応フロー**: FLOW-03
- **スキーマ（型のSSOT）**: `schemas/value_source`（oval）

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| locator_label | 画面に出す読み取り元（例 `見積依頼.xlsx 明細!C12`） |
| excerpt | 原本の抜粋（形式ごとの構造。Excel は周辺セル、PDF はページ内の前後、Word は表または段落、メール本文は前後の行） |
| sampled_rows / required_samples | 抜き取りとして数えた行の数と、一括確認に必要な数（min(3, N)） |

**この API を呼ぶと、抜き取りが記録される。** 対象の値が属する行の分類が「確信が高い」で、かつ `item_rows.source_opened_at` が NULL のときだけ、そのときの時刻を書く。2回目以降は何も変えない。一括確認の可否をサーバー側で判定するため（② FUNC-04）。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | 要確認の値には読み取り元がない（SCR-05 はそもそもパネルを開かない） | `NO_SOURCE_FOR_VALUE` |
| 422 | 原本の該当箇所を取り出せない（位置は返す） | `EXCERPT_UNAVAILABLE` |

### 一括確認

- **Method**: POST ／ **Path**: `/api/v1/inquiries/{inquiry_id}/items/bulk-check` ／ **目的**: 確信が高い行をまとめて確認済みにする
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `item_rows` ／ **対応フロー**: FLOW-03
- **スキーマ（型のSSOT）**: `schemas/items_bulk_check`（oval）

**判定の数え方**（④ と同じ）: N = 確信が高く、除外していない行の数（**確認済みかどうかは問わない**）。抜き取り数 = そのうち `source_opened_at` が NOT NULL の行の数。抜き取り数 ≧ min(3, N) で許可する。確認済みを N から除くと、1行ずつ確認するたびに分母が動いて判定が不安定になるため。

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | 抜き取りが min(3, N) 行に足りない。**サーバー側で拒否する**（画面のボタンを押せなくするだけにしない。② FUNC-04） | `SAMPLING_NOT_ENOUGH` |

### 行の修正

- **Method**: PATCH ／ **Path**: `/api/v1/inquiries/{inquiry_id}/items/{row_id}` ／ **目的**: 値を直し、その行を確認済みにする
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `item_rows`・`item_values` ／ **対応フロー**: FLOW-04
- **スキーマ（型のSSOT）**: `schemas/item_row_update`（oval）

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| values | Yes | 直す項目と値。必須5項目は値か「要確認」のどちらか。納期は種別 (a)(b)(c) と日付 |

**処理の順序**: 保存 → **行の分類を計算し直す** → その行を確認済みにする。

- 行の分類は値の状態から決まる。要確認の値が1つでもあれば「要確認」、なければ確信が低い値が1つでもあれば「確信が低い」、どちらもなければ「確信が高い」（呼び方と識別子の対応は ④ の表を正とする）
- **人が直した値は確信度を「高い」にし、手がかり（H1〜H4）を消す。** 人が入れた値は読み違いではないため

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | 数量が数値でない | `QUANTITY_NOT_NUMERIC` |
| 400 | 納期が (a)(b)(c) のいずれでもない | `DUE_DATE_OUT_OF_DOMAIN` |
| 400 | 月内の範囲が不正（月をまたぐ、開始日が終了日より後） | `DUE_RANGE_INVALID` |
| 400 | 必須5項目を空欄にした | `REQUIRED_FIELD_EMPTY` |
| 409 | 確定済みの案件は直せない | `ALREADY_CONFIRMED` |

### 確定

- **Method**: POST ／ **Path**: `/api/v1/inquiries/{inquiry_id}/confirm` ／ **目的**: 確定して Excel を出力する
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `inquiries`・`item_rows`・`inquiry_inputs`・`item_list_exports` ／ **対応フロー**: FLOW-05
- **スキーマ（型のSSOT）**: `schemas/inquiry_confirm`（oval）

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| confirmed_at | 確定日時 |
| row_count / pending_row_count | 出力した行数と、「顧客回答待ち」として出力した行数 |
| download_path | Excel を取る先（#18） |

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | 読み取れなかった入力が残っている（除外すれば確定できる） | `UNREADABLE_INPUT_REMAINS` |
| 409 | 未確認の行が残っている（件数を添えて返す） | `UNCHECKED_ROWS_REMAIN` |
| 409 | すでに確定済み | `ALREADY_CONFIRMED` |

**両方が残っているときは `UNREADABLE_INPUT_REMAINS` を先に返す。** 読み取れなかった入力には「除外」だけでなく「再実行」という選択肢があり（SCR-10）、再実行すると行が増えて未確認が復活するため、先に片付ける必要がある。

### 入力の除外

- **Method**: POST / DELETE ／ **Path**: `/api/v1/inquiries/{inquiry_id}/inputs/{input_id}/exclusion` ／ **目的**: 読み取れなかった入力を「手作業で補う」として除外する・取り消す
- **認証**: 要 ／ **必要権限**: 営業事務 ／ **対応テーブル(④)**: `inquiry_inputs` ／ **対応フロー**: FLOW-06
- **スキーマ（型のSSOT）**: `schemas/input_exclusion`（oval）

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 409 | 読み取れている入力は除外できない（除外は読み取り不可の入力に対する判断） | `INPUT_NOT_EXCLUDABLE` |
| 409 | 確定済みの案件 | `ALREADY_CONFIRMED` |

---

## 次のステップ

→ `/design-implementation-check` で実装設計フェーズ（04・05・`agent.md` Part 2）のレビューを行う
→ その後 `06-scenario-test` でシナリオテストを作成する
