from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.config import settings
import logging
from contextlib import contextmanager
from typing import Generator, Optional, TypeVar, Any

# Get logger
logger = logging.getLogger(__name__)

# Import models to ensure they are registered with SQLAlchemy
from app.models.base import Base
from app.models.classes import FitnessClass, Booking  # noqa

# Configure SQLAlchemy engine with connection pooling
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=300,    # Recycle connections after 5 minutes
    echo=settings.DEBUG, # Log SQL queries in debug mode
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=True,
)

Base = declarative_base()

# Configure SQLAlchemy logging
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, params, context, executemany):
    """Log SQL queries in debug mode"""
    if settings.DEBUG:
        logger.debug(
            "SQL Query",
            extra={
                "statement": statement,
                "params": params,
                "executemany": executemany,
            },
        )

@event.listens_for(engine, "handle_error")
def handle_db_error(exception_context):
    """Log database errors"""
    exc_info = exception_context.original_exception
    if exc_info:
        logger.error(
            "Database error",
            exc_info=exc_info,
            extra={
                "statement": exception_context.statement,
                "params": exception_context.parameters or {},
                "is_disconnect": exception_context.is_disconnect,
            },
        )

def get_db() -> Generator[Session, None, None]:
    """Dependency for getting DB session with proper cleanup.
    
    Yields:
        Session: A database session that will be automatically closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise
    finally:
        db.close()
