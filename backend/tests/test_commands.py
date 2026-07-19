"""
文件职责：
该文件负责测试应用层面的命令行脚本，主要是数据库迁移的准备命令。

所属功能：
数据库迁移指令 (Database Migration Commands)

主要流程：
1. 建立模拟的历史遗留数据库结构。
2. 运行 Alembic 准备迁移脚本。
3. 验证迁移版本号的正确性。
"""

import sqlite3

from app.commands import prepare_migrations


def test_prepare_migrations_stamps_unversioned_advisor_schema(tmp_path) -> None:
    """
    测试准备迁移脚本能够正确地为无版本记录的旧有 Advisor 数据库结构打上初始版本戳。

    Args:
        tmp_path: pytest 提供的临时目录，用于生成独立的测试数据库。

    Returns:
        None

    Raises:
        AssertionError: 当从数据库查出的 revision 与命令返回的不一致时。
    """
    # 初始化一个基于文件的 sqlite 数据库连接以模拟旧有架构
    database_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(database_path)
    connection.executescript(
        """
        CREATE TABLE users (id VARCHAR(36) PRIMARY KEY, username VARCHAR(64));
        CREATE TABLE advisor_sessions (id VARCHAR(36) PRIMARY KEY);
        CREATE TABLE advisor_turns (id VARCHAR(36) PRIMARY KEY);
        """
    )
    connection.close()

    # 获取准备完毕后最新的 revision 版本号
    revision = prepare_migrations(f"sqlite:///{database_path}")

    # 验证数据库中实际存储的版本号以确保 stamp 成功
    connection = sqlite3.connect(database_path)
    stored_revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    connection.close()
    assert revision == "8f2c4a1b7d30"
    assert stored_revision == revision
