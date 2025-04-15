"""Main entry point for the Facebook Marketplace processor service"""

import asyncio
import logging
import os
import signal
import sys
from typing import Dict, Any, List, Optional

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from prometheus_client import start_http_server

# Import shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from shared.config.settings import get_settings
from shared.config.logging_config import configure_logging, get_logger
from shared.models.marketplace import Listing, ListingStatus
from shared.utils.kafka import create_producer

# Import local modules
from health_setup import create_health_check, setup_health_checks
from kafka_consumer import KafkaConsumerManager, process_listing, process_alert

# Load environment variables
load_dotenv()

# Configure logging
configure_logging(service_name="processor-service", json_logs=True)
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(title="Facebook Marketplace Processor Service")

# Create health check manager
health_check = create_health_check("processor-service")

# Kafka consumer manager
consumer_manager: Optional[KafkaConsumerManager] = None

# Kafka producer
kafka_producer = None

async def process_new_listing(message: Dict[str, Any]) -> None:
    """Process a new marketplace listing
    
    Args:
        message: The listing data from Kafka
    """
    try:
        # Create a Listing object from the message
        listing = Listing.model_validate(message)
        
        logger.info(f"Processing new listing: {listing.id} - {listing.title}")
        
        # Example processing logic:
        # 1. Check for prohibited items
        # 2. Classify the listing category
        # 3. Extract relevant keywords
        # 4. Update the listing status
        
        # Update the listing status to processed
        listing.status = ListingStatus.PROCESSED
        
        # Send the processed listing to the next topic
        if kafka_producer:
            await kafka_producer.produce(
                topic="marketplace-listings-processed",
                key=str(listing.id),
                value=listing.model_dump_json()
            )
            logger.info(f"Sent processed listing to Kafka: {listing.id}")
    except Exception as e:
        logger.exception(f"Error processing listing: {str(e)}")
        health_check.set_component_status("listing-processor", False, f"Processing error: {str(e)}")

async def process_listing_alert(message: Dict[str, Any]) -> None:
    """Process an alert for marketplace listings
    
    Args:
        message: The alert data from Kafka
    """
    try:
        alert_id = message.get("id", "unknown")
        search_terms = message.get("search_terms", [])
        
        logger.info(f"Processing alert {alert_id} with search terms: {search_terms}")
        
        # Example alert processing logic:
        # 1. Match alert criteria against processed listings
        # 2. Generate notifications for matches
        
        # Send matches to the notifications service
        if kafka_producer and message.get("matches"):
            await kafka_producer.produce(
                topic="marketplace-notifications",
                key=alert_id,
                value=message
            )
            logger.info(f"Sent {len(message['matches'])} matches to notifications service")
    except Exception as e:
        logger.exception(f"Error processing alert: {str(e)}")
        health_check.set_component_status("alert-processor", False, f"Alert processing error: {str(e)}")

async def startup_event() -> None:
    """Initialize services on application startup"""
    global consumer_manager, kafka_producer
    
    logger.info("Starting processor service")
    
    settings = get_settings()
    
    try:
        # Start Prometheus metrics server
        metrics_port = int(os.getenv("METRICS_PORT", "8081"))
        start_http_server(metrics_port)
        logger.info(f"Prometheus metrics server started on port {metrics_port}")
        
        # Create Kafka producer
        kafka_producer = await create_producer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id="processor-service"
        )
        logger.info("Kafka producer initialized")
        health_check.set_component_status("kafka-producer", True, "Connected")
        
        # Create and configure Kafka consumer
        consumer_manager = KafkaConsumerManager(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="processor-group",
            health_check_callback=health_check.set_component_status
        )
        
        # Add topic handlers
        consumer_manager.add_topic_handler("marketplace-listings-new", process_new_listing)
        consumer_manager.add_topic_handler("marketplace-alerts", process_listing_alert)
        
        # Start consumers
        await consumer_manager.start()
        
        logger.info("Processor service startup complete")
    except Exception as e:
        logger.exception(f"Error during service startup: {str(e)}")
        # Set health check status to unhealthy
        health_check.set_component_status("service", False, f"Startup error: {str(e)}")

async def shutdown_event() -> None:
    """Clean up resources on application shutdown"""
    logger.info("Shutting down processor service")
    
    try:
        # Stop Kafka consumer
        if consumer_manager:
            await consumer_manager.stop()
        
        # Close Kafka producer
        if kafka_producer:
            await kafka_producer.close()
            logger.info("Kafka producer closed")
        
        logger.info("Processor service shutdown complete")
    except Exception as e:
        logger.exception(f"Error during service shutdown: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"service": "Facebook Marketplace Processor Service", "status": "running"}

# Register startup and shutdown events
app.add_event_handler("startup", startup_event)
app.add_event_handler("shutdown", shutdown_event)

# Set up health check endpoints
setup_health_checks(app, health_check)

def handle_signals() -> None:
    """Set up signal handlers for graceful shutdown"""
    def handle_exit(sig, frame):
        logger.info(f"Received exit signal {sig}")
        asyncio.create_task(shutdown_event())
    
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

if __name__ == "__main__":
    # Handle signals for graceful shutdown
    handle_signals()
    
    # Print startup banner
    print("=" * 50)
    print("Facebook Marketplace Processor Service")
    print("=" * 50)
    
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("ENV", "production").lower() == "development",
        log_config=None,  # Use our own logger
    ) 