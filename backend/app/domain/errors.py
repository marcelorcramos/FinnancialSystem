"""Erros de domínio. Os routers não os conhecem: são traduzidos para HTTP em app/api/errors.py."""


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


class MonthClosedError(ConflictError):
    code = "month_closed"

    def __init__(self) -> None:
        super().__init__("O mês está fechado. Reabre-o para fazer alterações.")
