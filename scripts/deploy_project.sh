#!/bin/bash

# Exit on error
set -e

echo "Deploying Facebook Marketplace Scraper..."

# Build and start containers
docker-compose build
docker-compose up -d

# Wait for database to be ready
echo "Waiting for database..."
sleep 10

# Run database migrations
docker-compose exec backend alembic upgrade head

# Initialize Prometheus and Grafana
echo "Setting up monitoring..."
docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
docker-compose exec grafana grafana-cli plugins install grafana-piechart-panel

echo "Deployment complete! Services available at:"
echo "- API: http://localhost:8000"
echo "- Frontend: http://localhost:3000"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000/grafana" 