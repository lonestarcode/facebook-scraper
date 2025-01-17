from fastapi import WebSocket
from typing import Dict, Set
import asyncio
from src.database.session import get_db_session
from src.database.models import MarketplaceListing
from datetime import datetime, timedelta
from src.logging.logger import get_logger

logger = get_logger(__name__)

class ListingNotifier:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
        self.last_check: Dict[str, datetime] = {}
        
    async def connect(self, websocket: WebSocket, category: str):
        """Connect a client to updates for a specific category"""
        await websocket.accept()
        
        if category not in self.connections:
            self.connections[category] = set()
            self.last_check[category] = datetime.utcnow()
            
        self.connections[category].add(websocket)
        logger.info(f"Client connected to category {category}")
        
    async def disconnect(self, websocket: WebSocket, category: str):
        """Disconnect a client"""
        self.connections[category].remove(websocket)
        logger.info(f"Client disconnected from category {category}")
        
    async def broadcast_listings(self, category: str):
        """Check for and broadcast new listings"""
        if not self.connections.get(category):
            return
            
        try:
            async with get_db_session() as session:
                query = session.query(MarketplaceListing)\
                    .filter(
                        MarketplaceListing.category == category,
                        MarketplaceListing.created_at > self.last_check[category]
                    )\
                    .order_by(MarketplaceListing.created_at.desc())
                    
                new_listings = await query.all()
                
                if new_listings:
                    self.last_check[category] = datetime.utcnow()
                    dead_connections = set()
                    
                    for websocket in self.connections[category]:
                        try:
                            now = datetime.utcnow()
                            age_hours = (now - listing.created_at).total_seconds() / 3600
                            await websocket.send_json({
                                "new_listings": [
                                    {
                                        "id": listing.id,
                                        "title": listing.title,
                                        "price": listing.price,
                                        "location": listing.location,
                                        "url": listing.listing_url,
                                        "created_at": listing.created_at.isoformat(),
                                        "age_hours": round(age_hours, 1),
                                        "age_display": self._format_age(age_hours)
                                    }
                                    for listing in new_listings
                                ]
                            })
                        except Exception as e:
                            logger.error(f"Error sending to websocket: {str(e)}")
                            dead_connections.add(websocket)
                            
                    # Clean up dead connections
                    for dead in dead_connections:
                        await self.disconnect(dead, category)
                        
        except Exception as e:
            logger.error(f"Error broadcasting listings: {str(e)}")

listing_notifier = ListingNotifier() 