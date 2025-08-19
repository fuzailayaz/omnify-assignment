"""
Error handlers for the FastAPI application.
"""
import logging
from typing import Any, Callable, Type, TypeVar, cast
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.exceptions import FitnessStudioError, error_mapping
from app.core.logger import logger

# Type variable for exception handling
E = TypeVar('E', bound=Exception)


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app."""
    # Register custom exception handler
    @app.exception_handler(FitnessStudioError)
    async def handle_fitness_studio_error(
        request: Request,
        exc: FitnessStudioError
    ) -> JSONResponse:
        """Handle FitnessStudioError and its subclasses."""
        logger.error(
            "API error",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "details": exc.details,
                "path": request.url.path,
            },
            exc_info=exc
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    # Register request validation error handler
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors."""
        errors = []
        for error in exc.errors():
            field = ".".join(map(str, error["loc"][1:]))  # Skip 'body' prefix
            errors.append({
                "field": field,
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(
            "Validation error",
            extra={
                "errors": errors,
                "path": request.url.path,
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Validation error",
                    "details": {"errors": errors}
                }
            }
        )
    
    # Register generic exception handler
    @app.exception_handler(Exception)
    async def handle_generic_exception(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """Handle all other exceptions."""
        logger.critical(
            "Unhandled exception",
            exc_info=exc,
            extra={"path": request.url.path}
        )
        
        # Find the most specific handler for this exception
        handler = None
        for exc_type, handler_func in error_mapping.items():
            if isinstance(exc, exc_type):
                handler = handler_func
                break
        
        if handler:
            error = handler(exc)
            if isinstance(error, FitnessStudioError):
                return await handle_fitness_studio_error(request, error)
        
        # Fallback to generic error
        error = FitnessStudioError(
            message="An unexpected error occurred",
            details={
                "type": exc.__class__.__name__,
                "message": str(exc)
            }
        )
        return await handle_fitness_studio_error(request, error)
    
    return app
