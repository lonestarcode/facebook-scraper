"""Configuration settings for the application services."""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file if it exists
env_path = Path(__file__).parents[2] / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# Configure logger
logger = logging.getLogger("config")

class KafkaTopicsConfig(BaseModel):
    """Configuration for Kafka topics."""
    raw_listings: str = Field(default="marketplace.listings.raw")
    processed_listings: str = Field(default="marketplace.listings.processed")
    alerts: str = Field(default="marketplace.alerts")
    notifications: str = Field(default="marketplace.notifications")


class KafkaConfig(BaseModel):
    """Configuration for Kafka."""
    bootstrap_servers: str = Field(default="localhost:9092")
    group_id: str = Field(default="facebook-scraper")
    topics: KafkaTopicsConfig = Field(default_factory=KafkaTopicsConfig)
    auto_offset_reset: str = Field(default="earliest")
    enable_auto_commit: bool = Field(default=True)
    auto_commit_interval_ms: int = Field(default=5000)


class DatabaseConfig(BaseModel):
    """Configuration for database."""
    url: str = Field(default="sqlite:///./facebook_marketplace.db")
    echo_sql: bool = Field(default=False)
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)


class ScraperConfig(BaseModel):
    """Configuration for scraper service."""
    interval_seconds: int = Field(default=3600)  # 1 hour
    search_terms: List[str] = Field(default_factory=list)
    search_radius_miles: int = Field(default=50)
    location: Optional[str] = Field(default=None)
    max_listings_per_search: int = Field(default=50)
    delay_between_requests: float = Field(default=2.0)
    cycle_delay_seconds: int = Field(default=3600)  # 1 hour
    
    @validator('search_terms', pre=True)
    def parse_search_terms(cls, v):
        """Parse search terms from string or list."""
        if isinstance(v, str):
            return [term.strip() for term in v.split(',') if term.strip()]
        return v


class ProcessorConfig(BaseModel):
    """Configuration for processor service."""
    batch_size: int = Field(default=100)
    analysis_enabled: bool = Field(default=True)
    alert_matching_enabled: bool = Field(default=True)
    keyword_extraction_enabled: bool = Field(default=True)


class APIConfig(BaseModel):
    """Configuration for API service."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    workers: int = Field(default=4)
    allow_origins: List[str] = Field(default_factory=lambda: ["*"])
    api_prefix: str = Field(default="/api/v1")
    auth_enabled: bool = Field(default=True)
    rate_limit_enabled: bool = Field(default=True)
    rate_limit: int = Field(default=100)  # requests per minute


class NotificationsConfig(BaseModel):
    """Configuration for notifications service."""
    smtp_server: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    sender_email: str = Field(default="")
    default_recipient_email: Optional[str] = Field(default=None)


class ObservabilityConfig(BaseModel):
    """Configuration for logging and monitoring."""
    log_level: str = Field(default="INFO")
    json_logs: bool = Field(default=True)
    log_file: Optional[str] = Field(default=None)
    metrics_enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    tracing_enabled: bool = Field(default=False)
    tracing_host: str = Field(default="localhost")
    tracing_port: int = Field(default=6831)


class Settings(BaseSettings):
    """Application settings."""
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # General settings
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    service_name: str = Field(default="")  # Will be set per service
    
    # Component-specific configurations
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    scraper: ScraperConfig = Field(default_factory=ScraperConfig)
    processor: ProcessorConfig = Field(default_factory=ProcessorConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    
    @validator('service_name', pre=True, always=True)
    def set_service_name(cls, v):
        """Set service name based on environment variable if not provided."""
        if v:
            return v
            
        # Try to get service name from environment variable
        return os.getenv('SERVICE_NAME', 'facebook-marketplace-scraper')

    class Config:
        env_prefix = "APP_"
        env_nested_delimiter = "__"


def get_settings(service_name: str = None) -> Settings:
    """
    Get application settings.
    
    Args:
        service_name: Optional service name to set
        
    Returns:
        Application settings
    """
    settings = Settings()
    
    if service_name:
        settings.service_name = service_name
        
    return settings


def load_settings(config_path: Optional[str] = None) -> Settings:
    """
    Load application settings from YAML configuration file and environment variables.
    
    Args:
        config_path: Path to YAML configuration file
        
    Returns:
        Application settings
    """
    # Default config path
    if not config_path:
        config_dir = os.environ.get("CONFIG_DIR", "./config")
        env = os.environ.get("ENVIRONMENT", "development")
        config_path = f"{config_dir}/{env}.yaml"
    
    # Load configuration from YAML if it exists
    config_data = {}
    config_file = Path(config_path)
    
    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                config_data = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration file {config_path}: {str(e)}")
    else:
        logger.warning(f"Configuration file {config_path} not found, using defaults and environment variables")
    
    # Override with environment variables
    # Example: DATABASE_URL environment variable would override database.url in YAML
    for key, value in os.environ.items():
        if key.isupper() and "__" not in key:
            parts = key.lower().split("_")
            
            # Skip non-configuration environment variables
            if len(parts) < 2:
                continue
                
            # Handle nested configuration
            current = config_data
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Set the value
            current[parts[-1]] = value
    
    # Validate and create settings object
    try:
        return Settings(**config_data)
    except Exception as e:
        logger.error(f"Error validating configuration: {str(e)}")
        raise


# Singleton instance of settings
_app_settings: Optional[Settings] = None


def get_settings(service_name: str) -> Settings:
    """
    Get settings for a specific service.
    
    Args:
        service_name: Name of the service (api, scraper, processor, notifications)
        
    Returns:
        Service-specific settings
    """
    global _app_settings
    
    if _app_settings is None:
        _app_settings = load_settings()
    
    if service_name == "api":
        return _app_settings.api
    elif service_name == "scraper":
        return _app_settings.scraper
    elif service_name == "processor":
        return _app_settings.processor
    elif service_name == "notifications":
        return _app_settings.notifications
    else:
        raise ValueError(f"Unknown service: {service_name}")


def get_environment() -> str:
    """
    Get the current environment.
    
    Returns:
        Environment name (development, staging, production)
    """
    return os.environ.get("ENVIRONMENT", "development")


def is_development() -> bool:
    """
    Check if the current environment is development.
    
    Returns:
        True if development, False otherwise
    """
    return get_environment() == "development"


def is_production() -> bool:
    """
    Check if the current environment is production.
    
    Returns:
        True if production, False otherwise
    """
    return get_environment() == "production" 