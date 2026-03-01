"""
WebSocket endpoints for real-time data streaming
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.routing import APIRouter
import uuid

from app.services.streaming_service import (
    get_streaming_service,
    StreamConfig,
    StreamMessage,
    MessagePriority
)
from app.core.logging import app_logger

router = APIRouter()

# Connection manager for WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_streams: Dict[str, str] = {}  # connection_id -> stream_id

    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept a WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        app_logger.info(f"WebSocket connection established: {connection_id}")

    def disconnect(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_streams:
            del self.connection_streams[connection_id]
        app_logger.info(f"WebSocket connection closed: {connection_id}")

    async def send_personal_message(self, message: str, connection_id: str):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
                return True
            except Exception as e:
                app_logger.error(f"Error sending message to {connection_id}: {e}")
                self.disconnect(connection_id)
                return False
        return False

    async def broadcast(self, message: str):
        """Broadcast a message to all connections"""
        disconnected = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                app_logger.error(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected:
            self.disconnect(connection_id)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time updates

    Supports:
    - Real-time market data streaming
    - Analysis progress updates
    - System notifications
    """
    connection_id = f"{client_id}_{uuid.uuid4().hex[:8]}"
    streaming_service = get_streaming_service()

    await manager.connect(websocket, connection_id)

    try:
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "connection_id": connection_id,
            "timestamp": asyncio.get_event_loop().time(),
            "message": "WebSocket connection established successfully"
        }
        await websocket.send_text(json.dumps(welcome_message))

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "subscribe_market_data":
                    await handle_market_data_subscription(
                        websocket, connection_id, message, streaming_service
                    )
                elif message_type == "subscribe_analysis_progress":
                    await handle_analysis_progress_subscription(
                        websocket, connection_id, message, streaming_service
                    )
                elif message_type == "unsubscribe":
                    await handle_unsubscribe(
                        websocket, connection_id, message, streaming_service
                    )
                elif message_type == "ping":
                    # Respond to ping with pong
                    pong_message = {
                        "type": "pong",
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    await websocket.send_text(json.dumps(pong_message))
                else:
                    error_message = {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    await websocket.send_text(json.dumps(error_message))

            except json.JSONDecodeError:
                error_message = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": asyncio.get_event_loop().time()
                }
                await websocket.send_text(json.dumps(error_message))

    except WebSocketDisconnect:
        app_logger.info(f"WebSocket client {connection_id} disconnected")
    except Exception as e:
        app_logger.error(f"WebSocket error for {connection_id}: {e}")
    finally:
        # Clean up stream if exists
        if connection_id in manager.connection_streams:
            stream_id = manager.connection_streams[connection_id]
            await streaming_service.close_stream(stream_id)

        manager.disconnect(connection_id)


async def handle_market_data_subscription(
    websocket: WebSocket,
    connection_id: str,
    message: dict,
    streaming_service
):
    """Handle market data subscription request"""
    symbols = message.get("symbols", [])
    if not symbols:
        error_message = {
            "type": "error",
            "message": "No symbols provided for market data subscription",
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(error_message))
        return

    # Create stream configuration
    stream_id = f"market_data_{connection_id}"
    config = StreamConfig(
        stream_id=stream_id,
        latency_threshold_ms=100.0,
        max_buffer_size=1000,
        heartbeat_interval=30.0
    )

    try:
        # Create stream
        await streaming_service.create_stream(config)
        manager.connection_streams[connection_id] = stream_id

        # Subscribe to stream messages
        async def message_callback(stream_message: StreamMessage):
            message_data = {
                "type": "market_data",
                "data": stream_message.data,
                "timestamp": stream_message.timestamp,
                "message_id": stream_message.id
            }
            await manager.send_personal_message(
                json.dumps(message_data), connection_id
            )

        await streaming_service.subscribe(stream_id, message_callback)

        # Start streaming market data
        asyncio.create_task(
            stream_market_data_task(streaming_service, symbols, stream_id)
        )

        # Send confirmation
        confirmation = {
            "type": "subscription_confirmed",
            "subscription": "market_data",
            "symbols": symbols,
            "stream_id": stream_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(confirmation))

    except Exception as e:
        error_message = {
            "type": "error",
            "message": f"Failed to subscribe to market data: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(error_message))


async def handle_analysis_progress_subscription(
    websocket: WebSocket,
    connection_id: str,
    message: dict,
    streaming_service
):
    """Handle analysis progress subscription request"""
    ticker = message.get("ticker")
    if not ticker:
        error_message = {
            "type": "error",
            "message": "No ticker provided for analysis progress subscription",
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(error_message))
        return

    # Create stream configuration
    stream_id = f"analysis_progress_{connection_id}"
    config = StreamConfig(
        stream_id=stream_id,
        latency_threshold_ms=200.0,
        max_buffer_size=100,
        heartbeat_interval=10.0
    )

    try:
        # Create stream
        await streaming_service.create_stream(config)
        manager.connection_streams[connection_id] = stream_id

        # Subscribe to stream messages
        async def message_callback(stream_message: StreamMessage):
            message_data = {
                "type": "analysis_progress",
                "data": stream_message.data,
                "timestamp": stream_message.timestamp,
                "message_id": stream_message.id
            }
            await manager.send_personal_message(
                json.dumps(message_data), connection_id
            )

        await streaming_service.subscribe(stream_id, message_callback)

        # Start streaming analysis progress
        asyncio.create_task(
            stream_analysis_progress_task(streaming_service, ticker, stream_id)
        )

        # Send confirmation
        confirmation = {
            "type": "subscription_confirmed",
            "subscription": "analysis_progress",
            "ticker": ticker,
            "stream_id": stream_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(confirmation))

    except Exception as e:
        error_message = {
            "type": "error",
            "message": f"Failed to subscribe to analysis progress: {str(e)}",
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(error_message))


async def handle_unsubscribe(
    websocket: WebSocket,
    connection_id: str,
    message: dict,
    streaming_service
):
    """Handle unsubscribe request"""
    if connection_id in manager.connection_streams:
        stream_id = manager.connection_streams[connection_id]
        await streaming_service.close_stream(stream_id)
        del manager.connection_streams[connection_id]

        confirmation = {
            "type": "unsubscribed",
            "stream_id": stream_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(confirmation))
    else:
        error_message = {
            "type": "error",
            "message": "No active subscription found",
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(error_message))


async def stream_market_data_task(streaming_service, symbols: list, stream_id: str):
    """Background task to stream market data"""
    try:
        async for message in streaming_service.stream_market_data(symbols, stream_id):
            # Message is automatically sent via callback
            pass
    except Exception as e:
        app_logger.error(f"Error in market data streaming task: {e}")


async def stream_analysis_progress_task(streaming_service, ticker: str, stream_id: str):
    """Background task to stream analysis progress"""
    try:
        async for message in streaming_service.stream_analysis_progress(ticker, stream_id):
            # Message is automatically sent via callback
            pass
    except Exception as e:
        app_logger.error(f"Error in analysis progress streaming task: {e}")


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "active_connections": len(manager.active_connections),
        "active_streams": len(manager.connection_streams),
        "connections": list(manager.active_connections.keys())
    }
