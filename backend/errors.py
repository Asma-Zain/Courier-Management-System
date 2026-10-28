"""Domain errors raised by the service layer and mapped to HTTP codes in main.py."""


class AppError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, **extra):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.extra = extra


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"


class BadRequest(AppError):
    status_code = 400
    code = "BAD_REQUEST"


class TooManyRequests(AppError):
    status_code = 429
    code = "RATE_LIMITED"
