"""Password policy: at least 8 characters with a lowercase, an uppercase, a digit and a symbol."""

MIN_LENGTH = 8
MAX_LENGTH = 128


def password_problems(password: str) -> list[str]:
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")
    if not any(c.islower() for c in password):
        problems.append("a lowercase letter")
    if not any(c.isupper() for c in password):
        problems.append("an uppercase letter")
    if not any(c.isdigit() for c in password):
        problems.append("a digit")
    if not any(not c.isalnum() and not c.isspace() for c in password):
        problems.append("a special character")
    return problems
