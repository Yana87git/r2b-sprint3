# API・IPO一覧（詳細設計）: {project_name}

> Vモデル: 詳細設計 / 対応する検証: 単体テスト
> 先にAPIの全体像（一覧・認証）を示し、その上で業務フローごとのデータの流れ（Input/Process/Output）がどのAPIで実現されるかを整理する。

> 認証・認可の方針（認証方式・トークン有効期限・権限モデル）は ② 非機能要件（セキュリティ）で定義する。
> ここでは各APIが「認証を要するか・どの権限が必要か」を詳細設計として整理する。

## 1. API一覧

| # | エンドポイント | メソッド | 機能 | 認証 | 必要権限 |
|---|--------------|---------|------|------|---------|
| 1 | {endpoint_1} | {method_1} | {function_1} | 要/不要 | {role_1} |
| 2 | {endpoint_2} | {method_2} | {function_2} | 要/不要 | {role_2} |
| 3 | {endpoint_3} | {method_3} | {function_3} | 要/不要 | {role_3} |

> フローは「ユースケース（ユーザーが1つの目的を達成する単位）」で切る。開始トリガーから結果が出るまでを1フローとし、画面・APIを複数跨いでよい。粒度は ② 機能のまとまりとほぼ対応する。

### FLOW-01 {flow_name}

**対応機能(②)**: {functions}

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | {input_1} | {process_1} | {output_1} | {api_1} | {table_1} |
| 2 | {input_2} | {process_2} | {output_2} | {api_2} | {table_2} |

### FLOW-02 {flow_name}

**対応機能(②)**: {functions}

| ステップ | Input | Process | Output | 対応API | 対応テーブル(④) |
|---------|-------|---------|--------|---------|----------------|
| 1 | {input_1} | {process_1} | {output_1} | {api_1} | {table_1} |

## 3. エンドポイント詳細

> 正確な型・JSON構造・バリデーションは oval スキーマを SSOT とする。ここでは契約の意味（フィールドの意味・エラーの意味論）を定義し、型はスキーマを参照する。

### {endpoint_name_1}

- **Method**: {method}
- **Path**: {path}
- **目的**: {purpose}
- **認証**: 要/不要
- **必要権限**: {role}
- **対応テーブル(④)**: {table}
- **対応フロー**: {flow}
- **スキーマ（型のSSOT）**: `schemas/{schema_name}`（oval）

#### リクエスト

| パラメータ | 必須 | 意味 |
|-----------|------|------|
| {param_1} | Yes/No | {description_1} |
| {param_2} | Yes/No | {description_2} |

（型・構造・バリデーションは上記 oval スキーマを参照）

#### レスポンス（成功）

| フィールド | 意味 |
|-----------|------|
| {field_1} | {field_description_1} |
| {field_2} | {field_description_2} |

（型・構造は oval スキーマを参照）

#### レスポンス（エラー）

| ステータス | 意味 | エラーコード |
|-----------|------|------------|
| 400 | {error_description_1} | {error_code_1} |
| 401 | {error_description_2} | {error_code_2} |
| 500 | {error_description_3} | {error_code_3} |

---

## 次のステップ

→ 設計フェーズ完了。Build フェーズに進む。
