"""引合の API（⑤ #4・#5・#9・#11・#17・#18）。認証は今回未実装で、固定ユーザーを使う（① 6章）。"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.errors import api_error
from app.api.v1.schemas import (
    ConfirmResponse,
    ItemListResponse,
    RowCheckResponse,
    ValueSourceResponse,
)
from app.api.v1.schemas.inquiry import InquiryCreateResponse, InquiryListResponse
from app.core.dependencies import get_db
from app.services import (
    confirm_service,
    inquiry_intake_service,
    inquiry_list_service,
    item_list_service,
    source_excerpt_service,
)
from app.services.inquiry_intake_service import ACCEPTED_MESSAGE, IntakeError, UploadedFile

router = APIRouter(prefix="/inquiries", tags=["Inquiries"])


@router.post("", response_model=InquiryCreateResponse, status_code=202)
async def create_inquiry(
    files: list[UploadFile] = File(default=[]),
    mail_body: str | None = Form(default=None),
    session: AsyncSession = Depends(get_db),
) -> InquiryCreateResponse:
    """入力を受け付け、案件を作り、**そのままエージェントを起動する**（⑤ #4）。"""
    uploads = [
        UploadedFile(filename=f.filename or "", content=await f.read()) for f in files if f.filename
    ]
    try:
        inquiry, inputs = await inquiry_intake_service.create_inquiry(session, uploads, mail_body)
    except IntakeError as e:
        raise api_error(400, e.code, e.message) from e
    # 実行記録は別のセッションで書くので、案件を先に確定させる
    await session.commit()

    try:
        run_id = await inquiry_intake_service.start_run(session, inquiry.id)
    except Exception as e:  # 起動できなければ受付ごと巻き戻す（⑤ #4）
        raise api_error(500, "INTERNAL_ERROR", "エージェントを起動できませんでした") from e

    return InquiryCreateResponse(
        inquiry_id=str(inquiry.id),
        inputs=[
            {
                "input_id": str(i.id),
                "display_name": i.display_name,
                "format": i.format,
                "message": ACCEPTED_MESSAGE[i.format],
            }
            for i in inputs
        ],
        run_id=run_id,
    )


@router.get("", response_model=InquiryListResponse)
async def list_inquiries(
    status: str | None = None, session: AsyncSession = Depends(get_db)
) -> InquiryListResponse:
    """引合一覧（⑤ #5）。投入日時の新しい順に全件返す。"""
    if status is not None and status not in inquiry_list_service.STATUSES:
        raise api_error(400, "INVALID_STATUS", "状況の指定が不正です")
    return InquiryListResponse(**await inquiry_list_service.list_inquiries(session, status))


@router.get("/{inquiry_id}/items", response_model=ItemListResponse)
async def get_items(
    inquiry_id: uuid.UUID,
    filter: str | None = None,
    include_excluded: bool = True,
    session: AsyncSession = Depends(get_db),
) -> ItemListResponse:
    """品目リスト案（⑤ #9）。**確認待ちで未記録のときだけ** KPI1 の起点を書く。"""
    payload = await item_list_service.get_items(
        session, inquiry_id, filter_=filter, include_excluded=include_excluded
    )
    if payload is None:
        raise api_error(404, "NOT_FOUND", "案件が見つかりません")
    await session.commit()
    return ItemListResponse(**payload)


@router.post("/{inquiry_id}/items/{row_id}/check", response_model=RowCheckResponse)
async def check_row(
    inquiry_id: uuid.UUID,
    row_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> RowCheckResponse:
    """行を確認済みにする（⑤ #11）。"""
    inquiry = await item_list_service.get_inquiry(session, inquiry_id)
    if inquiry is None:
        raise api_error(404, "NOT_FOUND", "案件が見つかりません")
    if inquiry.status == "confirmed":
        raise api_error(409, "ALREADY_CONFIRMED", "確定済みの案件は変更できません")

    payload = await item_list_service.check_row(session, inquiry_id, row_id)
    if payload is None:
        raise api_error(404, "NOT_FOUND", "行が見つかりません")
    await session.commit()
    return RowCheckResponse(**payload)


@router.get("/{inquiry_id}/values/{value_id}/source", response_model=ValueSourceResponse)
async def get_value_source(
    inquiry_id: uuid.UUID, value_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> ValueSourceResponse:
    """読み取り元と原本の抜粋（⑤ #14）。**この GET は抜き取りの記録も兼ねる。**"""
    payload = await source_excerpt_service.get_source(session, inquiry_id, value_id)
    if payload is None:
        raise api_error(404, "NOT_FOUND", "値が見つかりません")
    await session.commit()
    return ValueSourceResponse(**payload)


@router.get("/{inquiry_id}/export")
async def download_export(
    inquiry_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> FileResponse:
    """出力済み Excel のダウンロード（⑤ #18）。確定していなければ 404。"""
    export = await confirm_service.get_export(session, inquiry_id)
    if export is None:
        raise api_error(404, "NOT_FOUND", "出力された品目リストがありません")
    path = Path(export.storage_path)
    if not path.exists():
        raise api_error(404, "NOT_FOUND", "出力ファイルが見つかりません")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@router.post("/{inquiry_id}/confirm", response_model=ConfirmResponse)
async def confirm(
    inquiry_id: uuid.UUID, session: AsyncSession = Depends(get_db)
) -> ConfirmResponse:
    """確定して Excel を出力する（⑤ #17）。"""
    try:
        payload = await confirm_service.confirm(session, inquiry_id)
    except confirm_service.ConfirmError as e:
        raise api_error(409, e.code, e.message, **e.extra) from e
    if payload is None:
        raise api_error(404, "NOT_FOUND", "案件が見つかりません")
    await session.commit()
    return ConfirmResponse(**payload)
