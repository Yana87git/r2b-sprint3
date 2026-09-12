"""FastAPI の OpenAPI スキーマを書き出す。"""
import argparse
import json
import sys
from pathlib import Path

# scripts/ から実行しても backend/ を検索パスに含める
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema")
    parser.add_argument("-o", "--output", default="openapi.json", help="出力先")
    args = parser.parse_args()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)

    print(f"OpenAPI schema exported to: {args.output}")


if __name__ == "__main__":
    main()
