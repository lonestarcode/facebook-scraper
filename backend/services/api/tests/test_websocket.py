"""Tests for WebSocket functionality."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

from backend.services.api.src.app import app
from backend.services.api.src.websocket import websocket_manager


@pytest.fixture
def test_client():
    """Return a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    mock = AsyncMock(spec=WebSocket)
    mock.state = MagicMock()
    mock.accept = AsyncMock()
    mock.send_json = AsyncMock()
    mock.receive_text = AsyncMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_kafka_consumer():
    """Create a mock Kafka consumer for testing."""
    with patch("backend.services.api.src.websocket.manager.KafkaConsumer") as mock:
        consumer = AsyncMock()
        consumer.start = AsyncMock()
        consumer.stop = AsyncMock()
        consumer.consume = AsyncMock()
        mock.return_value = consumer
        yield consumer


@pytest.fixture
def mock_jwt_handler():
    """Create a mock JWT handler for testing."""
    with patch("backend.shared.auth.dependencies.jwt_handler") as mock:
        mock.verify_token = MagicMock()
        yield mock


@pytest.fixture
def mock_db_session():
    """Create a mock DB session for testing."""
    with patch("backend.shared.auth.dependencies.get_db_session") as mock:
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock()
        mock.return_value = session
        yield session


class TestWebSocketManager:
    """Tests for the WebSocketManager class."""

    @pytest.mark.asyncio
    async def test_connect(self, mock_websocket):
        """Test connecting a WebSocket."""
        # Reset the singleton for testing
        websocket_manager.active_connections = {}
        websocket_manager.running = False
        
        with patch.object(websocket_manager, "_start_kafka_consumer", AsyncMock()) as mock_start:
            await websocket_manager.connect(mock_websocket, "test")
            
            # Check that the WebSocket was accepted
            mock_websocket.accept.assert_called_once()
            
            # Check that the connection was added
            assert "test" in websocket_manager.active_connections
            assert mock_websocket in websocket_manager.active_connections["test"]
            
            # Check that the Kafka consumer was started
            mock_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_websocket):
        """Test disconnecting a WebSocket."""
        # Set up a connection
        websocket_manager.active_connections = {"test": {mock_websocket}}
        websocket_manager.running = True
        
        with patch.object(websocket_manager, "_stop_kafka_consumer", AsyncMock()) as mock_stop:
            await websocket_manager.disconnect(mock_websocket, "test")
            
            # Check that the connection was removed
            assert "test" not in websocket_manager.active_connections
            
            # Check that the Kafka consumer was stopped
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast(self, mock_websocket):
        """Test broadcasting a message."""
        # Set up connections
        websocket1 = mock_websocket
        websocket2 = AsyncMock(spec=WebSocket)
        websocket2.send_json = AsyncMock()
        
        websocket_manager.active_connections = {"test": {websocket1, websocket2}}
        
        # Broadcast a message
        message = {"type": "test", "data": "hello"}
        await websocket_manager.broadcast(message, "test")
        
        # Check that the message was sent to both WebSockets
        websocket1.send_json.assert_called_once_with(message)
        websocket2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_with_error(self, mock_websocket):
        """Test broadcasting a message when one client has an error."""
        # Set up connections
        websocket1 = mock_websocket
        websocket2 = AsyncMock(spec=WebSocket)
        websocket2.send_json = AsyncMock(side_effect=Exception("Test error"))
        
        websocket_manager.active_connections = {"test": {websocket1, websocket2}}
        
        # Broadcast a message
        message = {"type": "test", "data": "hello"}
        await websocket_manager.broadcast(message, "test")
        
        # Check that the message was sent to the working WebSocket
        websocket1.send_json.assert_called_once_with(message)
        
        # Check that the error WebSocket was removed
        assert websocket2 not in websocket_manager.active_connections["test"]

    @pytest.mark.asyncio
    async def test_handle_client_command_ping(self, mock_websocket):
        """Test handling a ping command from a client."""
        # Set up the test
        command = {"type": "ping"}
        
        # Call the method
        await websocket_manager._handle_client_command(mock_websocket, command, "test")
        
        # Check that a pong was sent
        mock_websocket.send_json.assert_called_once()
        sent_message = mock_websocket.send_json.call_args[0][0]
        assert sent_message["type"] == "pong"
        assert "timestamp" in sent_message

    @pytest.mark.asyncio
    async def test_handle_client_command_filter(self, mock_websocket):
        """Test handling a filter command from a client."""
        # Set up the test
        command = {"type": "filter", "category": "new_category"}
        
        # Patch the connect and disconnect methods
        with patch.object(websocket_manager, "disconnect", AsyncMock()) as mock_disconnect:
            with patch.object(websocket_manager, "connect", AsyncMock()) as mock_connect:
                # Call the method
                await websocket_manager._handle_client_command(mock_websocket, command, "test")
                
                # Check that disconnect and connect were called
                mock_disconnect.assert_called_once_with(mock_websocket, "test")
                mock_connect.assert_called_once_with(mock_websocket, "new_category")
                
                # Check that a confirmation was sent
                mock_websocket.send_json.assert_called_once()
                sent_message = mock_websocket.send_json.call_args[0][0]
                assert sent_message["type"] == "info"
                assert "Switched to new_category" in sent_message["message"]

    @pytest.mark.asyncio
    async def test_kafka_consumer_loop(self, mock_kafka_consumer):
        """Test the Kafka consumer loop."""
        # Set up the test
        websocket_manager.running = True
        
        # Create a message
        message = MagicMock()
        message.topic.return_value = "marketplace.listings.new"
        message.value.return_value = json.dumps({
            "id": "123",
            "title": "Test Listing",
            "category": "test_category"
        }).encode()
        
        # Mock the async iterator for consume
        mock_kafka_consumer.consume.return_value.__aiter__.return_value = [message]
        
        # Patch the broadcast method
        with patch.object(websocket_manager, "broadcast", AsyncMock()) as mock_broadcast:
            # Run the consumer loop (it will process one message and then we'll stop it)
            task = asyncio.create_task(websocket_manager._kafka_consumer_loop())
            
            # Give the task a chance to process the message
            await asyncio.sleep(0.1)
            
            # Stop the loop
            websocket_manager.running = False
            await task
            
            # Check that the consumer was started
            mock_kafka_consumer.start.assert_called_once()
            
            # Check that broadcast was called for the category and "all"
            assert mock_broadcast.call_count == 2
            mock_broadcast.assert_any_call(
                {
                    "type": "listing",
                    "data": {
                        "id": "123",
                        "title": "Test Listing",
                        "category": "test_category"
                    },
                    "topic": "marketplace.listings.new",
                    "timestamp": mock_broadcast.call_args[0][0]["timestamp"]
                },
                "test_category"
            )
            mock_broadcast.assert_any_call(
                {
                    "type": "listing",
                    "data": {
                        "id": "123",
                        "title": "Test Listing",
                        "category": "test_category"
                    },
                    "topic": "marketplace.listings.new",
                    "timestamp": mock_broadcast.call_args[0][0]["timestamp"]
                },
                "all"
            )


class TestWebSocketRoutes:
    """Tests for the WebSocket routes."""

    @pytest.mark.asyncio
    async def test_listings_websocket(self, mock_websocket):
        """Test the listings WebSocket endpoint."""
        with patch("backend.services.api.src.routes.websocket_routes.websocket_manager.handle_connection", AsyncMock()) as mock_handle:
            # Call the endpoint function directly
            from backend.services.api.src.routes.websocket_routes import listings_websocket
            await listings_websocket(mock_websocket, "test")
            
            # Check that handle_connection was called
            mock_handle.assert_called_once_with(mock_websocket, "test")

    @pytest.mark.asyncio
    async def test_secure_listings_websocket(self, mock_websocket, mock_jwt_handler, mock_db_session):
        """Test the secure listings WebSocket endpoint."""
        # Set up a mock user
        user = MagicMock()
        user.username = "testuser"
        user.id = "user123"
        mock_db_session.get.return_value = user
        
        # Set up token verification
        token_data = MagicMock()
        token_data.user_id = "user123"
        mock_jwt_handler.verify_token.return_value = token_data
        
        with patch("backend.services.api.src.routes.websocket_routes.websocket_manager.handle_connection", AsyncMock()) as mock_handle:
            with patch("backend.shared.auth.dependencies.get_user_by_id", AsyncMock(return_value=user)):
                # Call the endpoint function directly
                from backend.services.api.src.routes.websocket_routes import secure_listings_websocket
                with patch("backend.shared.auth.dependencies.get_current_user_ws", AsyncMock(return_value=user)):
                    await secure_listings_websocket(mock_websocket, "test", user)
                    
                    # Check that the user was added to the WebSocket state
                    assert mock_websocket.state.user == user
                    
                    # Check that handle_connection was called
                    mock_handle.assert_called_once_with(mock_websocket, "test")

    @pytest.mark.asyncio
    async def test_websocket_status(self):
        """Test the WebSocket status endpoint."""
        # Set up the test
        websocket_manager.active_connections = {"test": set(), "all": set()}
        websocket_manager.running = True
        
        with patch.object(websocket_manager, "_count_connections", return_value=5):
            # Call the endpoint function directly
            from backend.services.api.src.routes.websocket_routes import websocket_status
            response = await websocket_status()
            
            # Check the response
            assert response.status_code == 200
            data = json.loads(response.body)
            assert data["connections"] == 5
            assert sorted(data["categories"]) == ["all", "test"]
            assert data["status"] == "active" 