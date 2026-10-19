from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler


class AppError(APIException):
    def __init__(self, code, message, status=400):
        self.status_code = status
        super().__init__({"code": code, "message": message})


class PipelineError(Exception):
    def __init__(self, code, message, retryable=False):
        self.code, self.message, self.retryable = code, message, retryable
        super().__init__(code)


def exception_handler(exc, context):
    if isinstance(exc, PipelineError):
        exc = AppError(exc.code, exc.message, 503 if exc.retryable else 400)
    response = drf_exception_handler(exc, context)
    if response is not None:
        if isinstance(exc, AppError):
            response.data = {"error": response.data}
        else:
            response.data = {
                "error": {
                    "code": "VALIDATION_ERROR" if response.status_code == 400 else "REQUEST_REJECTED",
                    "message": "Please check the request.",
                    "details": response.data,
                }
            }
    return response
