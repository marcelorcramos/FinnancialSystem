import time
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.rabbitmq import RabbitMqContainer
from testcontainers.community.redis import RedisContainer
from testcontainers.core.container import DockerContainer

from alembic import command
from app.core.cache import Cache, get_cache
from app.core.jobs import JobQueue, get_job_queue
from app.core.rate_limit import RateLimiter, get_rate_limiter
from app.core.storage import Storage, get_storage
from app.db.session import get_session
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[2]
SEAWEEDFS_CONFIG = BACKEND_DIR.parent / "deploy" / "seaweedfs" / "s3.json"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in str(item.path):
            item.add_marker(pytest.mark.integration)


def alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def postgres() -> Iterator[PostgresContainer]:
    with PostgresContainer("postgres:16", driver="asyncpg") as container:
        yield container


@pytest.fixture(scope="session")
def redis_url() -> Iterator[str]:
    """A real Redis, started only by the tests that ask for it."""
    with RedisContainer("redis:7-alpine") as container:
        host, port = container.get_container_host_ip(), container.get_exposed_port(6379)
        yield f"redis://{host}:{port}/0"


@pytest.fixture(scope="session")
def rabbitmq_url() -> Iterator[str]:
    """A real RabbitMQ, started only by the tests that ask for it."""
    with RabbitMqContainer("rabbitmq:4", username="test", password="test") as container:
        host, port = container.get_container_host_ip(), container.get_exposed_port(5672)
        yield f"amqp://test:test@{host}:{port}/"


@pytest.fixture(scope="session")
def s3_url() -> Iterator[str]:
    """A real SeaweedFS S3 with the same credentials as Compose (anonymous access denied)."""
    container = (
        DockerContainer("chrislusf/seaweedfs:4.50")
        .with_command("server -dir=/data -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json")
        .with_volume_mapping(str(SEAWEEDFS_CONFIG), "/etc/seaweedfs/s3.json")
        .with_exposed_ports(8333)
    )
    with container:
        url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8333)}"
        storage = Storage(url, url, "probe")
        for _ in range(300):
            try:
                storage._s3.list_buckets()
                break
            except Exception:
                time.sleep(0.1)
        yield url


@pytest.fixture
def storage(s3_url: str) -> Iterator[Storage]:
    """Storage on the test S3; the API uses it for this test."""
    storage = Storage(s3_url, s3_url, "test-bucket")
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture(scope="session")
def database_url(postgres: PostgresContainer) -> str:
    url: str = postgres.get_connection_url()
    command.upgrade(alembic_config(url), "head")
    return url


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(database_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session inside a transaction that is rolled back after each test."""
    async with engine.connect() as connection:
        transaction = await connection.begin()
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        yield session
        await session.close()
        await transaction.rollback()


class RecordedJobs(JobQueue):
    """Keeps the jobs the API sends to Celery instead of sending them."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, dict[str, Any]]] = []

    async def enqueue(self, task: str, **kwargs: Any) -> None:
        self.sent.append((task, kwargs))

    def of(self, task: str) -> list[dict[str, Any]]:
        return [kwargs for name, kwargs in self.sent if name == task]


@pytest.fixture
def jobs() -> RecordedJobs:
    return RecordedJobs()


@pytest.fixture
async def client(session: AsyncSession, jobs: RecordedJobs) -> AsyncIterator[AsyncClient]:
    """API HTTP client using the test session (everything is rolled back at the end)."""

    async def _session_override() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session_override
    # No Redis by default: reads go straight to PostgreSQL (see test_cache.py).
    app.dependency_overrides.setdefault(get_cache, lambda: Cache(None))
    app.dependency_overrides.setdefault(get_rate_limiter, lambda: RateLimiter(None))
    app.dependency_overrides[get_job_queue] = lambda: jobs
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
