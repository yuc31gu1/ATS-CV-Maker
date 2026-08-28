from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    code = "INTERNAL_ERROR"
    status_code = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ResourceValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class InvalidResumeError(AppError):
    code = "INVALID_RESUME"
    status_code = 422


class LLMValidationFailed(AppError):
    code = "LLM_VALIDATION_FAILED"
    status_code = 502


class TailoringFailed(AppError):
    code = "TAILORING_FAILED"
    status_code = 502


class LatexCompilationFailed(AppError):
    code = "LATEX_COMPILATION_FAILED"
    status_code = 502


class PdfValidationFailed(AppError):
    code = "PDF_VALIDATION_FAILED"
    status_code = 502


class StorageFileNotFound(AppError):
    code = "FILE_NOT_FOUND"
    status_code = 404


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": exc.code, "message": exc.message, "details": exc.details}
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
        )