"""
Custom exceptions for the Fitness Studio API.
"""
from fastapi import status
from typing import Any, Dict, Optional

class FitnessStudioError(Exception):
    """Base exception for all Fitness Studio API errors."""
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_server_error"
    message: str = "An unexpected error occurred"
    details: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.message = message or self.message
        self.details = details or {**kwargs}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for JSON responses."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details or {}
            }
        }

# 400 Bad Request Errors
class ValidationError(FitnessStudioError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "validation_error"
    message = "Invalid request data"

class TimezoneError(ValidationError):
    error_code = "invalid_timezone"
    message = "Invalid timezone provided"

class BookingError(ValidationError):
    error_code = "booking_error"
    message = "Booking could not be processed"

class DuplicateBookingError(BookingError):
    error_code = "duplicate_booking"
    message = "User has already booked this class"

class ClassFullError(BookingError):
    error_code = "class_full"
    message = "No available slots in this class"

# 401 Unauthorized
class AuthenticationError(FitnessStudioError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"
    message = "Authentication failed"

# 403 Forbidden
class AuthorizationError(FitnessStudioError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "authorization_error"
    message = "Not authorized to perform this action"

# 404 Not Found
class NotFoundError(FitnessStudioError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    message = "The requested resource was not found"

class ClassNotFoundError(NotFoundError):
    error_code = "class_not_found"
    message = "Class not found"

class BookingNotFoundError(NotFoundError):
    error_code = "booking_not_found"
    message = "Booking not found"

# 409 Conflict
class ConflictError(FitnessStudioError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict_error"
    message = "A conflict occurred with the current state of the resource"

# 422 Unprocessable Entity
class UnprocessableEntityError(FitnessStudioError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "unprocessable_entity"
    message = "The request was well-formed but was unable to be processed"

# 429 Too Many Requests
class RateLimitExceededError(FitnessStudioError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limit_exceeded"
    message = "Too many requests, please try again later"

# 500 Internal Server Error
class DatabaseError(FitnessStudioError):
    error_code = "database_error"
    message = "A database error occurred"

class ExternalServiceError(FitnessStudioError):
    error_code = "external_service_error"
    message = "An error occurred with an external service"

# Error handler mappings
error_mapping = {
    # 400 Errors
    ValueError: lambda e: ValidationError(str(e)),
    
    # 404 Errors
    LookupError: lambda e: NotFoundError(str(e)),
    
    # 409 Errors
    RuntimeError: lambda e: ConflictError(str(e)),
    
    # 500 Errors
    Exception: lambda e: FitnessStudioError("An unexpected error occurred"),
}
