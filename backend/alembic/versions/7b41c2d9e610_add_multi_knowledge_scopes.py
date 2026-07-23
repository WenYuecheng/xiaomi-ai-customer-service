"""add multi knowledge scopes

Revision ID: 7b41c2d9e610
Revises: 3c7d9a2e4f10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7b41c2d9e610"
down_revision: str | None = "3c7d9a2e4f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_knowledge_bases",
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("conversation_id", "knowledge_base_id"),
    )
    op.create_table(
        "advisor_session_knowledge_bases",
        sa.Column("advisor_session_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["advisor_session_id"], ["advisor_sessions.id"]),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.PrimaryKeyConstraint("advisor_session_id", "knowledge_base_id"),
    )
    op.execute(
        """INSERT INTO conversation_knowledge_bases
        (conversation_id, knowledge_base_id, ordinal)
        SELECT id, knowledge_base_id, 0 FROM conversations"""
    )
    op.execute(
        """INSERT INTO advisor_session_knowledge_bases
        (advisor_session_id, knowledge_base_id, ordinal)
        SELECT id, knowledge_base_id, 0 FROM advisor_sessions"""
    )


def downgrade() -> None:
    op.drop_table("advisor_session_knowledge_bases")
    op.drop_table("conversation_knowledge_bases")
