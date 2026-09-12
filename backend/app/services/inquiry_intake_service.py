"""引合の投入（⑤ #4）。入力を受け付け、案件を作り、そのままエージェントを起動する。

**受付・保管・起動は1つの処理**として扱う。起動に失敗したら案件も原本も巻き戻し、
「受付済みのまま実行記録が0件」という詰まった案件を残さない（⑤ #4）。
"""
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import jobs
from app.agent.prompt import build_system_prompt
from app.core.config import settings
from app.models import Inquiry, InquiryInput
from app.models.inquiry_input import MAX_FILE_BYTES
from app.repositories.user_repository import UserRepository

MAX_INPUTS = 10
MAX_TOTAL_BYTES = 50 * 1024 * 1024
RETENTION_DAYS = 90
FORMAT_BY_SUFFIX = {".xlsx": "excel", ".pdf": "pdf", ".docx": "word"}
# ③ SCR-03 の受付メッセージ（「Excel形式として受け付けました」）
ACCEPTED_MESSAGE = {
    "excel": "Excel形式として受け付けました",
    "pdf": "PDF形式として受け付けました",
    "word": "Word形式として受け付けました",
    "mail_body": "メール本文として受け付けました",
}
START_PROMPT = "投入された入力から品目リスト案を作り、完了条件を満たしたら終了してください。"


class IntakeError(Exception):
    """投入の受付で弾いた（⑤ #4 の 400）。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class UploadedFile:
    filename: str
    content: bytes


def storage_root() -> Path:
    root = Path(settings.STORAGE_DIR)
    return root if root.is_absolute() else Path(__file__).resolve().parents[2] / root


def validate(files: list[UploadedFile], mail_body: str | None) -> None:
    """受付の検査（② FUNC-01・非機能）。案件を作る前に全部見る。"""
    has_mail = bool((mail_body or "").strip())
    if not files and not has_mail:
        raise IntakeError("NO_INPUT", "ファイルもメール本文もありません")
    if len(files) + (1 if has_mail else 0) > MAX_INPUTS:
        raise IntakeError("TOO_MANY_INPUTS", f"入力は{MAX_INPUTS}件までです")
    for file in files:
        if Path(file.filename).suffix.lower() not in FORMAT_BY_SUFFIX:
            raise IntakeError(
                "UNSUPPORTED_FORMAT",
                f"{file.filename} は対応していない形式です（.xlsx / .pdf / .docx）",
            )
        if len(file.content) > MAX_FILE_BYTES:
            raise IntakeError("FILE_TOO_LARGE", f"{file.filename} は20MBを超えています")
    if sum(len(f.content) for f in files) > MAX_TOTAL_BYTES:
        raise IntakeError("TOTAL_SIZE_EXCEEDED", "合計が50MBを超えています")


def build_title(files: list[UploadedFile], mail_body: str | None) -> str:
    """③ の一覧と同じ付け方: 最初のファイル名 +「ほかN件」。ファイルが無ければ本文の1行目。"""
    if files:
        title = files[0].filename
        others = len(files) - 1 + (1 if (mail_body or "").strip() else 0)
        return f"{title} ほか{others}件" if others else title
    first_line = next(
        (line.strip() for line in (mail_body or "").splitlines() if line.strip()), "メール本文"
    )
    return first_line[:200]


async def create_inquiry(
    session: AsyncSession, files: list[UploadedFile], mail_body: str | None
) -> tuple[Inquiry, list[InquiryInput]]:
    """案件と入力を作り、原本を保管する（コミットは呼び出し側）。"""
    validate(files, mail_body)
    user = await UserRepository(session).get_fixed_user()
    if user is None:
        raise RuntimeError("固定ユーザーがいない。先に uv run python scripts/seed.py を実行する")

    inquiry = Inquiry(
        title=build_title(files, mail_body),
        status="received",
        submitted_by=user.id,
        retention_until=date.today() + timedelta(days=RETENTION_DAYS),
    )
    session.add(inquiry)
    await session.flush()

    saved: list[InquiryInput] = []
    directory = storage_root() / str(inquiry.id)
    directory.mkdir(parents=True, exist_ok=True)
    for index, file in enumerate(files, start=1):
        path = directory / f"{index:02d}_{Path(file.filename).name}"
        path.write_bytes(file.content)
        input_ = InquiryInput(
            inquiry_id=inquiry.id,
            kind="file",
            display_name=Path(file.filename).name,
            format=FORMAT_BY_SUFFIX[Path(file.filename).suffix.lower()],
            byte_size=len(file.content),
            storage_path=str(path),
        )
        session.add(input_)
        saved.append(input_)

    if (mail_body or "").strip():
        input_ = InquiryInput(
            inquiry_id=inquiry.id,
            kind="mail_body",
            display_name="メール本文",
            format="mail_body",
            content_text=mail_body,
        )
        session.add(input_)
        saved.append(input_)

    await session.flush()
    return inquiry, saved


async def start_run(session: AsyncSession, inquiry_id: uuid.UUID, attempt_no: int = 1) -> str:
    """エージェントを起動して run_id を返す。失敗したら案件ごと巻き戻す。"""
    try:
        return await jobs.start_agent_job(
            START_PROMPT,
            system_prompt=build_system_prompt(str(inquiry_id)),
            inquiry_id=str(inquiry_id),
            attempt_no=attempt_no,
        )
    except Exception:
        await session.execute(delete(Inquiry).where(Inquiry.id == inquiry_id))
        await session.commit()
        directory = storage_root() / str(inquiry_id)
        if directory.exists():
            for path in sorted(directory.glob("*")):
                path.unlink()
            directory.rmdir()
        raise
