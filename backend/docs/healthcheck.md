# Health Check System

## Overview

This document describes the health check system implemented across all microservices in the Facebook Marketplace Scraper project. The health check system provides a standardized way to monitor service health, expose status endpoints for orchestration platforms, and integrate with monitoring systems.

## Architecture

The health check system consists of:

1. **Service-specific health implementations** - Each service has a `health_setup.py` file that defines its components and health check endpoints
2. **Shared health utilities** - Common code in `shared/utils/health.py` providing base functionality
3. **Monitoring integration** - Prometheus metrics exposed via `shared/utils/monitoring.py`
4. **Deployment integration** - Docker HEALTHCHECK commands and Kubernetes probes

## Health Check Endpoints

All services expose the following HTTP endpoints:

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/health` | Complete health status | Detailed JSON with component status |
| `/health/ready` | Readiness probe | 200 OK if ready, 503 if not |
| `/health/live` | Liveness probe | 200 OK if alive, 503 if not |
| `/health/status` | Component status | JSON object with component states |

## Service-Specific Components

Each service monitors different components based on its dependencies:

### API Service
- `service`: Core API service
- `database`: Database connection
- `auth-provider`: Authentication service
- `rate-limiter`: Rate limiting functionality
- `processor-service`: Connection to Processor service
- `scraper-service`: Connection to Scraper service

### Processor Service
- `service`: Core processor service
- `database`: Database connection
- `kafka-consumer`: Kafka consumer connection
- `kafka-producer`: Kafka producer connection
- `scraper-service`: Connection to Scraper service

### Scraper Service
- `service`: Core scraper service
- `database`: Database connection
- `kafka-producer`: Kafka producer connection
- `browser-engine`: Chrome/Selenium WebDriver
- `rate-limiter`: Rate limiting functionality

### Notifications Service
- `service`: Core notifications service
- `database`: Database connection
- `kafka-consumer`: Kafka consumer connection
- `email-sender`: Email service connection
- `sms-sender`: SMS service connection

## Implementation Details

### Health Status Model

The health check system uses a consistent status model across all services:

```python
class HealthStatus(BaseModel):
    status: str = "ok"                  # overall status: "ok", "degraded", or "error"
    version: str = os.getenv("VERSION", "2.0.0")  # service version
    service: str = "service-name"       # service name
    checks: Dict[str, bool] = {}        # component status map
    details: Dict[str, str] = {}        # component status details
```

### Health Check Manager

Each service implements a `HealthCheck` class that:

1. Initializes with service-specific components
2. Manages component status
3. Provides methods to check if the service is healthy, ready, and alive
4. Tracks uptime and detailed status information

```python
class HealthCheck:
    """Health check manager for the service"""
    
    def __init__(self, service_name: str):
        # Initialize with service-specific components
        self.checks = {
            "service": True,         # Always starts as true
            "database": False,       # External dependencies start as false
            # Service-specific components...
        }
        self.details = { ... }       # Status details
        self.start_time = time.time()
    
    def set_component_status(self, component: str, status: bool, details: str) -> None:
        # Update component status with details
    
    def get_health(self) -> HealthStatus:
        # Return overall health status
    
    def is_healthy(self) -> bool:
        # Check if all components are healthy
    
    def is_ready(self) -> bool:
        # Check if required components are healthy
    
    def is_alive(self) -> bool:
        # Check if core service is healthy
```

### Health Check Logic

Each service implements specific health check logic:

- **Is Healthy**: All components are operational (true only if all checks pass)
- **Is Ready**: Critical components required to handle requests are operational
- **Is Alive**: Core service component is operational (basic service health)

### Implemented Service Endpoints

All services expose standardized health check endpoints:

```python
# Main health status endpoint
@app.get("/health", tags=["Health"])
async def health():
    """Get the health status of the service"""
    health_status = health_check.get_health()
    return health_status

# Readiness probe endpoint
@app.get("/health/ready", tags=["Health"])
async def ready(response: Response):
    """Check if the service is ready to handle requests"""
    is_ready = health_check.is_ready()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": is_ready, "uptime": health_check.uptime()}

# Liveness probe endpoint
@app.get("/health/live", tags=["Health"])
async def live(response: Response):
    """Check if the service is alive"""
    is_alive = health_check.is_alive()
    if not is_alive:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"alive": is_alive, "uptime": health_check.uptime()}

# Component status endpoint
@app.get("/health/component/{component}", tags=["Health"])
async def component_status(component: str):
    """Get the status of a specific component"""
    # Return status of specific component
```

### Docker Integration

All service Dockerfiles include health checks:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health/live || exit 1
```

### Kubernetes Integration

Kubernetes deployments include readiness and liveness probes:

```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8080
  initialDelaySeconds: 20
  periodSeconds: 15
  timeoutSeconds: 5
livenessProbe:
  httpGet:
    path: /health/live
    port: 8080
  initialDelaySeconds: 40
  periodSeconds: 30
  timeoutSeconds: 5
```

## Usage

### Checking Service Health Manually

To check a service's health:

```bash
curl http://service-host:8080/health
```

Example response:

```json
{
  "status": "degraded",
  "version": "2.0.0",
  "service": "api-service",
  "checks": {
    "service": true,
    "database": true,
    "auth-provider": false,
    "rate-limiter": true
  },
  "details": {
    "environment": "production",
    "healthy": false,
    "ready": true,
    "alive": true
  }
}
```

### Updating Component Status

Services update component status when connections are established or lost:

```python
# On successful database connection
health_check.set_status("database", True)

# On failed connection
health_check.set_status("database", False)
```

## Monitoring

### Prometheus Integration

Health metrics are exported to Prometheus:

- `service_health{service="service_name"}`: Overall service health (1=healthy, 0=unhealthy)
- Component-specific metrics for detailed monitoring

### Logging

Component status changes are logged:

```
INFO - Health check component database set to True
INFO - Health check endpoints configured: /health, /ready, /live
```

## Security Considerations

Health endpoints provide system information and should be:

1. Protected from public access or exposure
2. Rate-limited to prevent DoS attacks
3. Secured according to your organization's requirements

## Best Practices

1. Keep critical component list minimal
2. Update health status promptly on failures
3. Test failure scenarios to ensure proper status reporting
4. Use health checks to implement circuit breakers
5. Include version information for debugging

## Troubleshooting

If health checks are failing:

1. Check logs for specific component errors
2. Verify external dependencies (database, Kafka, etc.)
3. Inspect network connectivity between services
4. Check for resource constraints (CPU, memory)

For detailed implementation, refer to:
- `backend/services/*/src/health_setup.py` - Service-specific implementations
- `backend/shared/utils/health.py` - Shared health utilities
- Deployment configuration in `backend/infrastructure/kubernetes/deployment.yaml`
