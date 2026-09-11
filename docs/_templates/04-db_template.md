# DB設計書（詳細設計）: {project_name}

> Vモデル: 詳細設計 / 対応する検証: 単体テスト
> 機能（②）・画面（③）に必要なデータを、動くSQLのテーブル設計に落とし込む。

## 1. テーブル一覧

| テーブル名 | 目的 | 関連機能(②) |
|-----------|------|-------------|
| {table_1} | {purpose_1} | {functions_1} |
| {table_2} | {purpose_2} | {functions_2} |
| {table_3} | {purpose_3} | {functions_3} |

## 2. ER図

```mermaid
erDiagram
    {TABLE_1} ||--o{ {TABLE_2} : "relationship"
    {TABLE_2} ||--|{ {TABLE_3} : "relationship"

    {TABLE_1} {
        int id PK
        string {column_1}
        datetime created_at
    }

    {TABLE_2} {
        int id PK
        int {table_1}_id FK
        string {column_2}
        datetime created_at
    }

    {TABLE_3} {
        int id PK
        int {table_2}_id FK
        string {column_3}
    }
```

## 3. テーブル定義

### {table_name_1}

**目的**: {purpose}

| カラム | 型 | 制約 | 説明 |
|-------|-----|------|------|
| id | integer | PK, AUTO_INCREMENT | 主キー |
| {column_name_1} | {type_1} | {constraint_1} | {description_1} |
| {column_name_2} | {type_2} | {constraint_2} | {description_2} |
| created_at | datetime | DEFAULT CURRENT_TIMESTAMP | 作成日時 |
| updated_at | datetime | ON UPDATE CURRENT_TIMESTAMP | 更新日時 |

### {table_name_2}

**目的**: {purpose}

| カラム | 型 | 制約 | 説明 |
|-------|-----|------|------|
| id | integer | PK, AUTO_INCREMENT | 主キー |
| {column_name_1} | {type_1} | {constraint_1} | {description_1} |
| created_at | datetime | DEFAULT CURRENT_TIMESTAMP | 作成日時 |

> 実際に動く CREATE 文（DDL）は Build フェーズの成果物として `db/schema.sql` などに作成する。
> この設計書ではテーブル定義表・ER図・制約までを正とする。

---

## 次のステップ

→ `05-api-ipo`（API・IPO一覧・詳細設計）でフローごとのIPOとAPI一覧を作成する
→ 必要に応じて `02-requirement`（要件定義書）の「対応テーブル」欄を追記更新する
