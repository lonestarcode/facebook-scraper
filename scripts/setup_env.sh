#!/bin/bash

# Exit on error
set -e

echo "Setting up Facebook Marketplace Scraper environment..."

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data/logs
mkdir -p data/downloads
mkdir -p config/prometheus
mkdir -p config/grafana

# Copy example configs if they don't exist
for config in scraper_config.yaml llm_config.yaml monitoring_config.yaml; do
    if [ ! -f "config/$config" ]; then
        cp "config/${config}.example" "config/$config"
    fi
done

# Set up environment variables
if [ ! -f .env ]; then
    cat > .env << EOL
ENVIRONMENT=development
OPENAI_API_KEY=your-api-key-here
GRAFANA_PASSWORD=admin
DATABASE_URL=postgresql://user:password@localhost:5432/marketplace
EOL
    echo "Created .env file with default values. Please update with your actual credentials."
fi

# Initialize database
alembic upgrade head

echo "Environment setup complete!"
