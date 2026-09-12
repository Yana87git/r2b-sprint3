"""アプリケーション設定（環境変数は backend/.env から読む）。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """設計書の対応: ② 非機能要件 / ① 6章「技術前提」。"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # アプリケーション
    APP_NAME: str = "引合書整理エージェント API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # データベース（Slice 0-2 で Docker の PostgreSQL に接続する）
    DATABASE_URL: str = "postgresql+psycopg://r2b:r2b_local_dev@localhost:5432/inquiry"

    # CORS（③ の Frontend は Next.js 15 / ポート 3000）
    # 3000 が他のアプリに使われていると Next は 3001 に逃げるので、両方許可しておく
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # エージェント（Slice 0-7 で使う。値は backend/.env のみに置く）
    ANTHROPIC_API_KEY: str = ""

    # 原本と出力 Excel の保管先（backend からの相対。git 管理外）
    STORAGE_DIR: str = "storage"

    # 認証: 今回は実装しない（① 6章。固定の営業事務ユーザーで動かす）
    # 将来 Scope 2 で JWT を入れるときの設定置き場:
    # JWT_SECRET_KEY: str = ""
    # JWT_ALGORITHM: str = "HS256"
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


settings = Settings()
