# r2b-sprint3

R2B ブートキャンプ Sprint3（個人開発）の作業リポジトリ。

- **テーマ**: AI Agent（自律エージェント）の設計・開発
- **スタック**: Claude Agent SDK（Python）。全てローカル実行・クラウドデプロイなし
- **お題A**: 引合書整理エージェント（Design → Build → Review）
- **お題B**: Review 後に着手（`/r2b-env-sprint3` か `/r2b-present-sprint3` のどちらか一方）

## 進め方

| フェーズ | コマンド |
|---------|---------|
| Design  | `/r2b-design-sprint3`（Vモデル10ステップ → `docs/requirements/`） |
| Build   | `/r2b-build-sprint3` → foundation エージェント → `/build-loop` |
| Review  | `/r2b-review-sprint3` |

設計成果物は `docs/requirements/` 配下（`agent-plan.md` が Sprint3 の中心）。
