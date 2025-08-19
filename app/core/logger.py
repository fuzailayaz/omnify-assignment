import logging
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import json
import traceback

class JSONFormatter(logging.Formatter):    
    def format(self, record):
        log_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        # Add stack trace if debug
        if record.levelno >= logging.ERROR:
            log_record['stack_trace'] = traceback.format_stack()
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logger(
    name: str,
    log_level: str = 'INFO',
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup a logger with both console and file handlers.
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    json_formatter = JSONFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    # File handler if path is provided
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    
    return logger

# Create a default application logger
logger = setup_logger(
    'fitness_studio',
    log_level='INFO',
    log_file='logs/app.log'
)

def log_exception(logger: logging.Logger, message: str, exc_info=None, extra: Optional[dict] = None):
    """Helper function to log exceptions with stack trace"""
    extra = extra or {}
    exc_type, exc_value, exc_traceback = exc_info or (None, None, None)
    
    logger.error(
        message,
        exc_info=(exc_type, exc_value, exc_traceback),
        extra=extra,
        stack_info=True
    )
