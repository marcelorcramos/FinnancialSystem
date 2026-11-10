"""Domain errors. Routers do not know them: they are mapped to HTTP in app/api/errors.py."""


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class AuthenticationError(DomainError):
    code = "authentication_failed"


class ValidationError(DomainError):
    code = "validation_failed"


class InvalidTokenError(ValidationError):
    code = "invalid_token"

    def __init__(self) -> None:
        super().__init__("This link is invalid or has expired. Ask for a new one.")


class MonthClosedError(ConflictError):
    code = "month_closed"

    def __init__(self) -> None:
        super().__init__("The month is closed. Reopen it to make changes.")


class RateLimitedError(DomainError):
    code = "rate_limited"

    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many attempts. Try again later.")
        self.retry_after = retry_after
