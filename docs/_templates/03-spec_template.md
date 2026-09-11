# 仕様書（基本設計）: {project_name}

> Vモデル: 基本設計 / 対応する検証: 結合テスト
> 要件（②）を画面に落とし込む。画面構成・画面ごとの機能・モックHTMLを定義する。
> モックは全画面を1つにまとめた [mocks/mockup.html](./mocks/mockup.html) に作成する（画面ID `#SCR-xx` で各画面へアンカー移動）。

## 1. 画面構成（サイトマップ）

| 画面ID | 画面名 | 目的 | 対応機能(②) | モック |
|--------|-------|------|-------------|-------|
| SCR-01 | {screen_1} | {purpose_1} | {functions_1} | [mockup.html#SCR-01](./mocks/mockup.html#SCR-01) |
| SCR-02 | {screen_2} | {purpose_2} | {functions_2} | [mockup.html#SCR-02](./mocks/mockup.html#SCR-02) |
| SCR-03 | {screen_3} | {purpose_3} | {functions_3} | [mockup.html#SCR-03](./mocks/mockup.html#SCR-03) |

### 画面遷移図

```mermaid
flowchart LR
    SCR-01[{screen_1}] --> SCR-02[{screen_2}]
    SCR-02 --> SCR-03[{screen_3}]
```

## 2. 画面ごとの仕様

### SCR-01 {screen_1}

**目的**: {purpose}

**UI要素**

| 要素 | 説明 | 位置 | 対応機能(②) |
|------|------|------|-------------|
| {element_1} | {description_1} | {position_1} | {function_1} |
| {element_2} | {description_2} | {position_2} | {function_2} |

**操作とインタラクション**

| 操作 | UI要素 | 挙動 | 対応機能(②) |
|------|--------|------|-------------|
| {action_1} | {ui_element_1} | {behavior_1} | {function_1} |
| {action_2} | {ui_element_2} | {behavior_2} | {function_2} |

**エラー・例外表示**

> 業務ルール（②の例外・バリデーション）を、この画面でどう見せる・どう振る舞うかを定義する。

| ケース | トリガー | 画面の挙動・表示 | 対応する要件(②) |
|--------|---------|----------------|----------------|
| {error_case_1} | {trigger_1} | {ui_behavior_1} | {function_1} |
| {error_case_2} | {trigger_2} | {ui_behavior_2} | {function_2} |

**モック**: [mockup.html#SCR-01](./mocks/mockup.html#SCR-01)

### SCR-02 {screen_2}

**目的**: {purpose}

**UI要素**

| 要素 | 説明 | 位置 | 対応機能(②) |
|------|------|------|-------------|
| {element_1} | {description_1} | {position_1} | {function_1} |

**操作とインタラクション**

| 操作 | UI要素 | 挙動 | 対応機能(②) |
|------|--------|------|-------------|
| {action_1} | {ui_element_1} | {behavior_1} | {function_1} |

**エラー・例外表示**

| ケース | トリガー | 画面の挙動・表示 | 対応する要件(②) |
|--------|---------|----------------|----------------|
| {error_case_1} | {trigger_1} | {ui_behavior_1} | {function_1} |

**モック**: [mockup.html#SCR-02](./mocks/mockup.html#SCR-02)

## 3. デザイントークン

> ⚠️ ここで決めたデザインが Build 以降のUIの基準として固定される（モック修正時もこの表と mockup.html の `:root` を同期させる）。
> 値の真実源はこの表。Build の `frontend/src/shared/theme/tokens.ts` はここから転記する。

**デザインの方向性**: {direction_summary}（例: 落ち着いた紺基調・角丸なし・見出しはコンデンス系で引き締める）

**シグネチャ要素**: {signature_element}（このプロダクトが記憶される固有の要素を1つ）

### 色（色相は main と error の2つだけ。他はすべて濃淡）

| トークン | 値 | 用途 |
|---------|-----|------|
| main-100 | {hex} | 淡い背景・ホバー |
| main-300 | {hex} | 枠線・補助 |
| main-500 | {hex} | 主要アクション・強調 |
| main-700 | {hex} | アクションのホバー・アクティブ |
| main-900 | {hex} | 濃い強調 |
| background | {hex} | ページ背景（純白禁止・main の色相に寄せた off-white） |
| surface | {hex} | カード・パネル背景 |
| text-primary | {hex} | 見出し・本文（純黒禁止） |
| text-secondary | {hex} | 補足テキスト |
| text-meta | {hex} | メタ情報・ラベル |
| error | {hex} | エラー・警告（この1色のみ。success/info は main の濃淡で表現） |

### タイポグラフィ（サイズ5種・ウェイト3種・フォント族2つまで）

| トークン | 値 | 用途 |
|---------|-----|------|
| font-heading | {font_stack}（日本語フォールバック必須） | 見出し |
| font-body | {font_stack}（日本語フォールバック必須） | 本文 |
| size-xl / lg / md / sm / xs | {px} / {px} / {px} / {px} / {px} | タイプスケール（5種まで） |
| weight | {例: 400 / 600 / 800} | ウェイト（3種まで） |

### 形状（全画面で各1種類）

| トークン | 値 | 用途 |
|---------|-----|------|
| radius | {px} | 角丸（全画面共通） |
| shadow | {値 or なし} | 影（1段階まで。枠線を基本とする） |
| border | {例: 1px solid main-300} | 罫線 |

## 4. モックHTML

全画面を1つにまとめた `mocks/mockup.html` を単一ファイル完結（外部CSS/JS依存なし）で作成する。

- 各画面は `<section id="SCR-01">` … のように画面IDをアンカーに持ち、本文の各画面仕様からリンクする
- 画面上部などにナビゲーション（画面一覧へのリンク）を置き、全画面を行き来できること
- 3章のデザイントークンを `:root` の CSS 変数として埋め込み、全画面に適用すること（外部フォントの読み込みは不可。フォントスタック指定のみ）
- ブラウザで開いてレイアウト・操作感・画面遷移を確認できること
- 実データは不要（ダミーデータで可）

---

## 次のステップ

→ `04-db`（DB設計書・詳細設計）でテーブル設計とCREATE文を作成する
