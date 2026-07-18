from pathlib import Path


def test_backend_container_runs_migrations_before_demo_initialization() -> None:
    dockerfile = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")

    preparation = dockerfile.index("python -m app.commands prepare-migrations")
    migration = dockerfile.index("alembic upgrade head")
    initialization = dockerfile.index("python -m app.commands init-demo")

    assert preparation < migration < initialization
