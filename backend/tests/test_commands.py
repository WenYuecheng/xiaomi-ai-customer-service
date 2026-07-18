import sqlite3

from app.commands import prepare_migrations


def test_prepare_migrations_stamps_unversioned_advisor_schema(tmp_path) -> None:
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

    revision = prepare_migrations(f"sqlite:///{database_path}")

    connection = sqlite3.connect(database_path)
    stored_revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    connection.close()
    assert revision == "8f2c4a1b7d30"
    assert stored_revision == revision
