import json
import logging
import sys
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    """Formatter that outputs JSON strings after parsing the log record."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "service": self.service_name,
            "path": record.pathname,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)

        return json.dumps(log_data)


def configure_logging(
    service_name: str,
    log_level: int = logging.INFO,
    use_json: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure logging for the application.

    Args:
        service_name: Name of the service for identification in logs
        log_level: The logging level (default: INFO)
        use_json: Whether to use JSON formatting (default: True)
        log_file: Optional file path to write logs to
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)

    # Set formatter for all handlers
    if use_json:
        formatter = JsonFormatter(service_name)
    else:
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] [%(service)s] - %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Set default logging context for all loggers
    logging.LoggerAdapter = LoggerAdapter


class LoggerAdapter(logging.LoggerAdapter):
    """Adapter for adding extra fields to logs."""
    
    def __init__(self, logger, extra=None):
        """Initialize with a logger and optional extra dict."""
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        """Process the logging message and keyword arguments."""
        kwargs.setdefault("extra", {}).update(self.extra)
        return msg, kwargs


def get_logger(name: str, extra: Optional[Dict[str, Any]] = None) -> logging.LoggerAdapter:
    """
    Get a configured logger with optional extra context.

    Args:
        name: Name of the logger
        extra: Extra fields to include in log records

    Returns:
        A configured logger adapter
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, extra or {}) 