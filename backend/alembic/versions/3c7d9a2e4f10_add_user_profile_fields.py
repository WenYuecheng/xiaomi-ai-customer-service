"""add user profile fields

Revision ID: 3c7d9a2e4f10
Revises: 8f2c4a1b7d30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3c7d9a2e4f10"
down_revision: str | None = "8f2c4a1b7d30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column("display_name", sa.String(length=40), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("avatar_key", sa.String(length=20), nullable=False, server_default="aurora")
        )
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
        )
    op.execute(sa.text("UPDATE users SET display_name = username WHERE display_name = ''"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
        batch_op.drop_column("avatar_key")
        batch_op.drop_column("display_name")
