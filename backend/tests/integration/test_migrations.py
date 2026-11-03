import asyncio
from typing import Any

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.community.postgres import PostgresContainer

from alembic import command
from app.db.base import Base
from app.models import *  # noqa: F403  (every model registers its table on Base.metadata)
from tests.integration.conftest import alembic_config


def _diff(connection: Connection) -> list[Any]:
    return list(compare_metadata(MigrationContext.configure(connection), Base.metadata))


async def _schema_diff(url: str) -> list[Any]:
    engine = create_async_engine(url)
    async with engine.connect() as connection:
        diff = await connection.run_sync(_diff)
    await engine.dispose()
    return diff


def test_migrations_upgrade_and_downgrade_cleanly(postgres: PostgresContainer) -> None:
    postgres.exec(["psql", "-U", postgres.username, "-c", "CREATE DATABASE migrations_check"])
    url = postgres.get_connection_url().rsplit("/", 1)[0] + "/migrations_check"
    config = alembic_config(url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    # The migrations build exactly what the models describe (like `alembic check`).
    assert asyncio.run(_schema_diff(url)) == []
