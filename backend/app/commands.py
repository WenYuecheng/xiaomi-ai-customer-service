import argparse

from sqlalchemy import select

from app.auth.service import create_user
from app.core.config import get_settings
from app.db.base import Base, create_database
from app.db.models import MockOrder, User


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
    parser.add_argument("command", choices=["init-demo"])
    args = parser.parse_args()
    if args.command == "init-demo":
        init_demo()


if __name__ == "__main__":
    main()
