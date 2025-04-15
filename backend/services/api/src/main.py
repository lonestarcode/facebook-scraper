"""Main entry point for the API service"""

import argparse
import uvicorn
import os
import sys
from dotenv import load_dotenv

# Add the root directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.append(parent_dir)

# Load environment variables from .env file
load_dotenv()

from backend.shared.config.settings import get_settings
from backend.shared.config.logging_config import configure_logging, get_logger
from backend.services.api.src.app import app  # Import the FastAPI app instance

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Facebook Marketplace Scraper API Service")
    parser.add_argument(
        "--host", 
        help="Host to bind the server to", 
        default=os.getenv("API_HOST", "0.0.0.0")
    )
    parser.add_argument(
        "--port", 
        help="Port to bind the server to",
        type=int, 
        default=int(os.getenv("API_PORT", "8000"))
    )
    parser.add_argument(
        "--reload", 
        help="Enable auto-reload", 
        action="store_true",
        default=os.getenv("API_RELOAD", "").lower() in ("true", "1", "yes")
    )
    parser.add_argument(
        "--log-level", 
        help="Logging level", 
        default=os.getenv("LOG_LEVEL", "info"),
        choices=["debug", "info", "warning", "error", "critical"]
    )
    return parser.parse_args()

def main():
    """Main entry point for the API service"""
    # Parse command line arguments
    args = parse_args()
    
    # Configure logging
    configure_logging(
        service_name="api-service",
        log_level=args.log_level.upper()
    )
    logger = get_logger(__name__)
    
    # Log startup information
    logger.info(f"Starting API service on {args.host}:{args.port}")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Debug mode: {args.reload}")
    
    # Start the server
    uvicorn.run(
        "backend.services.api.src.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower(),
        access_log=True
    )

if __name__ == "__main__":
    main() 