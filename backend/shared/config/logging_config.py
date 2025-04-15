"""
Logging configuration for the Facebook Marketplace Scraper microservices.
Provides structured JSON logging for production and formatted logs for development.
"""
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from .settings import get_settings


class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {}
        
        # Standard log record attributes
        log_record["timestamp"] = self.formatTime(record)
        log_record["level"] = record.levelname
        log_record["name"] = record.name
        log_record["message"] = record.getMessage()
        
        # Include exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Include any custom attributes added to the log record
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno",
                          "lineno", "module", "msecs", "message", "msg", 
                          "name", "pathname", "process", "processName", 
                          "relativeCreated", "stack_info", "thread", "threadName"]:
                log_record[key] = value
        
        return json.dumps(log_record)


def setup_logging(service_name: str, log_level: Optional[str] = None) -> None:
    """
    Set up logging for the given service.
    
    Args:
        service_name: Name of the service (api, scraper, processor, notifications)
        log_level: Optional log level to override the one in settings
    """
    settings = get_settings(service_name)
    
    # Get log level from parameters, settings, or default to INFO
    log_level = log_level or settings.log_level or "INFO"
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(numeric_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Use different formatters based on environment
    if settings.environment == "production":
        # JSON formatter for production
        formatter = JSONFormatter()
    else:
        # More readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set logging level for specific modules
    if settings.environment == "development":
        # Set SQLAlchemy logging to WARNING to reduce noise in development
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("kafka").setLevel(logging.WARNING)
    
    # Log initial message with service info
    logger = logging.getLogger(service_name)
    logger.info(
        f"Logging initialized for {service_name}",
        extra={
            "service": service_name,
            "environment": settings.environment,
            "version": settings.version
        }
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    Adds service context to the logger if available.
    
    Args:
        name: Name for the logger
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Add service info from environment if available
    service_name = os.environ.get("SERVICE_NAME")
    if service_name:
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.service = service_name
            return record
            
        logging.setLogRecordFactory(record_factory)
    
    return logger 