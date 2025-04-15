# Monitoring Documentation

## Overview

This document outlines the monitoring and observability strategy for the Facebook Marketplace Scraper backend. It covers metrics collection, logging, alerting, and visualization tools used to ensure system health and performance.

## Monitoring Architecture

The monitoring system follows a multi-layered approach:

1. **Application Instrumentation**: Code-level metrics and logs
2. **Service Monitoring**: Health checks and containerized service metrics
3. **Infrastructure Monitoring**: Host-level metrics and cloud resource utilization
4. **Synthetic Monitoring**: Automated testing of critical paths

## Metrics Collection

### Prometheus Metrics

The system uses Prometheus for metrics collection. Core metrics are defined in `backend/shared/utils/monitoring.py`:

```python
# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total count of HTTP requests',
    ['service', 'endpoint', 'method', 'status_code']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['service', 'endpoint', 'method'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Database metrics
DB_OPERATION_COUNT = Counter(
    'db_operations_total',
    'Total count of database operations',
    ['service', 'operation', 'table', 'status']
)

DB_OPERATION_LATENCY = Histogram(
    'db_operation_duration_seconds',
    'Database operation latency in seconds',
    ['service', 'operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

# Scraper-specific metrics
SCRAPE_COUNTER = Counter(
    'scrapes_total',
    'Total count of scraping operations',
    ['scraper', 'status', 'reason']
)

SCRAPE_DURATION = Histogram(
    'scrape_duration_seconds',
    'Duration of scraping operations',
    ['scraper'],
    buckets=(1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

PROCESSING_ERRORS = Counter(
    'processing_errors_total',
    'Total count of processing errors',
    ['service', 'processor', 'error_type']
)

# Kafka metrics
KAFKA_MESSAGE_COUNT = Counter(
    'kafka_messages_total',
    'Total count of Kafka messages',
    ['service', 'topic', 'operation']
)

KAFKA_MESSAGE_LATENCY = Histogram(
    'kafka_message_processing_seconds',
    'Kafka message processing time in seconds',
    ['service', 'topic'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)
```

### Metric Usage

Metrics are recorded throughout the application using the following patterns:

#### HTTP Request Metrics

The services use middleware for collecting HTTP request metrics:

```python
# Example from backend/services/api/src/middleware/metrics.py
class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract route pattern if it exists, otherwise use path
        route_pattern = request.url.path
        if request.scope.get("route"):
            route_pattern = request.scope["route"].path
        
        try:
            response = await call_next(request)
            
            REQUEST_COUNT.labels(
                service="api",
                endpoint=route_pattern,
                method=request.method,
                status_code=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                service="api",
                endpoint=route_pattern,
                method=request.method
            ).observe(time.time() - start_time)
            
            return response
        except Exception as e:
            # Log exception and re-raise
            logger.error(f"Request error: {str(e)}")
            REQUEST_COUNT.labels(
                service="api",
                endpoint=route_pattern,
                method=request.method,
                status_code=500
            ).inc()
            raise
```

#### Database Operation Metrics

```python
async def track_db_operation(operation, table, coroutine):
    """Measure database operation latency and count."""
    start_time = time.time()
    
    try:
        result = await coroutine
        DB_OPERATION_COUNT.labels(
            service="api",
            operation=operation,
            table=table,
            status="success"
        ).inc()
        
        DB_OPERATION_LATENCY.labels(
            service="api",
            operation=operation,
            table=table
        ).observe(time.time() - start_time)
        
        return result
    except Exception as e:
        DB_OPERATION_COUNT.labels(
            service="api",
            operation=operation,
            table=table,
            status="error"
        ).inc()
        raise
```

#### Kafka Metrics

Each Kafka consumer automatically tracks message processing metrics:

```python
# From backend/services/processor/src/kafka_consumer.py
# Message processing metrics
with PROCESSING_TIME.labels(topic).time():
    with tracer.start_as_current_span(f"process_{topic}_message"):
        # Call all handlers for this topic
        if topic in self.handlers:
            for handler_name, handler in self.handlers[topic].items():
                try:
                    # Use thread pool to avoid blocking the consumer
                    self.thread_pool.submit(handler, value)
                except Exception as e:
                    logger.exception(f"Handler {handler_name} failed: {str(e)}")
                    MESSAGES_PROCESSED.labels(topic=topic, result="error").inc()
        else:
            logger.warning(f"No handlers registered for topic {topic}")

# Increment successful processing counter
MESSAGES_PROCESSED.labels(topic=topic, result="success").inc()
```

### Metric Endpoints

Each service exposes a `/metrics` endpoint that can be scraped by Prometheus:

```python
from prometheus_client import make_asgi_app

# Create metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

## Health Checks

### Health Check Implementation

Each service now implements a standardized health check system via its `health_setup.py` module. This provides:

1. An overall health endpoint (`/health`)
2. A readiness check (`/health/ready`)
3. A liveness check (`/health/live`)
4. Component-specific health details (`/health/component/{component}`)
5. Service-specific endpoints (e.g. `/health/kafka` for processor service, `/health/dependencies` for API service)

Example health check response:

```json
{
  "status": "ok",
  "version": "2.0.0",
  "service": "api-service",
  "checks": {
    "service": true,
    "database": true,
    "auth-provider": true,
    "rate-limiter": true,
    "processor-service": false,
    "scraper-service": true
  },
  "details": {
    "service": "Running normally",
    "database": "Connected to PostgreSQL 14",
    "auth-provider": "JWT provider active",
    "rate-limiter": "Redis-based rate limiter active",
    "processor-service": "Connection refused",
    "scraper-service": "Service healthy"
  }
}
```

### Health Status Management

Services update their health status using a standardized HealthCheck class:

```python
# From backend/services/api/src/health_setup.py
def set_component_status(self, component: str, status: bool, details: str) -> None:
    """Set the status of a component
    
    Args:
        component: The name of the component
        status: Whether the component is healthy
        details: Details about the component status
    """
    if component in self.checks:
        old_status = self.checks[component]
        self.checks[component] = status
        self.details[component] = details
        
        if old_status != status:
            log_level = logging.INFO if status else logging.ERROR
            logger.log(log_level, f"Component {component} health changed to {status}: {details}")
    else:
        self.checks[component] = status
        self.details[component] = details
        logger.info(f"Added new component {component} with health {status}: {details}")
```

Each service type monitors different components:

- **API Service**: Database, auth provider, rate limiter, dependent services
- **Processor Service**: Database, Kafka consumer/producer connections
- **Scraper Service**: Network connectivity, scraper modules
- **Notification Service**: Email/SMS providers, Kafka consumer, database

### Kubernetes Integration

The health check endpoints are integrated with Kubernetes probes:

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: http
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: http
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Logging Framework

### Structured Logging

All services now use a unified logging configuration from `backend/shared/config/logging_config.py`:

```python
def configure_logging(
    service_name: str,
    log_level: str = "INFO",
    json_logs: bool = True
) -> None:
    """Configure the logging system for a service
    
    Args:
        service_name: Name of the service for log identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_logs: Whether to output logs in JSON format
    """
    # Set up root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create handler
    handler = logging.StreamHandler()
    
    if json_logs:
        # JSON formatter for structured logging
        handler.setFormatter(JsonFormatter(service_name))
    else:
        # Standard formatter for local development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
```

The JsonFormatter creates structured logs with consistent fields:

```python
class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name
    
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "logger": record.name,
            "path": f"{record.pathname}:{record.lineno}",
            "function": f"{record.module}.{record.funcName}"
        }
        
        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "value": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        # Include any extra attributes
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text", "filename", 
                "funcName", "id", "levelname", "levelno", "lineno", "module", 
                "msecs", "message", "msg", "name", "pathname", "process", 
                "processName", "relativeCreated", "stack_info", "thread", "threadName"
            }:
                log_record[key] = value
        
        return json.dumps(log_record)
```

### Contextual Logging

Services use the logger to include contextual information:

```python
logger = get_logger(__name__)

# Log with extra context
logger.info(
    "Processing listing data", 
    extra={
        "listing_id": listing.id,
        "category": listing.category,
        "processing_time_ms": int(processing_time * 1000)
    }
)
```

## Database Migrations

### Migration Framework

The system now uses Alembic for database migrations. The migration configuration is in:

- `backend/alembic.ini`: Database connection and configuration
- `backend/migrations/env.py`: Migration environment setup
- `backend/migrations/versions/`: Individual migration scripts

The initial migration creates all database tables:

```python
# From backend/migrations/versions/initial_migration.py
def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('username', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        # ... additional columns
    )
    
    # Create additional tables
    # ... table definitions for API keys, listings, alerts, etc.
```

### Migration Commands

Migrations are tracked and executed using:

```bash
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Check current migration state
alembic current

# Revert to a previous migration
alembic downgrade <revision>
```

## Distributed Tracing

Each service is instrumented with OpenTelemetry for distributed tracing:

```python
# Initialize tracer
tracer = trace.get_tracer(__name__)

# Use in code
with tracer.start_as_current_span("process_listing"):
    # Processing steps with additional spans
    with tracer.start_as_current_span("extract_data"):
        # Data extraction logic
        pass
        
    with tracer.start_as_current_span("store_listing"):
        # Database operations
        pass
```

The Kafka consumer uses tracing to track message processing across services:

```python
# From backend/services/processor/src/kafka_consumer.py
with tracer.start_as_current_span(f"process_{topic}_message"):
    # Call handlers for this topic
    # ...
```

## Dashboards and Visualization

### Grafana Dashboards

The system includes a set of pre-configured Grafana dashboards for monitoring all aspects of the application:

#### Service Overview Dashboard

This dashboard provides a high-level view of all services, including:

- Service health status
- Request rates and latencies
- Error rates by service and endpoint
- Resource utilization
- Kafka topic lag

![Service Overview Dashboard](../assets/images/service_overview_dashboard.png)

#### Scraper Performance Dashboard

This dashboard focuses on scraper-specific metrics:

- Scraping success and failure rates
- Average scrape duration
- Listings collected per scraper
- Error breakdown by type
- Rate limiting statistics

#### Database Performance Dashboard

This dashboard monitors database health and performance:

- Query latency by operation type
- Connection pool utilization
- Transaction rates
- Table sizes and index usage
- Lock statistics

#### User Activity Dashboard

This dashboard tracks user interactions with the system:

- Active users
- Registration rates
- Login success/failure
- API key usage
- Popular search terms

### Dashboard Configuration

Dashboards are provisioned automatically using the Grafana provisioning API:

```yaml
# /etc/grafana/provisioning/dashboards/facebook-marketplace.yaml
apiVersion: 1

providers:
  - name: 'Facebook Marketplace Scraper'
    orgId: 1
    folder: 'Facebook Marketplace'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 60
    options:
      path: /var/lib/grafana/dashboards
```

### Custom Visualization Panels

The system includes custom Grafana panels for visualizing:

1. **Scraper Coverage Map**: Geographic visualization of listing locations
2. **Alert Timeline**: Chronological view of system alerts
3. **Service Dependency Graph**: Interactive visualization of service dependencies
4. **Listing Trend Analysis**: Time-series analysis of listing prices and categories

## Resource Utilization Monitoring

### System Resource Metrics

The monitoring system tracks key resource metrics for each service:

```python
# From backend/shared/utils/monitoring.py
# Memory metrics
MEMORY_USAGE = Gauge(
    'process_memory_usage_bytes',
    'Memory usage of the process in bytes',
    ['service']
)

# CPU metrics
CPU_USAGE_PERCENT = Gauge(
    'process_cpu_usage_percent',
    'CPU usage of the process in percent',
    ['service']
)

# File descriptor metrics
OPEN_FILE_DESCRIPTORS = Gauge(
    'process_open_file_descriptors',
    'Number of open file descriptors',
    ['service']
)

# Thread metrics
THREAD_COUNT = Gauge(
    'process_thread_count',
    'Number of threads',
    ['service']
)
```

### Collection Methods

Resource metrics are collected using the `psutil` library:

```python
# From backend/shared/utils/monitoring.py
def collect_resource_metrics(service_name: str) -> None:
    """Collect resource metrics for a service.
    
    Args:
        service_name: The name of the service
    """
    process = psutil.Process()
    
    # Memory usage
    memory_info = process.memory_info()
    MEMORY_USAGE.labels(service=service_name).set(memory_info.rss)
    
    # CPU usage
    CPU_USAGE_PERCENT.labels(service=service_name).set(process.cpu_percent(interval=0.1))
    
    # File descriptors
    OPEN_FILE_DESCRIPTORS.labels(service=service_name).set(len(process.open_files()))
    
    # Thread count
    THREAD_COUNT.labels(service=service_name).set(process.num_threads())
```

### Kubernetes Resource Metrics

In Kubernetes environments, resources are also monitored at the container level through the Kubernetes Metrics API:

```yaml
# Prometheus scrape config for Kubernetes
kubernetes_sd_configs:
  - role: pod
relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_app]
    regex: facebook-marketplace-scraper
    action: keep
  - source_labels: [__meta_kubernetes_pod_container_name]
    regex: api|scraper|processor|notifications
    action: keep
```

### Automated Scaling

Resource metrics drive horizontal pod autoscaling in Kubernetes:

```yaml
# HorizontalPodAutoscaler for the scraper service
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: scraper
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: scraper
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Resource Usage Alerts

Alerts are configured for resource utilization thresholds:

```yaml
# Prometheus alert rules for resource utilization
groups:
- name: resource_alerts
  rules:
  - alert: HighMemoryUsage
    expr: process_memory_usage_bytes / 1024 / 1024 > 500
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "{{ $labels.service }} is using more than 500MB of memory"
      
  - alert: HighCPUUsage
    expr: process_cpu_usage_percent > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "{{ $labels.service }} is using more than 80% CPU"
```

## Log Management

### ELK Stack Integration

Logs from all services are centralized using the Elastic Stack (Elasticsearch, Logstash, Kibana):

#### Log Collection

Filebeat is configured to collect logs from all services:

```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - '/var/lib/docker/containers/*/*.log'
  processors:
    - add_kubernetes_metadata:
        host: ${NODE_NAME}
        matchers:
        - logs_path:
            logs_path: "/var/lib/docker/containers/"

output.logstash:
  hosts: ["logstash:5044"]
```

#### Log Processing

Logstash processes and enriches logs before indexing:

```ruby
# logstash.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [kubernetes][container][name] =~ "facebook-marketplace" {
    json {
      source => "message"
    }
    
    # Add service-specific metadata
    if [service] == "api" {
      mutate {
        add_field => { "component" => "api" }
      }
    } else if [service] == "scraper" {
      mutate {
        add_field => { "component" => "scraper" }
      }
    }
    
    # Parse timestamps
    date {
      match => [ "timestamp", "ISO8601" ]
      target => "@timestamp"
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "facebook-marketplace-%{+YYYY.MM.dd}"
  }
}
```

#### Log Storage and Retention

Elasticsearch indices are managed with Index Lifecycle Policies:

```json
{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_age": "1d",
            "max_size": "50gb"
          }
        }
      },
      "warm": {
        "min_age": "7d",
        "actions": {
          "shrink": {
            "number_of_shards": 1
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "30d",
        "actions": {
          "freeze": {}
        }
      },
      "delete": {
        "min_age": "90d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

#### Log Visualization and Analysis

Kibana dashboards are configured for log analysis:

- **Error Investigation**: Shows error patterns and frequencies
- **User Activity**: Tracks user actions and authentication events
- **Service Performance**: Visualizes service performance based on logs
- **Audit Trail**: Provides a chronological view of system changes

### Log Search and Analysis

Common log search patterns include:

```
# Find errors from a specific service
service:api AND level:ERROR

# Find logs for a specific listing ID
extra.listing_id:12345

# Search for authentication failures
message:"Authentication failed" AND service:api

# Find slow database operations
extra.processing_time_ms:>1000 AND message:"Database operation"
```

## Runbooks and Operational Procedures

### Automated Runbooks

The system includes automated runbooks for common operational tasks. These are executable scripts with built-in safety checks:

#### Service Restart Script

```bash
#!/bin/bash
# restart_service.sh - Safely restart a service
# Usage: restart_service.sh <service-name>

SERVICE=$1
NAMESPACE="facebook-marketplace"

# Validate input
if [[ -z "$SERVICE" ]]; then
  echo "Error: Service name is required"
  echo "Usage: restart_service.sh <service-name>"
  exit 1
fi

# Validate service exists
if ! kubectl get deployment -n $NAMESPACE $SERVICE &>/dev/null; then
  echo "Error: Service $SERVICE not found in namespace $NAMESPACE"
  exit 1
fi

# Check if service is currently healthy
HEALTH_URL="http://$SERVICE.$NAMESPACE.svc.cluster.local/health"
HEALTH_STATUS=$(kubectl run -i --rm --restart=Never curl-test --image=curlimages/curl -- -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [[ "$HEALTH_STATUS" != "200" ]]; then
  echo "Warning: Service $SERVICE is reporting unhealthy status ($HEALTH_STATUS)"
  read -p "Do you want to proceed with restart? (y/n) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restart aborted"
    exit 1
  fi
fi

# Perform rolling restart
echo "Restarting $SERVICE..."
kubectl rollout restart deployment -n $NAMESPACE $SERVICE

# Wait for rollout to complete
kubectl rollout status deployment -n $NAMESPACE $SERVICE

# Verify health after restart
sleep 5
HEALTH_STATUS=$(kubectl run -i --rm --restart=Never curl-test --image=curlimages/curl -- -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [[ "$HEALTH_STATUS" == "200" ]]; then
  echo "Service $SERVICE restarted successfully and is reporting healthy"
else
  echo "Warning: Service $SERVICE is reporting unhealthy status ($HEALTH_STATUS) after restart"
fi
```

#### Database Backup Script

```bash
#!/bin/bash
# backup_database.sh - Create a backup of the PostgreSQL database
# Usage: backup_database.sh [backup_dir]

BACKUP_DIR=${1:-"/var/backups/facebook-marketplace"}
TIMESTAMP=$(date +%Y%m%d%H%M%S)
DB_NAME="marketplace"
DB_USER="postgres"
DB_HOST="postgresql.facebook-marketplace.svc.cluster.local"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create backup
echo "Creating backup of $DB_NAME database..."
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

if pg_dump -h $DB_HOST -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE; then
  echo "Backup created successfully: $BACKUP_FILE"
  # Create a symlink to the latest backup
  ln -sf $BACKUP_FILE $BACKUP_DIR/latest.sql.gz
else
  echo "Error: Backup failed"
  exit 1
fi

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "${DB_NAME}_*.sql.gz" -type f -mtime +7 -delete
```

### Incident Response Procedure

The incident response procedure follows these steps:

1. **Detection**: Alert triggered or issue reported
2. **Triage**: Assess severity and impact
3. **Containment**: Limit the scope of the incident
4. **Resolution**: Apply corrective actions
5. **Recovery**: Restore normal operations
6. **Post-mortem**: Analyze root cause and preventive measures

#### Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|------------|
| P1    | Critical service outage | Immediate | Engineering manager |
| P2    | Significant degradation | 30 minutes | Technical lead |
| P3    | Minor functionality issues | 2 hours | Service owner |
| P4    | Cosmetic issues | 1 business day | Development team |

### On-Call Rotation

The on-call rotation follows a weekly schedule:

1. Primary on-call engineer: First responder to all alerts
2. Secondary on-call engineer: Backup for the primary engineer
3. Escalation manager: Available for P1/P2 incidents

On-call handover includes a review of:
- Current operational issues
- Recent deployments
- Planned maintenance
- Special considerations

## Related Documentation

- [Architecture Overview](architecture.md)
- [Deployment Guide](deployment.md)
- [Security Documentation](security.md)
- [Testing Documentation](testing.md)
