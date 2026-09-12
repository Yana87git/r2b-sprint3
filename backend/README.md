# 引合書整理エージェント — Backend (FastAPI)

設計の正は `docs/requirements/`（特に `agent.md` と `04-db.md` `05-api-ipo.md`）。

## セットアップ

```bash
uv sync                      # 依存（Python は .python-version = 3.12）
cp .env.example .env         # 値を埋める（ANTHROPIC_API_KEY は git 管理外）
```

## 開発サーバー

```bash
uv run uvicorn app.main:app --reload
```

- Swagger UI: http://localhost:8000/docs
- ヘルスチェック: http://localhost:8000/api/v1/health

## テスト・品質

```bash
uv run pytest
uv run ruff check .
```

## ディレクトリ

| パス | 役割 |
|------|------|
| `app/api/v1/endpoints` | エンドポイント（⑤ の API 19本） |
| `app/api/v1/schemas` | Pydantic のスキーマ |
| `app/core` | 設定・依存注入 |
| `app/models` | ORM（④ のテーブル8つ） |
| `app/repositories` | データアクセス |
| `app/services` | 業務ロジック（エージェントの起動もここから） |
| `app/agent` | Claude Agent SDK（Slice 0-7 で作る） |
| `traces/` | 実行トレース `{run_id}.jsonl`（git 管理外・ディレクトリのみ保持） |
| `tests/` | pytest |

## 留意点

- 3レイヤー（Presentation → Service → Repository）の依存の向きを守る（`.claude/rules/clean-architecture.md`）
- 認証は今回未実装。固定の営業事務ユーザーで動かす（① 6章）
- `ANTHROPIC_API_KEY` は `.env` のみ。コード・トレース・ドキュメントに書かない
