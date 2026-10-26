"""Política de passwords: mínimo 8 caracteres, com minúscula, maiúscula, número e símbolo."""

MIN_LENGTH = 8
MAX_LENGTH = 128


def password_problems(password: str) -> list[str]:
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"pelo menos {MIN_LENGTH} caracteres")
    if not any(c.islower() for c in password):
        problems.append("uma letra minúscula")
    if not any(c.isupper() for c in password):
        problems.append("uma letra maiúscula")
    if not any(c.isdigit() for c in password):
        problems.append("um número")
    if not any(not c.isalnum() and not c.isspace() for c in password):
        problems.append("um caractere especial")
    return problems
