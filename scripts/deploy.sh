#!/bin/bash

# Exit on error
set -e

# Configuration
APP_NAME="facebook-marketplace-scraper"
DEPLOY_DIR="/opt/$APP_NAME"
BACKUP_DIR="/opt/backups/$APP_NAME"

echo "Deploying $APP_NAME..."

# Create backup
timestamp=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
if [ -d "$DEPLOY_DIR" ]; then
    tar -czf "$BACKUP_DIR/backup_$timestamp.tar.gz" -C "$DEPLOY_DIR" .
fi

# Create deployment directory
mkdir -p "$DEPLOY_DIR"

# Copy application files
cp -r . "$DEPLOY_DIR/"

# Set permissions
chmod +x "$DEPLOY_DIR/scripts/"*.sh

# Install dependencies
cd "$DEPLOY_DIR"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start services with Docker
docker-compose down || true
docker-compose up -d

# Health check
echo "Performing health check..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "Deployment successful! Services are running."
        exit 0
    fi
    echo "Waiting for services to start... ($i/30)"
    sleep 2
done

echo "Error: Services failed to start properly"
exit 1
