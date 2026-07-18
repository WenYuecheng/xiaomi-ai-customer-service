"""
文件职责：
该文件负责封装 SQLAlchemy 的基础设置，包括声明式基类、数据库引擎创建以及提供会话（Session）依赖。

所属功能：
核心基础设施 -> 数据库访问层。

主要流程：
1. 声明 `Base` 作为所有 ORM 模型的基类。
2. 在应用启动时创建全局数据库连接引擎（Engine）和会话工厂（sessionmaker）。
3. 定义 FastAPI 路由依赖注入所需的数据库会话生成器 `get_session`。

主要调用方：
`main.py` 调用 `create_database` 初始化，各业务路由调用 `SessionDep`。
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """
    主要职责：
    SQLAlchemy ORM 模型的声明式基类。所有表模型都必须继承它。
    """

    pass


def create_database(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    """
    功能归属：
    核心基础设施 -> 数据库访问层。

    函数职责：
    根据配置连接字符串初始化并返回 SQLAlchemy 的数据库引擎和会话工厂。

    调用方：
    应用启动入口（`app/main.py`）。

    注意事项：
    对 SQLite 添加了 `check_same_thread=False` 参数，以兼容 FastAPI 的异步并发模型。
    """
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, factory


def get_session(request: Request) -> Iterator[Session]:
    """
    内部辅助函数：
    在请求到达时，从全局应用状态中提取会话工厂并分配一个新的数据库连接会话。
    采用 Generator 方式，当请求结束时，`with` 语法糖会自动关闭 session，释放连接归还连接池。
    """
    with request.app.state.session_factory() as session:
        yield session


# 公共依赖项，供 FastAPI 控制器注入使用。
SessionDep = Annotated[Session, Depends(get_session)]
