import logging
import logging.config
import sys
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.api.classes import router as classes_router
from app.core.logger import setup_logger, log_exception
from app.core.exceptions import FitnessStudioError
from app.api.error_handlers import register_error_handlers

# Setup logger
logger = setup_logger(__name__)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="API for managing fitness class bookings",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for managing fitness class bookings",
    version="1.0.0",
    docs_url=None,  # Disable default docs
    redoc_url=None,  # Disable default redoc
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Custom docs route
@app.get(f"{settings.API_V1_STR}/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        title=f"{settings.PROJECT_NAME} - Swagger UI",
        oauth2_redirect_url=None,
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip middleware for compressing responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routes
app.include_router(
    classes_router,
    prefix=f"{settings.API_V1_STR}",
    tags=["classes"],
)

# Add health check endpoint
@app.get("/health", include_in_schema=False)
async def health_check() -> Dict[str, str]:
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok"}

# Custom exception handlers
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming requests"""
    logger.info(
        "Request received",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else None,
            "headers": dict(request.headers),
        },
    )
    
    try:
        response = await call_next(request)
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
            },
        )
        return response
    except Exception as e:
        log_exception(logger, f"Request failed: {str(e)}")
        raise

# Register error handlers
register_error_handlers(app)

# Custom exception handler for 404 Not Found
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": {
                "code": "not_found",
                "message": "The requested resource was not found",
                "details": {"path": request.url.path}
            }
        }
    )

@app.get("/")
async def root():
    return {
        "message": "Welcome to Fitness Studio Booking API",
        "docs": f"{settings.API_V1_STR}/docs"
    }

# Set the custom OpenAPI schema
app.openapi = custom_openapi
