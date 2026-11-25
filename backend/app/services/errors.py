"""Domain errors describe failures without depending on HTTP or FastAPI."""


class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass


class BadRequestError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ServiceUnavailableError(DomainError):
    pass
