import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from src.api.middleware import RateLimitMiddleware, AuthenticationMiddleware
from src.pipeline.data_pipeline import MarketplacePipeline
from src.logging.logger import get_logger
from src.monitoring.metrics import SCRAPE_COUNTER, SCRAPE_DURATION
from src.database.session import get_db_session
from src.database.models import MarketplaceListing
from src.websocket.listing_notifier import listing_notifier

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Facebook Marketplace Scraper",
    description="API for scraping and managing Facebook Marketplace listings",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthenticationMiddleware)

# Add metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Background scraping task
async def scrape_categories():
    """Background task to scrape marketplace categories"""
    pipeline = MarketplacePipeline()
    categories = ["bikes", "electronics", "furniture"]
    
    while True:
        for category in categories:
            try:
                with SCRAPE_DURATION.labels(category=category).time():
                    await pipeline.process_category(category)
                SCRAPE_COUNTER.labels(category=category).inc()
            except Exception as e:
                logger.error(f"Error processing category {category}: {str(e)}")
        await asyncio.sleep(300)  # 5 minutes between scrapes

# API endpoints
@app.get("/listings/")
async def get_listings(
    category: str = None,
    limit: int = 10,
    offset: int = 0
):
    """Get marketplace listings with optional filtering"""
    try:
        async with get_db_session() as session:
            query = session.query(MarketplaceListing)
            if category:
                query = query.filter(MarketplaceListing.category == category)
            
            total = await query.count()
            listings = await query.offset(offset).limit(limit).all()
            
            return {
                "total": total,
                "listings": listings,
                "limit": limit,
                "offset": offset
            }
    except Exception as e:
        logger.error(f"Error fetching listings: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    """Get details for a specific listing"""
    try:
        async with get_db_session() as session:
            listing = await session.query(MarketplaceListing).filter(
                MarketplaceListing.listing_id == listing_id
            ).first()
            
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            return listing
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching listing {listing_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Start background scraping task on application startup"""
    asyncio.create_task(scrape_categories())

@app.websocket("/ws/listings/{category}")
async def websocket_endpoint(websocket: WebSocket, category: str):
    """WebSocket endpoint for real-time listing updates"""
    await listing_notifier.connect(websocket, category)
    
    try:
        while True:
            await listing_notifier.broadcast_listings(category)
            await asyncio.sleep(30)  # Check every 30 seconds
    except WebSocketDisconnect:
        await listing_notifier.disconnect(websocket, category)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await listing_notifier.disconnect(websocket, category)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
