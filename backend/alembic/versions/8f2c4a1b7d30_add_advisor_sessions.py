"""
文件职责：
该文件负责在 Alembic 迁移中创建智能顾问（Advisor）相关的会话表和交互回合表。

所属功能：
数据库迁移 / 智能顾问

主要流程：
1. 在 upgrade 函数中，创建 `advisor_sessions` 表记录顾问会话。
2. 创建 `advisor_turns` 表记录具体的每一回合对话状态与 AI 规划轨迹。
3. 在 downgrade 函数中，回滚并删除这些表和索引。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# 迁移版本的唯一标识符
revision: str = "8f2c4a1b7d30"
# 上一个迁移版本的标识符，用于链式追踪
down_revision: str | None = "511076d503e5"
# 分支标签，通常在复杂的迁移树中使用
branch_labels: str | Sequence[str] | None = None
# 依赖的其他迁移版本
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    执行数据库升级操作，创建顾问会话及对应的对话回合记录表。

    Args:
        无

    Returns:
        None
    """
    # 创建 advisor_sessions 表
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
    # 为 advisor_sessions 添加必要的索引以加速外键及业务查询
    op.create_index("ix_advisor_sessions_user_id", "advisor_sessions", ["user_id"])
    op.create_index(
        "ix_advisor_sessions_knowledge_base_id",
        "advisor_sessions",
        ["knowledge_base_id"],
    )
    op.create_index("ix_advisor_sessions_category", "advisor_sessions", ["category"])

    # 创建 advisor_turns 表
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
        # 同一会话下的回合序号必须唯一
        sa.UniqueConstraint("session_id", "sequence_no", name="uq_advisor_turn_sequence"),
    )
    # 为 advisor_turns 添加必要的查询索引
    op.create_index("ix_advisor_turns_session_id", "advisor_turns", ["session_id"])
    op.create_index("ix_advisor_turns_message_id", "advisor_turns", ["message_id"])
    op.create_index("ix_advisor_turns_status", "advisor_turns", ["status"])


def downgrade() -> None:
    """
    执行数据库降级操作，回滚创建的顾问相关数据表。

    Args:
        无

    Returns:
        None
    """
    # 按照依赖关系，先删除外键依赖表 advisor_turns 及其索引
    op.drop_index("ix_advisor_turns_status", table_name="advisor_turns")
    op.drop_index("ix_advisor_turns_message_id", table_name="advisor_turns")
    op.drop_index("ix_advisor_turns_session_id", table_name="advisor_turns")
    op.drop_table("advisor_turns")

    # 最后删除主表 advisor_sessions 及其索引
    op.drop_index("ix_advisor_sessions_category", table_name="advisor_sessions")
    op.drop_index("ix_advisor_sessions_knowledge_base_id", table_name="advisor_sessions")
    op.drop_index("ix_advisor_sessions_user_id", table_name="advisor_sessions")
    op.drop_table("advisor_sessions")
