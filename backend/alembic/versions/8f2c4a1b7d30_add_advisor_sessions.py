"""add advisor sessions

Revision ID: 8f2c4a1b7d30
Revises: 511076d503e5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8f2c4a1b7d30"
down_revision: str | None = "511076d503e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advisor_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("knowledge_base_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_advisor_sessions_user_id", "advisor_sessions", ["user_id"])
    op.create_index(
        "ix_advisor_sessions_knowledge_base_id",
        "advisor_sessions",
        ["knowledge_base_id"],
    )
    op.create_index("ix_advisor_sessions_category", "advisor_sessions", ["category"])
    op.create_table(
        "advisor_turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("ai_trace", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["advisor_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "sequence_no", name="uq_advisor_turn_sequence"),
    )
    op.create_index("ix_advisor_turns_session_id", "advisor_turns", ["session_id"])
    op.create_index("ix_advisor_turns_message_id", "advisor_turns", ["message_id"])
    op.create_index("ix_advisor_turns_status", "advisor_turns", ["status"])


def downgrade() -> None:
    op.drop_index("ix_advisor_turns_status", table_name="advisor_turns")
    op.drop_index("ix_advisor_turns_message_id", table_name="advisor_turns")
    op.drop_index("ix_advisor_turns_session_id", table_name="advisor_turns")
    op.drop_table("advisor_turns")
    op.drop_index("ix_advisor_sessions_category", table_name="advisor_sessions")
    op.drop_index("ix_advisor_sessions_knowledge_base_id", table_name="advisor_sessions")
    op.drop_index("ix_advisor_sessions_user_id", table_name="advisor_sessions")
    op.drop_table("advisor_sessions")
