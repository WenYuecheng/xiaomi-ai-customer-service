import argparse

from sqlalchemy import inspect, select, text

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base, create_database
from app.db.models import MockOrder, User

INITIAL_REVISION = "511076d503e5"
ADVISOR_REVISION = "8f2c4a1b7d30"
PROFILE_REVISION = "3c7d9a2e4f10"


def prepare_migrations(database_url: str | None = None) -> str | None:
    """Stamp databases created by the legacy ``create_all`` startup path.

    Fresh and already-versioned databases are left untouched. The compatibility
    stamp lets Alembic apply only migrations that are newer than the schema the
    legacy database already contains.
    """
    settings = get_settings()
    engine, _ = create_database(database_url or settings.database_url)
    try:
        with engine.begin() as connection:
            inspector = inspect(connection)
            tables = set(inspector.get_table_names())
            if "users" not in tables:
                return None

            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS alembic_version "
                    "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                )
            )
            existing = connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar_one_or_none()
            if existing:
                return str(existing)

            user_columns = {column["name"] for column in inspector.get_columns("users")}
            if {"display_name", "avatar_key", "token_version"} <= user_columns:
                revision = PROFILE_REVISION
            elif {"advisor_sessions", "advisor_turns"} <= tables:
                revision = ADVISOR_REVISION
            else:
                revision = INITIAL_REVISION
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )
            return revision
    finally:
        engine.dispose()


def init_demo() -> None:
    settings = get_settings()
    engine, session_factory = create_database(settings.database_url)
    Base.metadata.create_all(engine)
    accounts = [
        (settings.initial_admin_username, settings.initial_admin_password, "admin"),
        (settings.initial_operator_username, settings.initial_operator_password, "operator"),
        (settings.initial_user_username, settings.initial_user_password, "user"),
    ]
    with session_factory() as session:
        for username, password, role in accounts:
            if password and not session.scalar(select(User).where(User.username == username)):
                create_user(session, username, password, role)
        customer = session.scalar(
            select(User).where(User.username == settings.initial_user_username)
        )
        existing_order = customer and session.scalar(
            select(MockOrder).where(MockOrder.user_id == customer.id)
        )
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
    parser = argparse.ArgumentParser(description="Course demo maintenance commands")
    parser.add_argument("command", choices=["init-demo", "prepare-migrations"])
    args = parser.parse_args()
    if args.command == "init-demo":
        init_demo()
    elif args.command == "prepare-migrations":
        prepare_migrations()


if __name__ == "__main__":
    main()
