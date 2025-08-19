from fastapi import (
    APIRouter, Depends, HTTPException, status, 
    Query, Path, Body, Request, Response
)
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pytz
from pydantic import BaseModel, Field

from app.core.logger import logger
from app.db.session import get_db
from app.models.classes import FitnessClass, Booking
from app.schemas.classes import (
    FitnessClassCreate, FitnessClassInDB, FitnessClassUpdate,
    BookingCreate, BookingInDB, FitnessClassBase
)
from app.core.config import settings

# Constants
DEFAULT_TIMEZONE = 'Asia/Kolkata'
TIMEZONE_PATTERN = r'^[A-Za-z_]+/[A-Za-z_]+$'

# Error messages
INVALID_TIMEZONE_MSG = "Invalid timezone provided"
CLASS_NOT_FOUND_MSG = "Class not found"
BOOKING_NOT_FOUND_MSG = "Booking not found"
NO_AVAILABLE_SLOTS_MSG = "No available slots"
DUPLICATE_BOOKING_MSG = "You have already booked this class"

router = APIRouter()

@router.post("/classes", response_model=FitnessClassInDB, status_code=status.HTTP_201_CREATED, tags=["Classes"])
async def create_class(
    request: Request,
    fitness_class: FitnessClassCreate,
    timezone: str = Query(
        DEFAULT_TIMEZONE,
        description="Timezone for the class times",
        regex=TIMEZONE_PATTERN,
        example=DEFAULT_TIMEZONE
    ),
    db: Session = Depends(get_db)
):
    logger.info(
        "Creating new fitness class",
        extra={
            "class_name": fitness_class.name,
            "timezone": timezone,
            "client": request.client.host if request.client else None,
        },
    )
    
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as e:
        logger.error(INVALID_TIMEZONE_MSG, extra={"timezone": timezone, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{INVALID_TIMEZONE_MSG}: {timezone}"
        ) from e
    
    # Convert input times to timezone-aware datetimes
    try:
        start_time = fitness_class.start_time.astimezone(tz) if fitness_class.start_time.tzinfo else tz.localize(fitness_class.start_time)
        end_time = fitness_class.end_time.astimezone(tz) if fitness_class.end_time.tzinfo else tz.localize(fitness_class.end_time)
    except (AttributeError, ValueError) as e:
        logger.error("Invalid datetime format", extra={"error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid datetime format: {str(e)}"
        ) from e
    
    # Create the class with timezone information
    db_class = FitnessClass(
        name=fitness_class.name,
        description=fitness_class.description,
        instructor=fitness_class.instructor,
        start_time=start_time,
        end_time=end_time,
        capacity=fitness_class.capacity,
        available_slots=fitness_class.capacity,  # Initially all slots are available
        timezone=timezone
    )
    
    try:
        db.add(db_class)
        db.commit()
        db.refresh(db_class)
        
        # Log successful creation
        logger.info(
            "Successfully created fitness class",
            extra={
                "class_id": db_class.id,
                "class_name": db_class.name,
                "start_time": db_class.start_time.isoformat(),
                "end_time": db_class.end_time.isoformat(),
            },
        )
        
        # Set the timezone for the response
        db_class.timezone = timezone
        return db_class
        
    except Exception as e:
        logger.error(
            "Failed to create fitness class",
            exc_info=True,
            extra={
                "class_name": fitness_class.name,
                "error": str(e),
            },
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the fitness class"
        ) from e

def _get_class_before_update(db_class: FitnessClass) -> dict:
    """Get the state of a class before updates are applied."""
    return {
        "name": db_class.name,
        "instructor": db_class.instructor,
        "start_time": db_class.start_time.isoformat() if db_class.start_time else None,
        "end_time": db_class.end_time.isoformat() if db_class.end_time else None,
        "capacity": db_class.capacity,
        "available_slots": db_class.available_slots,
    }

def _get_class_after_update(db_class: FitnessClass) -> dict:
    """Get the state of a class after updates are applied."""
    return {
        "name": db_class.name,
        "instructor": db_class.instructor,
        "start_time": db_class.start_time.isoformat() if db_class.start_time else None,
        "end_time": db_class.end_time.isoformat() if db_class.end_time else None,
        "capacity": db_class.capacity,
        "available_slots": db_class.available_slots,
    }

def _process_time_updates(update_data: dict, tz: pytz.BaseTzInfo) -> None:
    """Process time-related updates and convert to timezone-aware datetimes."""
    if 'start_time' in update_data:
        start_time = update_data['start_time']
        update_data['start_time'] = start_time.astimezone(tz) if start_time.tzinfo else tz.localize(start_time)
    
    if 'end_time' in update_data:
        end_time = update_data['end_time']
        update_data['end_time'] = end_time.astimezone(tz) if end_time.tzinfo else tz.localize(end_time)

def _get_db_class_with_lock(db: Session, class_id: int) -> FitnessClass:
    """Retrieve a class from the database with a row lock."""
    db_class = (db.query(FitnessClass)
               .filter(FitnessClass.id == class_id)
               .with_for_update()
               .first())
    
    if not db_class:
        logger.warning("Class not found for update", extra={"class_id": class_id})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=CLASS_NOT_FOUND_MSG
        )
    return db_class

@router.put("/classes/{class_id}", response_model=FitnessClassInDB, tags=["Classes"])
async def update_class(
    request: Request,
    class_id: int,
    fitness_class: FitnessClassUpdate,
    timezone: str = Query(
        DEFAULT_TIMEZONE,
        description="Timezone for the class times",
        regex=TIMEZONE_PATTERN,
        example=DEFAULT_TIMEZONE
    ),
    db: Session = Depends(get_db)
):
    """
    Update an existing fitness class with the provided data.
    
    - **class_id**: ID of the class to update
    - **fitness_class**: Class data to update
    - **timezone**: Timezone for datetime fields
    """
    logger.info(
        "Updating fitness class",
        extra={
            "class_id": class_id,
            "updates": fitness_class.dict(exclude_unset=True),
            "client": request.client.host if request.client else None,
            "timezone": timezone,
        },
    )
    
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as e:
        logger.error(INVALID_TIMEZONE_MSG, extra={"timezone": timezone, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone: {timezone}"
        ) from e
    
    try:
        # Get and validate the class
        db_class = _get_db_class_with_lock(db, class_id)
        before_update = _get_class_before_update(db_class)
        
        # Process updates
        update_data = fitness_class.dict(exclude_unset=True)
        if 'start_time' in update_data or 'end_time' in update_data:
            _process_time_updates(update_data, tz)
        
        # Apply updates
        for field, value in update_data.items():
            setattr(db_class, field, value)
        
        # Save changes
        db.add(db_class)
        db.commit()
        db.refresh(db_class)
        
        # Log successful update
        logger.info(
            "Successfully updated fitness class",
            extra={
                "class_id": class_id,
                "before_update": before_update,
                "after_update": _get_class_after_update(db_class),
            },
        )
        
        # Convert times to requested timezone for response
        if db_class.start_time and db_class.end_time:
            db_class.start_time = db_class.start_time.astimezone(tz)
            db_class.end_time = db_class.end_time.astimezone(tz)
        
        return db_class
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to update fitness class",
            exc_info=True,
            extra={
                "class_id": class_id,
                "error": str(e),
            },
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the fitness class"
        ) from e

@router.delete("/bookings/{booking_id}", status_code=status.HTTP_200_OK, tags=["Bookings"])
@router.post("/bookings/{booking_id}/cancel", status_code=status.HTTP_200_OK, tags=["Bookings"], include_in_schema=False)
async def cancel_booking(
    request: Request,
    booking_id: int,
    db: Session = Depends(get_db)
):
    logger.info(
        "Cancelling booking",
        extra={
            "booking_id": booking_id,
            "client": request.client.host if request.client else None,
        },
    )
    
    try:
        # Get the booking with a lock to prevent concurrent operations
        db_booking = (db.query(Booking)
                     .filter(Booking.id == booking_id)
                     .with_for_update()
                     .first())
        
        if not db_booking:
            logger.warning("Booking not found for cancellation", extra={"booking_id": booking_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=BOOKING_NOT_FOUND_MSG
            )
        
        # Get the associated class and lock it
        db_class = (db.query(FitnessClass)
                   .filter(FitnessClass.id == db_booking.fitness_class_id)
                   .with_for_update()
                   .first())
        
        if not db_class:
            logger.error(
                "Associated class not found for booking",
                extra={"booking_id": booking_id, "class_id": db_booking.fitness_class_id}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Associated class not found"
            )
        
        # Log booking cancellation
        logger.debug(
            "Processing booking cancellation",
            extra={
                "client_name": db_booking.client_name,
                "client_email": db_booking.client_email,
                "booking_created_at": db_booking.created_at.isoformat(),
                "class_name": getattr(db_class, 'name', 'N/A'),
                "class_start_time": db_class.start_time.isoformat() if db_class.start_time else None,
            },
        )
        
        # Increment available slots
        db_class.available_slots += 1
        
        # Delete the booking
        db.delete(db_booking)
        db.commit()
        
        logger.info(
            "Successfully cancelled booking",
            extra={
                "booking_id": booking_id,
                "class_id": db_class.id,
                "client_email": db_booking.client_email,
                "available_slots_after": db_class.available_slots,
            },
        )
        
        return {
            "status": "success",
            "message": "Booking cancelled successfully",
            "class_name": db_class.name,
            "available_slots": db_class.available_slots,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to cancel booking",
            exc_info=True,
            extra={
                "booking_id": booking_id,
                "error": str(e),
            },
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while cancelling the booking"
        ) from e

@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Classes"])
async def delete_class(
    request: Request,
    class_id: int,
    db: Session = Depends(get_db)
):
    logger.info(
        "Deleting fitness class",
        extra={
            "class_id": class_id,
            "client": request.client.host if request.client else None,
        },
    )
    
    try:
        # Get the class with a lock to prevent concurrent operations
        db_class = (db.query(FitnessClass)
                   .filter(FitnessClass.id == class_id)
                   .with_for_update()
                   .first())
        
        if not db_class:
            logger.warning("Class not found for deletion", extra={"class_id": class_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found"
            )
        
        # Log class details before deletion (for audit)
        class_details = {
            "name": db_class.name,
            "instructor": db_class.instructor,
            "start_time": db_class.start_time.isoformat() if db_class.start_time else None,
            "end_time": db_class.end_time.isoformat() if db_class.end_time else None,
            "capacity": db_class.capacity,
            "available_slots": db_class.available_slots,
            "booking_count": len(db_class.bookings) if hasattr(db_class, 'bookings') else 0,
        }
        
        # Delete the class (cascading deletes will handle related bookings)
        db.delete(db_class)
        db.commit()
        
        logger.info(
            "Successfully deleted fitness class",
            extra={
                "class_id": class_id,
                "class_details": class_details,
            },
        )
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete fitness class",
            exc_info=True,
            extra={
                "class_id": class_id,
                "error": str(e),
            },
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the fitness class"
        ) from e

@router.get("/classes/availability/{class_id}", tags=["Classes"])
async def check_class_availability(
    request: Request,
    class_id: int,
    timezone: str = Query(
        DEFAULT_TIMEZONE,
        description="Timezone for the response",
        regex=TIMEZONE_PATTERN,
        example=DEFAULT_TIMEZONE
    ),
    db: Session = Depends(get_db)
):
    logger.info(
        "Checking class availability",
        extra={
            "class_id": class_id,
            "timezone": timezone,
            "client": request.client.host if request.client else None,
        },
    )
    
    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError as e:
        logger.error(INVALID_TIMEZONE_MSG, extra={"timezone": timezone, "error": str(e)})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone: {timezone}"
        ) from e
    
    try:
        # Get the class with a lock to prevent concurrent modifications
        db_class = (db.query(FitnessClass)
                   .filter(FitnessClass.id == class_id)
                   .with_for_update(read=True)  # Use read lock for better concurrency
                   .first())
        
        if not db_class:
            logger.warning("Class not found for availability check", extra={"class_id": class_id})
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CLASS_NOT_FOUND_MSG
            )
        
        current_time = datetime.now(pytz.UTC)
        is_available = (
            db_class.available_slots > 0 and
            db_class.start_time > current_time
        )
        
        availability_info = {
            "class_id": db_class.id,
            "class_name": db_class.name,
            "start_time": db_class.start_time.astimezone(tz).isoformat(),
            "end_time": db_class.end_time.astimezone(tz).isoformat() if db_class.end_time else None,
            "available_slots": db_class.available_slots,
            "total_capacity": db_class.capacity,
            "is_available": is_available,
            "next_available_time": None,
            "time_until_start": (db_class.start_time - current_time).total_seconds() if db_class.start_time > current_time else 0,
            "timezone": timezone,
        }
        
        logger.info(
            "Class availability checked",
            extra={
                "class_id": class_id,
                "is_available": is_available,
                "available_slots": db_class.available_slots,
            },
        )
        
        return availability_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to check class availability",
            exc_info=True,
            extra={
                "class_id": class_id,
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking class availability"
        ) from e

@router.get("/classes", response_model=List[FitnessClassInDB], tags=["Classes"])
async def list_classes(
    request: Request,
    timezone: str = Query(
        DEFAULT_TIMEZONE,
        description="Timezone for displaying class times",
        regex=TIMEZONE_PATTERN,
        example=DEFAULT_TIMEZONE
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    List all upcoming fitness classes.
    
    - **timezone**: Timezone for displaying class times (e.g., 'America/New_York', 'Asia/Kolkata')
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (max 1000)
    """
    try:
        logger.info(
            "Listing fitness classes",
            extra={
                "timezone": timezone,
                "skip": skip,
                "limit": limit,
                "client": request.client.host if request.client else None,
            },
        )
        
        # Validate timezone
        if timezone not in pytz.all_timezones:
            logger.error(INVALID_TIMEZONE_MSG, extra={"timezone": timezone})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{INVALID_TIMEZONE_MSG}. Must be one of: {', '.join(pytz.common_timezones)}"
            )
        
        current_time = datetime.now(pytz.UTC)  # Compare with UTC time in database
        
        # Query upcoming classes
        query = db.query(FitnessClass)
        query = query.filter(FitnessClass.start_time >= current_time)
        query = query.order_by(FitnessClass.start_time)
        query = query.offset(skip).limit(limit)
        classes = query.all()
        
        # Set timezone for response
        for cls in classes:
            cls.timezone = timezone
        
        logger.info(
            "Successfully listed fitness classes",
            extra={
                "num_classes": len(classes),
            },
        )
        
        return classes
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        logger.error(
            "Error listing fitness classes",
            exc_info=True,
            extra={
                "error": str(e),
                "timezone": timezone,
                "skip": skip,
                "limit": limit,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving fitness classes"
        )

@router.post("/book", response_model=BookingInDB, status_code=status.HTTP_201_CREATED, tags=["Bookings"])
def book_class(
    request: Request,
    booking: BookingCreate,
    timezone: str = Query(
        DEFAULT_TIMEZONE,
        description="Timezone for the booking response",
        regex=TIMEZONE_PATTERN,
        example=DEFAULT_TIMEZONE
    ),
    db: Session = Depends(get_db)
) -> BookingInDB:
    """Book a fitness class.
    
    Args:
        request: The incoming request object
        booking: The booking details
        timezone: Timezone for the response
        db: Database session
        
    Returns:
        The created booking
    """
    logger.info(
        "Booking a fitness class",
        extra={
            "class_id": booking.fitness_class_id,
            "client_email": booking.client_email,
            "client": request.client.host if request.client else None,
        },
    )
    
    try:
        # Check if class exists and has available slots
        db_class = (
            db.query(FitnessClass)
            .filter(
                FitnessClass.id == booking.fitness_class_id,
                FitnessClass.available_slots > 0
            )
            .with_for_update()  # Lock the row for update
            .first()
        )
        
        if not db_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=NO_AVAILABLE_SLOTS_MSG
            )
        
        # Check for existing booking with same email
        existing_booking = (
            db.query(Booking)
            .filter(
                Booking.fitness_class_id == booking.fitness_class_id,
                Booking.client_email == booking.client_email.lower()
            )
            .first()
        )
        
        if existing_booking:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=DUPLICATE_BOOKING_MSG
            )
        
        # Create the booking with explicit timestamps
        db_booking = Booking(
            fitness_class_id=booking.fitness_class_id,
            client_name=booking.client_name,
            client_email=booking.client_email.lower(),
            created_at=datetime.now(pytz.UTC),
            updated_at=datetime.now(pytz.UTC)
        )
        
        # Add booking to session
        db.add(db_booking)
        
        # Decrement available slots
        db_class.available_slots -= 1
        
        # Commit the transaction
        db.commit()
        
        # Refresh to get the latest state
        db.refresh(db_booking)
        
        # Eager load the fitness class with all required fields
        db_booking = (
            db.query(Booking)
            .options(joinedload(Booking.fitness_class))
            .filter(Booking.id == db_booking.id)
            .first()
        )
        
        # Set timezone for response
        if db_booking.fitness_class:
            db_booking.fitness_class.timezone = timezone
        
        # Create a new dictionary with all required fields
        response_data = {
            "id": db_booking.id,
            "fitness_class_id": db_booking.fitness_class_id,
            "client_name": db_booking.client_name,
            "client_email": db_booking.client_email,
            "created_at": db_booking.created_at,
            "updated_at": db_booking.updated_at,
            "fitness_class": {
                "id": db_booking.fitness_class.id,
                "name": db_booking.fitness_class.name,
                "description": db_booking.fitness_class.description or "",
                "instructor": db_booking.fitness_class.instructor,
                "start_time": db_booking.fitness_class.start_time,
                "end_time": db_booking.fitness_class.end_time,
                "timezone": timezone,
                "capacity": db_booking.fitness_class.capacity,
                "available_slots": db_booking.fitness_class.available_slots,
                "created_at": getattr(db_booking.fitness_class, 'created_at', datetime.now(pytz.UTC)),
                "updated_at": getattr(db_booking.fitness_class, 'updated_at', datetime.now(pytz.UTC))
            }
        }
        
        try:
            # Convert to Pydantic model to ensure validation
            return BookingInDB.model_validate(response_data)
        except Exception as e:
            logger.error(f"Error validating response data: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing booking response"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing booking: {str(e)}", exc_info=True)
        # The context manager will handle the rollback
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your booking"
        )

@router.get("/bookings", response_model=List[BookingInDB], tags=["Bookings"])
async def list_bookings(
    email: str = Query(..., description="Email address to look up bookings for", example="user@example.com"),
    timezone: str = Query(
        DEFAULT_TIMEZONE,
        description="Timezone for displaying booking times",
        regex=TIMEZONE_PATTERN,
        example=DEFAULT_TIMEZONE
    ),
    upcoming: bool = Query(True, description="Filter for upcoming bookings only"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """
    Get all bookings for a specific email address.
    
    - **email**: Email address to look up bookings for
    - **timezone**: Timezone for displaying booking times (e.g., 'America/New_York', 'Asia/Kolkata')
    - **upcoming**: If True, only return upcoming bookings. If False, return all bookings.
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (max 1000)
    """
    try:
        tz = pytz.timezone(timezone)  # We need the timezone object for datetime conversion
        current_time = datetime.now(tz).astimezone(pytz.UTC) if upcoming else None
    except pytz.UnknownTimeZoneError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid timezone. Must be one of: {', '.join(pytz.common_timezones)}"
        )
    
    # Normalize email (case-insensitive search)
    email = email.lower().strip()
    
    # Base query with eager loading of fitness_class
    query = (db.query(Booking)
            .options(joinedload(Booking.fitness_class))
            .filter(Booking.client_email == email))
    
    # Apply upcoming filter if needed
    if upcoming:
        query = query.join(FitnessClass).filter(FitnessClass.start_time >= current_time)
    
    # Apply pagination and execute query
    bookings = (query.order_by(FitnessClass.start_time)
                .offset(skip)
                .limit(limit)
                .all())
    
    # Set timezone for response and ensure datetimes are timezone-aware
    for booking in bookings:
        booking.fitness_class.timezone = timezone
        booking.created_at = booking.created_at.replace(tzinfo=pytz.UTC) if booking.created_at.tzinfo is None else booking.created_at
        booking.updated_at = booking.updated_at.replace(tzinfo=pytz.UTC) if booking.updated_at.tzinfo is None else booking.updated_at
    
    return bookings
