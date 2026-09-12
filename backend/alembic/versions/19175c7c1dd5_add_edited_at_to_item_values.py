"""add edited_at to item_values

Revision ID: 19175c7c1dd5
Revises: 577f4e4fc98b
Create Date: 2026-09-13 06:38:35.063518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '19175c7c1dd5'
down_revision: Union[str, None] = '577f4e4fc98b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHECK_NAME = "ck_item_values_extracted_needs_source"
OLD_CHECK = (
    "(state = 'extracted' AND raw_text IS NOT NULL AND source_input_id IS NOT NULL "
    "AND locator IS NOT NULL) OR "
    "(state = 'needs_confirmation' AND raw_text IS NULL AND source_input_id IS NULL "
    "AND locator IS NULL)"
)
NEW_CHECK = (
    "(state = 'extracted' AND ((raw_text IS NOT NULL AND source_input_id IS NOT NULL "
    "AND locator IS NOT NULL) OR edited_at IS NOT NULL)) OR "
    "(state = 'needs_confirmation' AND raw_text IS NULL AND source_input_id IS NULL "
    "AND locator IS NULL)"
)


def upgrade() -> None:
    """人が直した値（⑤ #10）は読み取り元を持たないので、その場合だけ制約を緩める。"""
    op.add_column(
        "item_values", sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "item_values",
        sa.Column("edited_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_item_values_edited_by_users", "item_values", "users", ["edited_by"], ["id"]
    )
    op.drop_constraint(CHECK_NAME, "item_values", type_="check")
    op.create_check_constraint(CHECK_NAME, "item_values", NEW_CHECK)


def downgrade() -> None:
    op.drop_constraint(CHECK_NAME, "item_values", type_="check")
    op.create_check_constraint(CHECK_NAME, "item_values", OLD_CHECK)
    op.drop_constraint("fk_item_values_edited_by_users", "item_values", type_="foreignkey")
    op.drop_column("item_values", "edited_by")
    op.drop_column("item_values", "edited_at")
