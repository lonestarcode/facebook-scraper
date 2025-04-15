# Deployment Guide

## Overview

This document provides detailed instructions for deploying the Facebook Marketplace Scraper microservices architecture to various environments. It covers local development setup, containerization, Kubernetes deployment, and production considerations.

## Prerequisites

Before deploying the application, ensure you have the following prerequisites:

- Docker and Docker Compose (for local development and containerization)
- Kubernetes cluster (for production deployment)
- Helm (for Kubernetes package management)
- kubectl CLI tool
- Access credentials for container registries
- Database server (PostgreSQL)
- Kafka cluster
- Cloud provider account (if deploying to cloud infrastructure)

## Local Development Environment

### Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-organization/facebook-marketplace-scraper.git
   cd facebook-marketplace-scraper/backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -e .
   ```

4. Set up local environment variables (create a `.env` file in the project root):
   ```
   # Database Configuration
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/marketplace
   
   # Kafka Configuration
   KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   
   # Authentication
   JWT_SECRET_KEY=your_development_secret_key
   JWT_ALGORITHM=HS256
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
   
   # Scraper Configuration
   SCRAPER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
   SCRAPER_TIMEOUT=30
   SCRAPER_MAX_RETRIES=3
   
   # API Configuration
   API_HOST=0.0.0.0
   API_PORT=8000
   
   # Logging
   LOG_LEVEL=INFO
   ```

### Running Services Locally with Docker Compose

1. Start the infrastructure dependencies:
   ```bash
   docker-compose -f infrastructure/docker/docker-compose.yml up -d
   ```

2. Run individual services:
   ```bash
   # API Service
   cd services/api
   uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   
   # Scraper Service (in a new terminal)
   cd services/scraper
   python -m src.main
   
   # Processor Service (in a new terminal)
   cd services/processor
   python -m src.main
   
   # Notifications Service (in a new terminal)
   cd services/notifications
   python -m src.main
   ```

## Containerization

### Building Docker Images

Each service has its own Dockerfile. To build all service images:

```bash
# Build API Service
docker build -t marketplace-api:latest -f services/api/Dockerfile .

# Build Scraper Service
docker build -t marketplace-scraper:latest -f services/scraper/Dockerfile .

# Build Processor Service
docker build -t marketplace-processor:latest -f services/processor/Dockerfile .

# Build Notifications Service
docker build -t marketplace-notifications:latest -f services/notifications/Dockerfile .
```

### Tagging and Pushing Images

For deployment to a container registry:

```bash
# Tag images
docker tag marketplace-api:latest your-registry.com/marketplace-api:1.0.0
docker tag marketplace-scraper:latest your-registry.com/marketplace-scraper:1.0.0
docker tag marketplace-processor:latest your-registry.com/marketplace-processor:1.0.0
docker tag marketplace-notifications:latest your-registry.com/marketplace-notifications:1.0.0

# Push images
docker push your-registry.com/marketplace-api:1.0.0
docker push your-registry.com/marketplace-scraper:1.0.0
docker push your-registry.com/marketplace-processor:1.0.0
docker push your-registry.com/marketplace-notifications:1.0.0
```

## Kubernetes Deployment

### Configuration

The system uses Kubernetes ConfigMaps and Secrets for configuration:

1. Create namespace:
   ```bash
   kubectl create namespace marketplace
   ```

2. Create ConfigMap:
   ```bash
   kubectl apply -f infrastructure/kubernetes/configmap.yaml
   ```

3. Create Secrets (replace placeholders with actual values):
   ```bash
   kubectl create secret generic marketplace-secrets \
     --from-literal=database-url='postgresql://user:password@postgres-host:5432/marketplace' \
     --from-literal=jwt-secret='your-production-secret-key' \
     --from-literal=smtp-password='your-smtp-password' \
     -n marketplace
   ```

### Deploying Services

Apply the Kubernetes deployment manifest:

```bash
kubectl apply -f infrastructure/kubernetes/deployment.yaml
```

This will deploy:
- API Service with appropriate replicas
- Scraper Service
- Processor Service
- Notifications Service
- Service resources for internal communication
- Ingress resource for external access to the API

### Helm Chart Deployment (Alternative)

For more complex deployments, a Helm chart is provided:

```bash
# Add values file customizations
cp infrastructure/helm/values-example.yaml infrastructure/helm/values-production.yaml
# Edit values-production.yaml with your configuration

# Install the chart
helm install marketplace infrastructure/helm/marketplace \
  --namespace marketplace \
  --values infrastructure/helm/values-production.yaml
```

## Database Migration

Before starting the services, run the database migrations:

```bash
# Using the migration script in a Kubernetes job
kubectl apply -f infrastructure/kubernetes/migration-job.yaml

# Or manually through a Kubernetes pod
kubectl run migration --image=your-registry.com/marketplace-api:1.0.0 \
  --restart=Never --rm -it \
  --env="DATABASE_URL=postgresql://user:password@postgres-host:5432/marketplace" \
  -- python -m alembic upgrade head
```

## Environment-Specific Deployment

### Development

For development environments, you can use:

```bash
# Apply development configuration
kubectl apply -f infrastructure/kubernetes/environments/development/

# Or with Helm
helm install marketplace-dev infrastructure/helm/marketplace \
  --namespace marketplace-dev \
  --values infrastructure/helm/values-development.yaml
```

### Staging

For staging environments:

```bash
# Apply staging configuration
kubectl apply -f infrastructure/kubernetes/environments/staging/

# Or with Helm
helm install marketplace-staging infrastructure/helm/marketplace \
  --namespace marketplace-staging \
  --values infrastructure/helm/values-staging.yaml
```

### Production

For production environments:

```bash
# Apply production configuration
kubectl apply -f infrastructure/kubernetes/environments/production/

# Or with Helm
helm install marketplace-prod infrastructure/helm/marketplace \
  --namespace marketplace-prod \
  --values infrastructure/helm/values-production.yaml
```

## Scaling

### Horizontal Pod Autoscaling

The system uses Horizontal Pod Autoscalers (HPA) to scale services based on metrics:

```bash
kubectl apply -f infrastructure/kubernetes/hpa.yaml
```

Example HPA configuration:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: marketplace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Manual Scaling

To manually scale a service:

```bash
kubectl scale deployment api-service --replicas=5 -n marketplace
```

## Continuous Deployment

### CI/CD Pipeline

The project uses GitHub Actions for CI/CD. The workflow is defined in `.github/workflows/deploy.yml`.

Example deployment workflow:

1. Code is pushed to a deployment branch
2. CI pipeline runs tests
3. If tests pass, Docker images are built and pushed to the registry
4. Kubernetes manifests are updated with new image tags
5. Kubernetes resources are applied to the appropriate environment

### Blue/Green Deployment

For zero-downtime deployments, the system supports blue/green deployment:

```bash
# Deploy the new version (green)
kubectl apply -f infrastructure/kubernetes/deployment-green.yaml

# Test the green deployment
# ...

# Switch traffic to the new version
kubectl apply -f infrastructure/kubernetes/service-switch-to-green.yaml

# Remove old version after confirming new version works
kubectl delete -f infrastructure/kubernetes/deployment-blue.yaml
```

## Monitoring and Logging

### Prometheus and Grafana

1. Deploy monitoring stack:
   ```bash
   kubectl apply -f infrastructure/kubernetes/monitoring/
   ```

2. Access Grafana dashboard:
   ```bash
   kubectl port-forward svc/grafana 3000:3000 -n monitoring
   ```

3. Import provided dashboards from `infrastructure/grafana-dashboards/`

### Logging with ELK Stack

1. Deploy logging stack:
   ```bash
   kubectl apply -f infrastructure/kubernetes/logging/
   ```

2. Access Kibana:
   ```bash
   kubectl port-forward svc/kibana 5601:5601 -n logging
   ```

## Backup and Disaster Recovery

### Database Backups

Regular database backups are scheduled using Kubernetes CronJobs:

```bash
kubectl apply -f infrastructure/kubernetes/backup-cronjob.yaml
```

### Restore Procedure

To restore from a backup:

1. Stop affected services:
   ```bash
   kubectl scale deployment api-service --replicas=0 -n marketplace
   kubectl scale deployment processor-service --replicas=0 -n marketplace
   ```

2. Restore the database:
   ```bash
   kubectl apply -f infrastructure/kubernetes/restore-job.yaml
   ```

3. Restart services:
   ```bash
   kubectl scale deployment api-service --replicas=2 -n marketplace
   kubectl scale deployment processor-service --replicas=2 -n marketplace
   ```

## Troubleshooting

### Common Issues

#### Pod Startup Failures
```bash
# Check pod status
kubectl get pods -n marketplace

# Check pod logs
kubectl logs pod/api-service-6d9bd5b48c-abcd1 -n marketplace

# Check pod events
kubectl describe pod api-service-6d9bd5b48c-abcd1 -n marketplace
```

#### Database Connection Issues
```bash
# Check the database secret
kubectl get secret marketplace-secrets -n marketplace -o yaml

# Check service endpoints
kubectl get endpoints -n marketplace
```

#### Ingress Issues
```bash
# Check ingress status
kubectl get ingress -n marketplace

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller
```

### Health Checks

To verify service health:

```bash
# Get the API service URL
export API_URL=$(kubectl get ingress api-ingress -n marketplace -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Check API health
curl http://$API_URL/health

# Check individual service health via port-forwarding
kubectl port-forward svc/scraper-service 8001:8000 -n marketplace
curl http://localhost:8001/health
```

## Security Considerations

### Network Policies

Apply network policies to restrict service communication:

```bash
kubectl apply -f infrastructure/kubernetes/network-policies.yaml
```

### Secret Management

For production, consider using a dedicated secrets management solution like HashiCorp Vault or cloud provider solutions (AWS Secrets Manager, GCP Secret Manager, etc.).

## Related Documentation

- [Architecture Overview](architecture.md)
- [Configuration Guide](configuration.md)
- [Monitoring Documentation](monitoring.md)
- [Database Schema](database.md)
