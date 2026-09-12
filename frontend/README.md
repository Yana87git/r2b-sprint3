# 引合書整理エージェント — Frontend (Next.js 15)

Next.js 15（App Router）+ Material-UI + TanStack Query。バックエンド（FastAPI）は
`http://localhost:8000`、この画面は `http://localhost:3000`。

## セットアップ

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev   # http://localhost:3000 → /dashboard
```

## 開発コマンド

- `npm run dev` / `npm run build`
- `npm run test`（Jest）・`npm run typecheck`
- `npm run orval`（`backend/openapi.json` から API クライアントとフックを再生成）

## 構造

- `app/`: ページ（Server Component のまま薄く保つ）
- `features/`: 機能単位（api.ts / hooks.ts / components/ / index.ts）。外へは index.ts 経由
- `shared/api/generated/`: orval 自動生成（編集禁止・git 管理外）
- `shared/{ui,hooks,lib,theme,i18n}/`: 横断モジュール

## ルール

- Client Component には `"use client"` を明示
- JSX に日本語を直書きしない（`t()` を使う）
- デザイン値は `shared/theme/tokens.ts` 経由のみ（真実源は `docs/requirements/03-spec.md` 3章）

## 今回のスコープ

認証は実装しない（① 6章）。`(auth)/login` は作らず、API 側は固定ユーザーで動く。
画面は SCR-03 投入 / SCR-04 処理状況 / SCR-05 確認 / SCR-09 完了 の4つを作る。
