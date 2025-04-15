# Architecture Overview

## Introduction

This document outlines the architectural design of the Facebook Marketplace Scraper project. The system is designed to efficiently scrape, process, and deliver marketplace listings to users through a microservices architecture.

## System Architecture

The Facebook Marketplace Scraper is built using a microservices architecture with the following primary services:

1. **API Service** - Handles external requests and user interactions
2. **Scraper Service** - Extracts data from Facebook Marketplace
3. **Processor Service** - Processes and enriches scraped data
4. **Notifications Service** - Delivers alerts and notifications to users

### Architecture Diagram

```
┌────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│                │      │                  │      │                    │
│   API Service  │◄────►│  Scraper Service │◄────►│  Processor Service │
│                │      │                  │      │                    │
└───────┬────────┘      └──────────────────┘      └─────────┬──────────┘
        │                                                   │
        │                                                   │
        │                                                   │
        │                                                   │
        │                                                   │
┌───────▼────────┐      ┌──────────────────┐               │
│                │      │                  │               │
│  Shared DB     │◄────►│  Kafka Cluster   │◄──────────────┘
│                │      │                  │
└───────┬────────┘      └──────┬───────────┘
        │                      │
        │                      │
        │                      │
┌───────▼────────┐      ┌──────▼───────────┐
│                │      │                  │
│  User Portal   │      │ Notifications    │
│                │      │ Service          │
└────────────────┘      └──────────────────┘
```

### Service Responsibilities

#### API Service
- Handles REST API requests from clients
- Manages user authentication and authorization
- Serves listing data and handles search queries
- Creates and manages user alerts
- Provides WebSocket connections for real-time updates

#### Scraper Service
- Orchestrates scheduled scraping jobs
- Implements browser automation for data extraction
- Handles rate limiting and request throttling
- Provides resilience against website changes
- Publishes scraped data to Kafka topics

#### Processor Service
- Consumes raw listing data from Kafka
- Cleanses and normalizes listing data
- Detects duplicate listings and merges information
- Analyzes pricing trends and anomalies
- Enriches listings with additional metadata
- Matches listings against user alerts

#### Notifications Service
- Consumes processed alerts from Kafka
- Manages notification delivery preferences
- Sends emails, SMS, and push notifications
- Handles notification throttling and batching
- Tracks notification delivery status

### Communication Patterns

The system employs two primary communication patterns:

1. **Asynchronous Communication** (Event-Driven)
   - Services communicate via Kafka messages
   - Enables loose coupling between services
   - Provides natural buffering during traffic spikes
   - Facilitates independent scaling of services

2. **Synchronous Communication** (REST API)
   - API service communicates with clients via REST
   - Internal service-to-service communication when immediate response is required
   - Health checks and administrative operations

### Data Flow

1. **Listing Discovery**
   - Scraper Service extracts listings from Facebook Marketplace
   - Raw listings are published to Kafka topic `raw-listings`

2. **Data Processing**
   - Processor Service consumes from `raw-listings`
   - Processed listings are saved to the database
   - Matching alerts are published to `alert-matches`

3. **Notification Delivery**
   - Notifications Service consumes from `alert-matches`
   - Notifications are delivered according to user preferences

4. **User Interaction**
   - Users interact with the system via API Service
   - Real-time updates are pushed via WebSockets

## Design Principles

The architecture adheres to the following key principles:

### Service Independence
- Each service can be developed, deployed, and scaled independently
- Services communicate via well-defined interfaces
- Service failures are isolated and don't cascade

### Eventual Consistency
- The system prioritizes availability over immediate consistency
- Data is eventually consistent across all services
- Compensating transactions handle inconsistencies

### Observability
- Comprehensive logging in structured format
- Distributed tracing across service boundaries
- Metrics collection for performance monitoring
- Centralized monitoring and alerting

### Resilience
- Services implement circuit breakers for external dependencies
- Automatic retries with exponential backoff
- Graceful degradation during partial system failure
- Health checks for all services

## Infrastructure

### Container Orchestration
- Kubernetes manages service deployment and scaling
- Services are packaged as Docker containers
- Horizontal Pod Autoscalers adjust capacity based on load

### Data Storage
- PostgreSQL for relational data (users, accounts, alerts)
- Optionally, MongoDB for listing data (scalability for large datasets)
- Redis for caching and rate limiting

### Message Broker
- Apache Kafka for event streaming
- Multiple topics for different event types
- Consumer groups for load distribution

### Security
- JWT-based authentication
- Role-based access control
- API rate limiting
- Network isolation between services
- Secrets management

## Future Enhancements

The architecture is designed to support the following future enhancements:

1. **Multi-platform Support**
   - Extend scraping to additional marketplace platforms
   - Normalize data across different platforms

2. **Advanced Analytics**
   - Price trend analysis
   - Recommendation engine
   - Fraud detection

3. **High Availability**
   - Multi-region deployment
   - Automated failover
   - Disaster recovery planning

4. **Enhanced Search**
   - Full-text search capabilities
   - Image-based search
   - Semantic search for similar items

## Related Documentation
- [API Documentation](api.md)
- [Deployment Guide](deployment.md)
- [Health Check System](healthcheck.md)
- [Database Schema](database_schema.md)
