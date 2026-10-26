import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789")
# The `postgres` fixture already stops the container at the end of the session. Ryuk (the
# testcontainers auto-cleanup) fails intermittently on Docker Desktop, so it is disabled.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
