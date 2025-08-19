from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator, model_validator, FieldValidationInfo
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import pytz
from enum import Enum

# Common timezone string pattern
TIMEZONE_PATTERN = r'^[A-Za-z_]+/[A-Za-z_]+$'
DEFAULT_TIMEZONE = "Asia/Kolkata"

class FitnessClassBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, example="Morning Yoga")
    description: Optional[str] = Field(None, example="A relaxing morning yoga session")
    instructor: str = Field(..., min_length=1, max_length=100, example="Priya Sharma")
    start_time: datetime = Field(..., example="2025-08-19T07:00:00+05:30")
    end_time: datetime = Field(..., example="2025-08-19T08:00:00+05:30")
    timezone: str = Field(DEFAULT_TIMEZONE, pattern=TIMEZONE_PATTERN, example=DEFAULT_TIMEZONE)
    capacity: int = Field(..., gt=0, example=15)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def parse_datetime(cls, v: Any) -> datetime:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("Invalid datetime format. Use ISO 8601 format")
        return v
    
    @field_validator('end_time')
    @classmethod
    def validate_times(cls, v: datetime, info: FieldValidationInfo) -> datetime:
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        if v not in pytz.all_timezones:
            raise ValueError(f'Invalid timezone. Must be one of: {pytz.common_timezones}')
        return v
    
    @model_validator(mode='after')
    def ensure_timezone_awareness(self) -> 'FitnessClassBase':
        timezone_str = self.timezone or 'UTC'
        tz = pytz.timezone(timezone_str)
        
        if self.start_time is not None:
            if self.start_time.tzinfo is None:
                self.start_time = tz.localize(self.start_time)
            else:
                self.start_time = self.start_time.astimezone(tz)
                
        if self.end_time is not None:
            if self.end_time.tzinfo is None:
                self.end_time = tz.localize(self.end_time)
            else:
                self.end_time = self.end_time.astimezone(tz)
        
        return self

class FitnessClassCreate(FitnessClassBase):
    """Schema for creating a new fitness class"""
    pass

class FitnessClassUpdate(BaseModel):
    """Schema for updating a fitness class"""
    name: Optional[str] = Field(None, max_length=100, example="Evening Yoga")
    description: Optional[str] = None
    instructor: Optional[str] = Field(None, max_length=100, example="Rahul Verma")
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: Optional[str] = Field(None, pattern=TIMEZONE_PATTERN, example=DEFAULT_TIMEZONE)
    capacity: Optional[int] = Field(None, gt=0, example=20)
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

class FitnessClassInDB(FitnessClassBase):
    """Schema for fitness class data in the database"""
    id: int
    available_slots: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

class BookingBase(BaseModel):
    """Base schema for booking operations"""
    fitness_class_id: int = Field(..., gt=0, example=1)
    client_name: str = Field(..., min_length=1, max_length=100, example="John Doe")
    client_email: EmailStr = Field(..., example="john.doe@example.com")
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )

class BookingCreate(BookingBase):
    """Schema for creating a new booking"""
    pass

class BookingInDB(BookingBase):
    """Schema for booking data in the database"""
    id: int
    created_at: datetime
    updated_at: datetime
    fitness_class: 'FitnessClassInDB'
    
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
