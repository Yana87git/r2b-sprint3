"""item_list_exports — 確定時に出力した品目リスト（Excel）の記録（04）。"""
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class ItemListExport(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "item_list_exports"

    # 確定は1案件につき1回なので1対1
    inquiry_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("inquiries.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    # 「顧客回答待ち」として出力した行数（③ SCR-09）
    pending_row_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
