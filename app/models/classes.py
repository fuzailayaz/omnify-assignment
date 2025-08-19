from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Index, Text, CheckConstraint
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func
from app.models.base import Base, TZDateTime
from datetime import datetime
import pytz

class FitnessClass(Base):
    """Model for fitness classes"""
    __tablename__ = "fitness_classes"
    __table_args__ = (
        # Ensure end time is after start time
        Index('idx_fitness_class_times', 'start_time', 'end_time'),
    )

    id = Column(Integer, primary_key=True, index=True)  # Explicitly include id
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    instructor = Column(String(100), nullable=False, index=True)
    start_time = Column(TZDateTime, nullable=False, index=True)
    end_time = Column(TZDateTime, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_slots = Column(Integer, nullable=False, index=True)
    timezone = Column(String(50), default='UTC', nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    bookings = relationship(
        "Booking", 
        back_populates="fitness_class", 
        cascade="all, delete-orphan",
        lazy='selectin'  # Eager load bookings when loading a fitness class
    )
    
    @validates('start_time', 'end_time')
    def validate_times(self, key, value):
        if value is None:
            raise ValueError(f"{key} cannot be None")
        if not value.tzinfo:
            raise ValueError(f"{key} must be timezone-aware")
            
        # Convert to UTC for consistent storage
        value = value.astimezone(pytz.UTC)
        
        # Additional validation for end_time
        if key == 'end_time' and hasattr(self, 'start_time') and self.start_time and value <= self.start_time:
            raise ValueError("End time must be after start time")
            
        return value
    
    @validates('capacity', 'available_slots')
    def validate_capacity(self, key, value):
        if value is not None and value < 0:
            raise ValueError(f"{key} cannot be negative")
            
        # Only validate capacity vs available_slots if both are set
        if (key == 'capacity' and hasattr(self, 'available_slots') and 
            self.available_slots is not None and value is not None and 
            value < self.available_slots):
            raise ValueError("Capacity cannot be less than available slots")
            
        # If setting available_slots, ensure it doesn't exceed capacity
        if (key == 'available_slots' and hasattr(self, 'capacity') and 
            self.capacity is not None and value is not None and 
            value > self.capacity):
            raise ValueError("Available slots cannot exceed capacity")
            
        return value
    
    def __repr__(self):
        return f"<FitnessClass {self.id}: {self.name} by {self.instructor}>"


class Booking(Base):
    """Model for class bookings"""
    __tablename__ = "bookings"
    __table_args__ = (
        # Prevent duplicate bookings for the same email and class
        Index('idx_booking_email_class', 'client_email', 'fitness_class_id', unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)  # Explicitly include id
    fitness_class_id = Column(Integer, ForeignKey("fitness_classes.id", ondelete="CASCADE"), nullable=False)
    client_name = Column(String(100), nullable=False)
    client_email = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    fitness_class = relationship(
        "FitnessClass", 
        back_populates="bookings",
        lazy='joined'  # Always load the related fitness class
    )
    
    @validates('client_email')
    def validate_email(self, key, email):
        if '@' not in email:
            raise ValueError("Invalid email format")
        return email.lower().strip()
    
    def __repr__(self):
        return f"<Booking {self.id}: {self.client_name} for class {self.fitness_class_id}>"
