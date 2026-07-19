"""
文件职责：
该文件负责Alembic数据库迁移环境的配置和初始化。

所属功能：
数据库迁移管理

主要流程：
1. 读取Alembic配置文件。
2. 从应用配置中获取数据库连接URL并设置。
3. 加载SQLAlchemy的元数据（MetaData）以支持自动生成迁移脚本。
4. 根据当前运行模式（离线或在线）执行相应的迁移逻辑。
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base
from app.db import models  # noqa: F401

# 获取Alembic的配置对象，该对象提供了对.ini文件中值的访问
config = context.config

# 如果配置文件指定了名称，则使用它来配置Python的日志记录器
if config.config_file_name:
    fileConfig(config.config_file_name)

# 动态设置SQLAlchemy的连接URL，使用我们应用的核心配置
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# 将目标元数据设置为我们应用中声明的Base.metadata，
# 这是自动生成迁移脚本（autogenerate）所必需的
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    在“离线”模式下运行数据库迁移。

    在此模式下，我们只需要配置context并提供URL，而不需要创建真正的数据库引擎（Engine）。
    通过这种方式，迁移脚本可以将SQL语句输出到控制台或文件中，而不是直接在数据库中执行。

    Args:
        无

    Returns:
        None
    """
    # 使用URL和目标元数据配置上下文
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    # 开启事务并运行迁移
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在“在线”模式下运行数据库迁移。

    在此模式下，我们需要创建一个真实的数据库连接（Engine），
    并将其与上下相关联。所有的迁移操作都将在一个事务中直接对数据库执行。

    Args:
        无

    Returns:
        None
    """
    # 从配置中创建数据库连接引擎，使用NullPool以避免连接池问题
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 建立连接并配置上下文
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        # 开启事务并运行迁移
        with context.begin_transaction():
            context.run_migrations()


# 根据当前上下文的模式（离线或在线），决定调用哪个函数来执行迁移
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
