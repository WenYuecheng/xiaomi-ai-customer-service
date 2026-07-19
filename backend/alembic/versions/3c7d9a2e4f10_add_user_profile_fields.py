"""
文件职责：
该文件负责在Alembic迁移中为用户表（users）添加个人资料相关的字段。

所属功能：
数据库迁移 / 用户管理

主要流程：
1. 在upgrade函数中，向users表添加显示名称（display_name）、头像（avatar_key）和令牌版本（token_version）字段。
2. 并在升级过程中通过SQL语句处理已存在数据的默认值填充。
3. 在downgrade函数中，执行回滚操作，移除上述添加的字段。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# 迁移版本的唯一标识符
revision: str = "3c7d9a2e4f10"
# 上一个迁移版本的标识符，用于链式追踪
down_revision: str | None = "8f2c4a1b7d30"
# 分支标签，通常在复杂的迁移树中使用
branch_labels: str | Sequence[str] | None = None
# 依赖的其他迁移版本
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    执行数据库升级操作，添加用户相关的字段。

    Args:
        无

    Returns:
        None
    """
    # 批量修改 users 表
    with op.batch_alter_table("users") as batch_op:
        # 添加显示名称字段，非空，默认值为空字符串
        batch_op.add_column(
            sa.Column("display_name", sa.String(length=40), nullable=False, server_default="")
        )
        # 添加头像标识字段，非空，默认值为 aurora
        batch_op.add_column(
            sa.Column("avatar_key", sa.String(length=20), nullable=False, server_default="aurora")
        )
        # 添加令牌版本字段，非空，默认值为 0，用于管理和作废 JWT
        batch_op.add_column(
            sa.Column("token_version", sa.Integer(), nullable=False, server_default="0")
        )

    # 针对历史数据，将显示名称设置为了用户名，避免显示为空
    op.execute(sa.text("UPDATE users SET display_name = username WHERE display_name = ''"))


def downgrade() -> None:
    """
    执行数据库降级操作，回滚添加的用户字段。

    Args:
        无

    Returns:
        None
    """
    # 批量修改 users 表，移除新增的三个字段
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("token_version")
        batch_op.drop_column("avatar_key")
        batch_op.drop_column("display_name")
