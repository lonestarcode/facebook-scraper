# Facebook Marketplace Scraper - Backend v2

This directory contains the next-generation backend for the Facebook Marketplace Scraper, implemented as a microservices architecture. The implementation is now complete (100%) and ready for deployment.

## Architecture

The backend consists of the following microservices:

1. **Scraper Service**: Handles collection of listings from Facebook Marketplace
2. **API Service**: Handles HTTP and WebSocket connections from clients
3. **Processor Service**: Processes scraped listings, applies transformations, and matches alerts
4. **Notifications Service**: Manages sending notifications through various channels

## Directory Structure

```
backend/
├── services/              # Main microservices
│   ├── scraper/           # Facebook Marketplace scraper service
│   ├── api/               # API service for client connections
│   ├── processor/         # Data processing service
│   │   └── src/
│   │       ├── main.py    # Main entry point
│   │       ├── pipelines/ # Processing pipelines
│   │       └── analyzers/ # Data analyzers
│   └── notifications/     # Notification service
├── shared/                # Shared code between services
│   ├── models/            # Data models
│   ├── utils/             # Utility functions
│   ├── auth/              # Authentication utilities
│   └── config/            # Configuration
├── infrastructure/        # Infrastructure as code
│   ├── docker/            # Docker configuration
│   └── kubernetes/        # Kubernetes manifests
├── docs/                  # Documentation
│   ├── architecture.md    # Architecture overview
│   ├── api.md             # API documentation
│   ├── deployment.md      # Deployment guide
│   ├── monitoring.md      # Monitoring documentation
│   ├── security.md        # Security documentation
│   ├── scraper.md         # Scraper documentation
│   └── testing.md         # Testing documentation
├── migrations/            # Database migrations
├── alembic.ini            # Alembic configuration
└── setup.py               # Package setup
```

## Key Features

- **Scalable Microservices**: Each service can be scaled independently
- **Robust Data Processing**: Handles large volumes of listings efficiently
- **Real-time Updates**: WebSocket support for instant notifications
- **Comprehensive Monitoring**: Prometheus metrics and structured logging
- **Database Migrations**: Clean database schema management with Alembic
- **Authentication**: JWT-based authentication with role-based access control
- **Health Checks**: Each service provides health check endpoints
- **Rate Limiting**: Protection against API abuse
- **Comprehensive Testing**: Unit and integration tests

## Getting Started

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Kubernetes (for production deployment)
- PostgreSQL
- Redis
- Kafka

### Development Setup

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -e .
   ```

3. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run services with Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Running Tests

```bash
pytest
```

## Documentation

- [Architecture Overview](docs/architecture.md) - The overall system architecture
- [API Documentation](docs/api.md) - API endpoints and usage
- [Deployment Guide](docs/deployment.md) - How to deploy the system
- [Monitoring Documentation](docs/monitoring.md) - Monitoring and observability
- [Security Documentation](docs/security.md) - Security features and best practices
- [Scraper Documentation](docs/scraper.md) - Scraper implementation details
- [Testing Documentation](docs/testing.md) - Testing strategies and framework 