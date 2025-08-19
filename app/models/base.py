from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func
from datetime import datetime
import pytz
from sqlalchemy import TypeDecorator

class TZDateTime(TypeDecorator):
    """
    A DateTime type which can only store timezone-aware datetime objects.
    The datetime is stored as UTC in the database.
    """
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, _):
        if value is not None and not value.tzinfo:
            raise ValueError("timezone awareness is required")
        # Convert to UTC before storing
        return value.astimezone(pytz.UTC) if value and value.tzinfo else value

    def process_result_value(self, value, _):
        # Ensure returned datetime is timezone-aware (UTC)
        return value.replace(tzinfo=pytz.UTC) if value and value.tzinfo is None else value

# Create base declarative class first
Base = declarative_base()

# Common columns for all models
class TimestampMixin:
    created_at = Column(TZDateTime, default=lambda: datetime.now(pytz.UTC), nullable=False)
    updated_at = Column(
        TZDateTime, 
        default=lambda: datetime.now(pytz.UTC), 
        onupdate=lambda: datetime.now(pytz.UTC), 
        nullable=False
    )

class BaseModel(TimestampMixin, Base):
    """Base model with common fields and methods"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                # Ensure datetime is timezone-aware for serialization
                if value.tzinfo is None:
                    value = value.replace(tzinfo=pytz.UTC)
                value = value.isoformat()
            result[column.name] = value
        return result
