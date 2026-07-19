"""
文件职责：
该文件负责验证 Docker 容器启动的初始化流程。

所属功能：
部署与容器化支持。

主要流程：
解析 Dockerfile 内容，确认数据库迁移和演示数据初始化的先后执行顺序。
"""

from pathlib import Path


def test_backend_container_runs_migrations_before_demo_initialization() -> None:
    """
    测试后端容器在启动时，是否先执行数据库迁移，然后再进行演示数据的初始化。

    通过分析 Dockerfile 中的命令出现顺序，来确保容器启动逻辑的安全性与正确性。
    """
    # 定位并读取项目中 Dockerfile 的文件内容，解码为字符串供后续处理。
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    # 在 Dockerfile 内容中寻找关键命令对应的字符串的起始索引。
    # 查找准备迁移命令。
    preparation = dockerfile.index("python -m app.commands prepare-migrations")
    # 查找执行 alembic 迁移升级的命令。
    migration = dockerfile.index("alembic upgrade head")
    # 查找初始化演示数据的命令。
    initialization = dockerfile.index("python -m app.commands init-demo")

    # 断言这三个命令在 Dockerfile 中的书写顺序必须是：准备迁移 -> 执行迁移 -> 初始化数据。
    # 这个顺序保证了表结构创建后才进行数据插入。
    assert preparation < migration < initialization
