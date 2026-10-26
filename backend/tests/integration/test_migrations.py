from testcontainers.community.postgres import PostgresContainer

from alembic import command
from tests.integration.conftest import alembic_config


def test_migrations_upgrade_and_downgrade_cleanly(postgres: PostgresContainer) -> None:
    postgres.exec(["psql", "-U", postgres.username, "-c", "CREATE DATABASE migrations_check"])
    url = postgres.get_connection_url().rsplit("/", 1)[0] + "/migrations_check"
    config = alembic_config(url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
