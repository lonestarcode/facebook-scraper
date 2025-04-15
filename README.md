# FACEBOOK MARKETPLACE SCRAPER

A comprehensive solution for scraping, monitoring, and analyzing Facebook Marketplace listings with real-time notifications and a modern web interface.

## Project Structure

This project is organized into two main components:

- **`/backend`** - Python-based scraper, API, and data processing pipeline
- **`/frontend`** - Next.js web application for visualizing and interacting with the data

## Features

### 1. Flexible Category Monitoring
System is designed to monitor any marketplace category. The search functionality allows:
- Keyword-based searching across all categories
- Price range filtering
- Location-based filtering
- Age-based sorting and filtering

### 2. Anti-Detection Measures
The system implements sophisticated anti-detection strategies:
- Dynamic request delays
- Multiple fallback methods
- Session management
- Rate limiting
- Automatic error recovery

### 3. Reliable Data Collection
The pipeline ensures reliable data collection through:
- Multiple scraping methods with automatic fallbacks
- Comprehensive error handling
- Data validation
- Automatic retries
- Session management

### 4. Scalability & Maintenance
The codebase is built for long-term maintainability:
- Modular architecture
- Clear separation of concerns
- Comprehensive error logging
- Performance monitoring
- Easy configuration

### 5. Real-Time Notifications
The system provides multiple ways to stay updated:
- Email alerts for specific criteria
- WebSocket connections for instant updates
- Webhook support for custom integrations
- Price threshold notifications

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.9+ (for backend development)
- Node.js 16+ (for frontend development)

### Running with Docker
The easiest way to run the entire stack is with Docker Compose:

```bash
docker-compose up
```

This will start:
- Backend API (port 8000)
- Frontend web application (port 3000)
- PostgreSQL database
- Prometheus for metrics
- Grafana for monitoring

### Development Setup

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Technical Architecture

### Backend Components
- **Scraper Modules**: Different strategies for collecting data
- **API Layer**: FastAPI endpoints for data access
- **Data Pipeline**: Processing and enrichment
- **Database**: SQLAlchemy ORM with PostgreSQL
- **Monitoring**: Prometheus metrics and logging

### Frontend Components
- **Next.js App**: Modern React application with server-side rendering
- **Mantine UI**: Beautiful component library
- **Real-time Updates**: WebSocket integration
- **Data Fetching**: SWR for efficient data loading
- **TypeScript**: Type-safe development

## Contributing
See the contribution guidelines in each subfolder:
- [Backend Contribution Guide](backend/README.md)
- [Frontend Contribution Guide](frontend/README.md)


## Key Technical Advantages

1. **Flexible Search System**
   - Multi-keyword support
   - Category-agnostic design
   - Combined filters (price, age, location)
   - Sort by various criteria

2. **Smart Notification System**
   - Multiple notification channels
   - Customizable alert criteria
   - Real-time and batch notifications
   - Delivery confirmation

3. **Robust Error Handling**
   - Automatic recovery
   - Multiple fallback methods
   - Detailed error logging
   - Rate limit management

4. **Performance Monitoring**
   - Request tracking
   - Success rate monitoring
   - Response time tracking
   - Error rate monitoring

## Future-Proof Foundation

The system is designed to be easily extended:
1. Add new categories without code changes
2. Implement new notification methods
3. Add new search criteria
4. Integrate with other systems via webhooks
5. Scale horizontally as needed

## Compliance & Reliability

The system is built with platform compliance in mind:
- Respects rate limits
- Implements reasonable delays
- Uses only public data
- Maintains natural request patterns

