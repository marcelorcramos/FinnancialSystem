import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789")
# Docker Desktop (macOS) expõe o socket noutro caminho; o Ryuk do testcontainers
# precisa do caminho dentro da VM. Em Linux/CI é o mesmo valor por omissão.
os.environ.setdefault("TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE", "/var/run/docker.sock")
