from pydantic_settings import BaseSettings
from datetime import datetime
import pytz

from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "Fitness Studio Booking API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Database
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./fitness_studio.db"
    
    # Timezone settings
    TIMEZONE: str = "Asia/Kolkata"  # IST timezone
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = "logs/app.log"
    LOG_FORMAT: str = "json"  # or 'text'
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        
    @property
    def log_config(self) -> dict:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "json": {
                    "()": "app.core.logger.JSONFormatter",
                },
                "text": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "json" if self.LOG_FORMAT == "json" else "text",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json" if self.LOG_FORMAT == "json" else "text",
                    "filename": str(self.BASE_DIR / self.LOG_FILE) if self.LOG_FILE else None,
                    "maxBytes": 10485760,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf8"
                }
            },
            "loggers": {
                "fitness_studio": {
                    "handlers": ["console", "file"] if self.LOG_FILE else ["console"],
                    "level": self.LOG_LEVEL,
                    "propagate": True
                },
                "sqlalchemy": {
                    "handlers": ["console", "file"] if self.LOG_FILE else ["console"],
                    "level": "WARNING",
                    "propagate": False
                },
                "uvicorn": {
                    "handlers": ["console", "file"] if self.LOG_FILE else ["console"],
                    "level": "INFO",
                    "propagate": False
                }
            }
        }

settings = Settings()

# Set the default timezone
DEFAULT_TIMEZONE = pytz.timezone(settings.TIMEZONE)
CURRENT_DATETIME = datetime.now(DEFAULT_TIMEZONE)
