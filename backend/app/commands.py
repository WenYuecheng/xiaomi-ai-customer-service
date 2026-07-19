"""
文件职责：
该文件负责提供管理应用生命周期的命令行脚本（CLI）。主要用于演示环境的初始化和数据库迁移的准备工作。

所属功能：
应用生命周期管理 / 命令行工具

主要流程：
1. 提供 `prepare_migrations` 方法，用于在将旧数据库升级为 Alembic 管理时打上初始版本戳。
2. 提供 `init_demo` 方法，用于创建表结构并写入演示用的种子数据（如管理员账号、测试订单）。
3. 通过 `argparse` 解析命令行参数并分发到对应功能。
"""

import argparse

from sqlalchemy import inspect, select, text

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base, create_database
from app.db.models import MockOrder, User

# 记录当前已知的 Alembic 迁移版本，用于遗留系统兼容
INITIAL_REVISION = "511076d503e5"
ADVISOR_REVISION = "8f2c4a1b7d30"
PROFILE_REVISION = "3c7d9a2e4f10"


def prepare_migrations(database_url: str | None = None) -> str | None:
    """
    为通过旧版 ``create_all`` 启动路径创建的数据库打上版本戳。

    对于全新或已经拥有版本号的数据库，不会进行任何修改。这个兼容性时间戳
    可以让 Alembic 只应用那些比当前遗留数据库模式更新的迁移。

    Args:
        database_url (str | None): 可选的数据库连接字符串。未提供则使用全局配置。

    Returns:
        str | None: 最终打在数据库上的迁移版本号。如果不是遗留库，返回 None 或已有的版本。
    """
    settings = get_settings()
    engine, _ = create_database(database_url or settings.database_url)

    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())

            # 如果连 users 表都没有，说明是新数据库，直接返回由正常迁移处理
            if "users" not in tables:
                return None

            # 创建 alembic_version 表来记录版本，如果不存在的话
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version "
                    "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )

            # 检查是否已经记录过版本
            existing = connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar_one_or_none()
            if existing:
                return str(existing)

            # 探测数据库当前状态，判断遗留系统的最新版本
            user_columns = {column["name"] for column in inspector.get_columns("users")}

            # 根据已存在的表结构特征，推断其对应的 Alembic 迁移版本
            if {"display_name", "avatar_key", "token_version"} <= user_columns:
                revision = PROFILE_REVISION
            elif {"advisor_sessions", "advisor_turns"} <= tables:
                revision = ADVISOR_REVISION
            else:
                revision = INITIAL_REVISION

            # 插入计算出的初始版本
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )
            return revision
    finally:
        engine.dispose()


def init_demo() -> None:
    """
    初始化演示环境。

    该函数将执行以下操作：
    1. 根据当前 ORM 模型定义，创建所有缺失的数据表。
    2. 创建配置文件中指定的初始管理员、操作员和用户账号。
    3. 为初始用户生成一些 mock（模拟）的订单数据。
    """
    settings = get_settings()
    engine, session_factory = create_database(settings.database_url)

    # 自动创建表结构（注意：生产环境应通过 Alembic 执行）
    Base.metadata.create_all(engine)

    # 定义要创建的初始账户列表
    accounts = [
        (settings.initial_admin_username, settings.initial_admin_password, "admin"),
        (settings.initial_operator_username, settings.initial_operator_password, "operator"),
        (settings.initial_user_username, settings.initial_user_password, "user"),
    ]

    with session_factory() as session:
        # 1. 遍历创建账号，如果密码有配置且用户不存在
        for username, password, role in accounts:
            if password and not session.scalar(select(User).where(User.username == username)):
                create_user(session, username, password, role)

        # 2. 查询出初始普通用户对象
        customer = session.scalar(
            select(User).where(User.username == settings.initial_user_username)
        )

        # 判断该用户是否已有模拟订单
        existing_order = customer and session.scalar(
            select(MockOrder).where(MockOrder.user_id == customer.id)
        )

        # 3. 如果用户存在且没有订单，则插入演示用订单
        if customer and not existing_order:
            session.add_all(
                [
                    MockOrder(
                        user_id=customer.id,
                        order_no="MOCK-20260717-001",
                        product_name="小米 14",
                        payment_status="已支付",
                        shipping_status="运输中",
                        logistics=["北京仓已出库", "正在运往配送站"],
                    ),
                    MockOrder(
                        user_id=customer.id,
                        order_no="MOCK-20260717-002",
                        product_name="米家扫地机器人 P10",
                        payment_status="已支付",
                        shipping_status="已签收",
                        logistics=["已揽收", "运输中", "已签收"],
                    ),
                ]
            )
            session.commit()

    engine.dispose()


def main() -> None:
    """
    命令行的入口函数。

    解析传入的子命令（init-demo / prepare-migrations）并调度执行。
    """
    parser = argparse.ArgumentParser(description="Course demo maintenance commands")
    parser.add_argument("command", choices=["init-demo", "prepare-migrations"])
    args = parser.parse_args()

    if args.command == "init-demo":
        init_demo()
    elif args.command == "prepare-migrations":
        prepare_migrations()


if __name__ == "__main__":
    main()
