"""Domain errors raised by the service layer and mapped to HTTP codes in main.py."""


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFound(AppError):
    status_code = 404


class Forbidden(AppError):
    status_code = 403


class Conflict(AppError):
    status_code = 409


class BadRequest(AppError):
    status_code = 400
