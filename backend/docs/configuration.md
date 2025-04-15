# Configuration Guide

## Overview

This document describes the configuration options and mechanisms for the Facebook Marketplace Scraper project. The application uses a layered configuration approach, allowing settings to be specified through environment variables, configuration files, and command line arguments.

## Configuration Sources

The system loads configuration from the following sources, in order of precedence (highest to lowest):

1. Command line arguments
2. Environment variables
3. Environment-specific configuration files
4. Default configuration files
5. Hardcoded defaults

## Environment Variables

Environment variables provide a convenient way to configure the application, especially in containerized environments. The most important environment variables are:

### Core Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `ENVIRONMENT` | Deployment environment | `development` | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` |
| `CONFIG_FILE` | Path to configuration file | `config.yaml` | `/etc/marketplace/config.yaml` |

### Database Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/marketplace` | `postgresql://user:password@db.example.com:5432/marketplace` |
| `DB_POOL_SIZE` | Database connection pool size | `5` | `10` |
| `DB_MAX_OVERFLOW` | Maximum overflow connections | `10` | `20` |
| `DB_POOL_TIMEOUT` | Connection timeout in seconds | `30` | `60` |

### Kafka Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka bootstrap servers | `localhost:9092` | `kafka-1:9092,kafka-2:9092` |
| `KAFKA_GROUP_ID` | Consumer group ID | `marketplace-consumer` | `marketplace-processor-group` |
| `KAFKA_AUTO_OFFSET_RESET` | Offset reset policy | `earliest` | `latest` |

### API Service Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `API_HOST` | Host to bind API server | `0.0.0.0` | `127.0.0.1` |
| `API_PORT` | Port to bind API server | `8000` | `8080` |
| `API_WORKERS` | Number of worker processes | `1` | `4` |
| `API_CORS_ORIGINS` | Allowed CORS origins | `*` | `https://app.example.com` |
| `API_RATE_LIMIT_ANONYMOUS` | Rate limit for anonymous users | `30/minute` | `10/minute` |
| `API_RATE_LIMIT_AUTHENTICATED` | Rate limit for authenticated users | `100/minute` | `200/minute` |

### Authentication Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `JWT_SECRET_KEY` | Secret key for JWT tokens | *required* | `your-secret-key` |
| `JWT_ALGORITHM` | Algorithm for JWT tokens | `HS256` | `RS256` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token expiry in minutes | `60` | `30` |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiry in days | `7` | `14` |

### Scraper Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SCRAPER_USER_AGENT` | User agent string for scraper | `Mozilla/5.0...` | `Custom User Agent` |
| `SCRAPER_TIMEOUT` | Request timeout in seconds | `30` | `60` |
| `SCRAPER_MAX_RETRIES` | Maximum retry attempts | `3` | `5` |
| `SCRAPER_CONCURRENCY` | Max concurrent scraping operations | `5` | `10` |
| `SCRAPER_RATE_LIMIT` | Rate limit for scraping operations | `20/minute` | `10/minute` |
| `SCRAPER_PROXY_URL` | Optional proxy URL | `None` | `http://proxy.example.com:8080` |

### Notification Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` | `smtp.sendgrid.net` |
| `SMTP_PORT` | SMTP server port | `587` | `465` |
| `SMTP_USERNAME` | SMTP username | *required* | `apikey` |
| `SMTP_PASSWORD` | SMTP password | *required* | `your-smtp-password` |
| `SMTP_FROM_EMAIL` | From email address | `notifications@example.com` | `alerts@marketplace.example.com` |
| `NOTIFICATIONS_BATCH_SIZE` | Notification batch size | `50` | `100` |

### Monitoring Settings

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `METRICS_PORT` | Prometheus metrics port | `8001` | `9090` |
| `PUSH_GATEWAY_URL` | Prometheus pushgateway URL | `None` | `http://pushgateway:9091` |
| `TRACING_ENABLED` | Enable distributed tracing | `False` | `True` |
| `TRACING_EXPORTER_URL` | OpenTelemetry exporter URL | `None` | `http://jaeger:14268/api/traces` |

## Configuration Files

The application supports YAML configuration files with a hierarchical structure. The default configuration file is located at `config/config.yaml`.

### Example Configuration File

```yaml
# Main configuration file
environment: development

logging:
  level: INFO
  format: json
  output: stdout

database:
  url: postgresql://postgres:postgres@localhost:5432/marketplace
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30

kafka:
  bootstrap_servers: localhost:9092
  group_id: marketplace-consumer
  auto_offset_reset: earliest
  topics:
    listings: marketplace.listings
    alerts: marketplace.alerts
    notifications: marketplace.notifications

api:
  host: 0.0.0.0
  port: 8000
  workers: 1
  cors_origins:
    - http://localhost:3000
    - https://app.example.com
  rate_limit:
    anonymous: 30/minute
    authenticated: 100/minute

auth:
  jwt_algorithm: HS256
  access_token_expire_minutes: 60
  refresh_token_expire_days: 7

scraper:
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  timeout: 30
  max_retries: 3
  concurrency: 5
  rate_limit: 20/minute
  proxy:
    enabled: false
    url: null

notifications:
  email:
    smtp_host: smtp.gmail.com
    smtp_port: 587
    smtp_use_tls: true
    from_email: notifications@example.com
  batch_size: 50
  default_frequency: daily

monitoring:
  metrics_port: 8001
  push_gateway_url: null
  tracing:
    enabled: false
    exporter_url: null
```

### Environment-Specific Configuration

The application supports environment-specific configuration files. These files are loaded based on the `ENVIRONMENT` variable:

- `config/development.yaml`
- `config/staging.yaml`
- `config/production.yaml`

Settings in these files override the default configuration.

## Configuration Loading

The configuration is loaded by the `settings.py` module in the `backend/shared/config/` directory.

### Example Usage

```python
from backend.shared.config.settings import get_settings

# Get settings object
settings = get_settings()

# Access configuration values
database_url = settings.DATABASE_URL
api_port = settings.API_PORT
```

### Settings Validation

The settings are validated using Pydantic models to ensure type safety and validation:

```python
from pydantic import BaseSettings, Field, validator
from typing import List, Optional, Dict, Any

class DatabaseSettings(BaseSettings):
    URL: str = "postgresql://postgres:postgres@localhost:5432/marketplace"
    POOL_SIZE: int = 5
    MAX_OVERFLOW: int = 10
    POOL_TIMEOUT: int = 30
    
    @validator("URL")
    def validate_url(cls, v):
        if not v.startswith("postgresql://"):
            raise ValueError("Database URL must be a PostgreSQL connection string")
        return v

class Settings(BaseSettings):
    # ... other settings
    DATABASE: DatabaseSettings = DatabaseSettings()
    # ... more settings
```

## Configuration in Docker

When running in Docker, configuration is typically provided through environment variables:

```bash
docker run -d \
  --name marketplace-api \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@postgres:5432/marketplace \
  -e KAFKA_BOOTSTRAP_SERVERS=kafka:9092 \
  -e JWT_SECRET_KEY=your-secret-key \
  marketplace-api:latest
```

## Configuration in Kubernetes

In Kubernetes, configuration is provided through ConfigMaps and Secrets:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: marketplace-config
  namespace: marketplace
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  KAFKA_BOOTSTRAP_SERVERS: "kafka-headless.kafka:9092"
  # Other non-sensitive configuration

---
apiVersion: v1
kind: Secret
metadata:
  name: marketplace-secrets
  namespace: marketplace
type: Opaque
data:
  DATABASE_URL: cG9zdGdyZXNxbDovL3VzZXI6cGFzc3dvcmRAcG9zdGdyZXM6NTQzMi9tYXJrZXRwbGFjZQ==  # Base64 encoded
  JWT_SECRET_KEY: eW91ci1zZWNyZXQta2V5  # Base64 encoded
  SMTP_PASSWORD: c210cC1wYXNzd29yZA==  # Base64 encoded
```

## Command Line Arguments

Some services support command line arguments for configuration. These are defined using Python's `argparse` module:

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Marketplace Scraper Service")
    parser.add_argument("--config", help="Path to configuration file", default="config.yaml")
    parser.add_argument("--log-level", help="Logging level", default="INFO")
    parser.add_argument("--concurrency", help="Scraper concurrency", type=int, default=5)
    return parser.parse_args()
```

## Best Practices

1. **Never hardcode sensitive information** in the codebase
2. **Use environment variables** for containerized environments
3. **Provide sensible defaults** for local development
4. **Document all configuration options** with descriptions and examples
5. **Validate configuration** at startup to fail fast if required settings are missing
6. **Use separate configurations** for different environments

## Related Documentation

- [Deployment Guide](deployment.md)
- [Security Documentation](security.md)
- [Architecture Overview](architecture.md)
