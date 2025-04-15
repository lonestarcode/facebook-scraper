"""WebSocket manager for real-time marketplace listing updates."""

import json
import logging
import asyncio
from typing import Dict, Set, Optional, Any, List
from fastapi import WebSocket, WebSocketDisconnect

from shared.utils.kafka import KafkaConsumer
from shared.config.logging_config import get_logger
from shared.utils.monitoring import WEBSOCKET_CONNECTIONS, WEBSOCKET_MESSAGES_SENT

logger = get_logger("api.websocket")

class WebSocketManager:
    """
    Manager for WebSocket connections.
    
    Handles:
    - Connection management
    - Broadcasting messages to clients
    - Subscribing to Kafka topics for real-time updates
    """
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.kafka_consumer: Optional[KafkaConsumer] = None
        self.kafka_consumer_task: Optional[asyncio.Task] = None
        self.running = False
        
    async def connect(self, websocket: WebSocket, category: str):
        """Accept a new WebSocket connection and add it to the active connections.
        
        Args:
            websocket: The WebSocket connection
            category: The category to subscribe to (e.g., 'furniture', 'electronics', 'all')
        """
        await websocket.accept()
        
        if category not in self.active_connections:
            self.active_connections[category] = set()
        
        self.active_connections[category].add(websocket)
        
        # Update metrics
        WEBSOCKET_CONNECTIONS.set(self._count_connections())
        
        logger.info(f"New WebSocket connection for category '{category}'. Total connections: {self._count_connections()}")
        
        # Start Kafka consumer if not already running
        if not self.running:
            await self._start_kafka_consumer()
    
    async def disconnect(self, websocket: WebSocket, category: str):
        """Remove a WebSocket connection from the active connections.
        
        Args:
            websocket: The WebSocket connection
            category: The category the connection was subscribed to
        """
        if category in self.active_connections:
            self.active_connections[category].discard(websocket)
            
            # Remove the category if no connections
            if not self.active_connections[category]:
                del self.active_connections[category]
        
        # Update metrics
        WEBSOCKET_CONNECTIONS.set(self._count_connections())
        
        logger.info(f"WebSocket disconnected from category '{category}'. Total connections: {self._count_connections()}")
        
        # Stop Kafka consumer if no more connections
        if self._count_connections() == 0:
            await self._stop_kafka_consumer()
    
    async def broadcast(self, message: Dict[str, Any], category: str):
        """Broadcast a message to all clients in a specific category.
        
        Args:
            message: The message to broadcast
            category: The category of clients to broadcast to
        """
        if category not in self.active_connections:
            return
            
        disconnected_websockets = set()
        message_count = 0
        
        for websocket in self.active_connections[category]:
            try:
                await websocket.send_json(message)
                message_count += 1
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {str(e)}")
                disconnected_websockets.add(websocket)
        
        # Remove any disconnected websockets
        for websocket in disconnected_websockets:
            self.active_connections[category].discard(websocket)
        
        # Update metrics
        WEBSOCKET_MESSAGES_SENT.inc(message_count)
        
        if disconnected_websockets:
            # Update connection count metric after removing disconnected sockets
            WEBSOCKET_CONNECTIONS.set(self._count_connections())
    
    async def broadcast_all(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients.
        
        Args:
            message: The message to broadcast
        """
        for category in list(self.active_connections.keys()):
            await self.broadcast(message, category)
    
    async def handle_connection(self, websocket: WebSocket, category: str):
        """Handle a WebSocket connection for a specific category.
        
        Args:
            websocket: The WebSocket connection
            category: The category to subscribe to
        """
        await self.connect(websocket, category)
        
        try:
            # Send welcome message
            await websocket.send_json({
                "type": "info",
                "message": f"Connected to {category} listings feed",
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Keep connection alive and handle incoming messages
            while True:
                # We receive messages but don't do anything with them currently
                # Can be extended to handle client commands like filtering
                data = await websocket.receive_text()
                
                try:
                    command = json.loads(data)
                    await self._handle_client_command(websocket, command, category)
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON: {data}")
                except Exception as e:
                    logger.error(f"Error handling client command: {str(e)}")
                    
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            await self.disconnect(websocket, category)
    
    async def _handle_client_command(self, websocket: WebSocket, command: Dict[str, Any], category: str):
        """Handle a command from a client.
        
        Args:
            websocket: The WebSocket connection
            command: The command from the client
            category: The category the client is subscribed to
        """
        cmd_type = command.get("type")
        
        if cmd_type == "ping":
            # Respond to ping
            await websocket.send_json({
                "type": "pong",
                "timestamp": asyncio.get_event_loop().time()
            })
        elif cmd_type == "filter":
            # Handle filter requests - could update the category or add specific filters
            new_category = command.get("category")
            if new_category and new_category != category:
                await self.disconnect(websocket, category)
                await self.connect(websocket, new_category)
                
                await websocket.send_json({
                    "type": "info",
                    "message": f"Switched to {new_category} listings feed"
                })
    
    async def _start_kafka_consumer(self):
        """Start the Kafka consumer task."""
        if self.kafka_consumer_task is None or self.kafka_consumer_task.done():
            self.running = True
            self.kafka_consumer_task = asyncio.create_task(self._kafka_consumer_loop())
            logger.info("Started Kafka consumer for WebSocket updates")
    
    async def _stop_kafka_consumer(self):
        """Stop the Kafka consumer task."""
        if self.kafka_consumer_task and not self.kafka_consumer_task.done():
            self.running = False
            
            if self.kafka_consumer:
                await self.kafka_consumer.stop()
            
            self.kafka_consumer_task.cancel()
            try:
                await self.kafka_consumer_task
            except asyncio.CancelledError:
                pass
            
            self.kafka_consumer_task = None
            self.kafka_consumer = None
            logger.info("Stopped Kafka consumer for WebSocket updates")
    
    async def _kafka_consumer_loop(self):
        """Consume messages from Kafka and broadcast them to WebSocket clients."""
        # Topics to consume from
        topics = [
            "marketplace.listings.new", 
            "marketplace.listings.processed",
            "marketplace.alerts.triggered"
        ]
        
        try:
            self.kafka_consumer = KafkaConsumer(
                bootstrap_servers="kafka:9092",
                group_id="websocket-manager",
                topics=topics,
                client_id="api-websocket"
            )
            
            await self.kafka_consumer.start()
            
            async for message in self.kafka_consumer.consume():
                if not self.running:
                    break
                
                try:
                    # Parse the message value
                    if not message.value():
                        continue
                        
                    value = json.loads(message.value())
                    
                    # Determine the category from the message
                    # For listings, use the category field
                    # For alerts, use a special "alerts" category
                    if message.topic() == "marketplace.alerts.triggered":
                        category = "alerts"
                    else:
                        category = value.get("category", "all")
                    
                    # Broadcast to specific category and "all" category
                    websocket_message = {
                        "type": "listing" if "listing" in message.topic() else "alert",
                        "data": value,
                        "topic": message.topic(),
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    
                    await self.broadcast(websocket_message, category)
                    
                    # Also broadcast to "all" if it's not already the category
                    if category != "all":
                        await self.broadcast(websocket_message, "all")
                    
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from Kafka: {message.value()}")
                except Exception as e:
                    logger.error(f"Error processing Kafka message for WebSocket: {str(e)}")
        
        except Exception as e:
            logger.error(f"Kafka consumer error: {str(e)}")
            self.running = False
    
    def _count_connections(self) -> int:
        """Count the total number of active WebSocket connections.
        
        Returns:
            The total number of connections
        """
        return sum(len(connections) for connections in self.active_connections.values())
    
    async def close_all(self):
        """Close all WebSocket connections."""
        # First, stop the Kafka consumer
        await self._stop_kafka_consumer()
        
        # Close all connections
        all_websockets = []
        for category in self.active_connections:
            all_websockets.extend(self.active_connections[category])
        
        for websocket in all_websockets:
            try:
                await websocket.close(code=1000)
            except Exception as e:
                logger.error(f"Error closing WebSocket: {str(e)}")
        
        # Clear the connections dictionary
        self.active_connections.clear()
        
        # Update metrics
        WEBSOCKET_CONNECTIONS.set(0)

# Create a singleton instance
websocket_manager = WebSocketManager() 