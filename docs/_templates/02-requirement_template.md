# 要件定義書: {project_name}

> Vモデル: 要件定義 / 対応する検証: システムテスト  
> 要求定義（①）を「何を作るか」に翻訳する。各機能の要件・スコープ・非機能要件を定義する。

## 1. 機能一覧


| #   | 機能ID    | 機能名          | 概要              | 対応する要求(①)   |
| --- | ------- | ------------ | --------------- | ----------- |
| 1   | FUNC-01 | {function_1} | {description_1} | {request_1} |
| 2   | FUNC-02 | {function_2} | {description_2} | {request_2} |
| 3   | FUNC-03 | {function_3} | {description_3} | {request_3} |


## 2. 各機能の要件

### FUNC-01 {function_1}

- **概要**: {overview}
- **事前条件**: {precondition}
- **正常フロー**: {main_flow}
- **例外・バリデーション**: {validation}
- **受入基準**: {acceptance_criteria}

### FUNC-02 {function_2}

- **概要**: {overview}
- **事前条件**: {precondition}
- **正常フロー**: {main_flow}
- **例外・バリデーション**: {validation}
- **受入基準**: {acceptance_criteria}

## 3. スコープ

各機能を優先度で 4 区分に振り分ける。


| 区分                  | 意味                     |
| ------------------- | ---------------------- |
| **Scope 1（初版）**     | まず必ず作る。MVPとして成立させる最小機能 |
| **Scope 2（改善）**     | 初版の次に着手する改善・拡張機能       |
| **Scope 3（余裕があれば）** | 時間・リソースに余裕があれば実装する機能   |
| **Out of Scope**    | 今回は明確に実装しないと決めたもの      |


### Scope 1（初版）


| 機能ID    | 機能名          | 備考       |
| ------- | ------------ | -------- |
| FUNC-01 | {function_1} | {note_1} |


### Scope 2（改善）


| 機能ID    | 機能名          | 備考       |
| ------- | ------------ | -------- |
| FUNC-02 | {function_2} | {note_2} |


### Scope 3（余裕があれば）


| 機能ID    | 機能名          | 備考       |
| ------- | ------------ | -------- |
| FUNC-03 | {function_3} | {note_3} |


### Out of Scope（今回は実装しない）


| 項目               | 実装しない理由    |
| ---------------- | ---------- |
| {out_of_scope_1} | {reason_1} |
| {out_of_scope_2} | {reason_2} |


## 4. 非機能要件


| カテゴリ    | 要件                |
| ------- | ----------------- |
| 性能      | {performance}     |
| セキュリティ（認証・認可方針） | 認証方式: {auth_method} / トークン有効期限: {token_expiration} / 権限モデル: {role_model} |
| 可用性     | {availability}    |
| ユーザビリティ | {usability}       |
| 保守性     | {maintainability} |


---

## 次のステップ

→ `03-spec`（仕様書・基本設計）で画面構成・画面ごとの機能・モックHTMLを作成する