"""value_clues — 確信が低いと判断した手がかり H1〜H4（① 2章）。1つの値に複数付く。"""
import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin

# H1 ファイル間不一致 / H2 列内の形式ずれ / H3 単位数量の不自然 / H4 正規化の非一意
CLUES = ("H1", "H2", "H3", "H4")


class ValueClue(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "value_clues"

    item_value_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("item_values.id", ondelete="CASCADE"), nullable=False
    )
    clue: Mapped[str] = mapped_column(String(4), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("clue IN ('H1','H2','H3','H4')", name="ck_value_clues_clue"),
        UniqueConstraint("item_value_id", "clue", name="uq_value_clues_value_clue"),
        Index("ix_value_clues_item_value_id", "item_value_id"),
    )
