"""API のエラー表現。⑤ 3章のエラーコードをそのまま返す。"""
from typing import Any

from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str, **extra: Any) -> HTTPException:
    """{code, message, ...} を detail に載せた HTTPException を作る。"""
    return HTTPException(
        status_code=status_code, detail={"code": code, "message": message, **extra}
    )
