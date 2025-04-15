"""WebSocket routes for real-time marketplace listing updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from typing import Optional

from backend.shared.config.logging_config import get_logger
from backend.shared.auth.dependencies import get_current_user_ws
from backend.services.api.src.websocket import websocket_manager

logger = get_logger("api.routes.websocket")

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/listings/{category}")
async def listings_websocket(
    websocket: WebSocket, 
    category: str
):
    """WebSocket endpoint for real-time listing updates.
    
    Args:
        websocket: The WebSocket connection
        category: The category to subscribe to (e.g., 'furniture', 'electronics', 'all')
    """
    try:
        await websocket_manager.handle_connection(websocket, category)
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected from category {category}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")

@router.websocket("/ws/secure/listings/{category}")
async def secure_listings_websocket(
    websocket: WebSocket, 
    category: str,
    user = Depends(get_current_user_ws)
):
    """Authenticated WebSocket endpoint for real-time listing updates.
    
    Args:
        websocket: The WebSocket connection
        category: The category to subscribe to (e.g., 'furniture', 'electronics', 'all')
        user: The authenticated user
    """
    try:
        # Add user info to the connection context
        websocket.state.user = user
        logger.info(f"Authenticated WebSocket connection from user {user.username}")
        
        await websocket_manager.handle_connection(websocket, category)
    except WebSocketDisconnect:
        logger.info(f"Authenticated WebSocket client disconnected from category {category}")
    except Exception as e:
        logger.error(f"Error in authenticated WebSocket connection: {str(e)}")

@router.websocket("/ws/alerts")
async def alerts_websocket(
    websocket: WebSocket,
    user = Depends(get_current_user_ws)
):
    """WebSocket endpoint for real-time alert notifications.
    
    Args:
        websocket: The WebSocket connection
        user: The authenticated user
    """
    try:
        # Add user info to the connection context
        websocket.state.user = user
        logger.info(f"Alert WebSocket connection from user {user.username}")
        
        await websocket_manager.handle_connection(websocket, f"alerts:{user.id}")
    except WebSocketDisconnect:
        logger.info(f"Alert WebSocket client disconnected for user {user.username}")
    except Exception as e:
        logger.error(f"Error in alert WebSocket connection: {str(e)}")

@router.get("/ws/status")
async def websocket_status():
    """Get the status of the WebSocket connections.
    
    Returns:
        JSON response with WebSocket statistics
    """
    connection_count = websocket_manager._count_connections()
    
    return JSONResponse({
        "connections": connection_count,
        "categories": list(websocket_manager.active_connections.keys()),
        "status": "active" if websocket_manager.running else "inactive"
    }) 