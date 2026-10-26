import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789")
# O fixture `postgres` já para o contentor no fim da sessão. O Ryuk (limpeza automática do
# testcontainers) falha de forma intermitente no Docker Desktop, por isso fica desligado.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
