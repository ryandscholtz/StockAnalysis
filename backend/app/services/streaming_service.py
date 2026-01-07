"""
Real-time streaming service for market data and analysis updates
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, asdict
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels for streaming"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class StreamStatus(Enum):
    """Stream status enumeration"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"


@dataclass
class StreamMessage:
    """Stream message data structure"""
    id: str
    type: str
    data: Dict[str, Any]
    timestamp: float
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "id": self.id,
            "type": self.type,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value
        })


@dataclass
class StreamConfig:
    """Stream configuration"""
    stream_id: str
    latency_threshold_ms: float = 100.0
    max_buffer_size: int = 1000
    heartbeat_interval: float = 30.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_compression: bool = True
    message_ordering: bool = True


class StreamingService:
    """Real-time streaming service for market data and analysis updates"""
    
    def __init__(self):
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.message_buffer: Dict[str, List[StreamMessage]] = {}
        self.stream_configs: Dict[str, StreamConfig] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        
    async def create_stream(self, config: StreamConfig) -> str:
        """Create a new streaming connection"""
        stream_id = config.stream_id
        
        self.stream_configs[stream_id] = config
        self.active_streams[stream_id] = {
            "status": StreamStatus.INITIALIZING,
            "created_at": time.time(),
            "last_message": None,
            "message_count": 0,
            "error_count": 0
        }
        self.message_buffer[stream_id] = []
        self.subscribers[stream_id] = []
        
        # Mark stream as active
        self.active_streams[stream_id]["status"] = StreamStatus.ACTIVE
        
        logger.info(f"Created stream {stream_id}")
        return stream_id
    
    async def send_message(self, stream_id: str, message: StreamMessage) -> bool:
        """Send a message to a stream"""
        if stream_id not in self.active_streams:
            logger.error(f"Stream {stream_id} not found")
            return False
        
        stream_info = self.active_streams[stream_id]
        if stream_info["status"] != StreamStatus.ACTIVE:
            logger.warning(f"Stream {stream_id} is not active (status: {stream_info['status']})")
            return False
        
        config = self.stream_configs[stream_id]
        
        # Check buffer size
        if len(self.message_buffer[stream_id]) >= config.max_buffer_size:
            # Remove oldest message if buffer is full
            self.message_buffer[stream_id].pop(0)
        
        # Add message to buffer
        self.message_buffer[stream_id].append(message)
        
        # Update stream info
        stream_info["last_message"] = time.time()
        stream_info["message_count"] += 1
        
        # Notify subscribers
        for callback in self.subscribers[stream_id]:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")
                stream_info["error_count"] += 1
        
        return True
    
    async def subscribe(self, stream_id: str, callback: Callable) -> bool:
        """Subscribe to stream messages"""
        if stream_id not in self.active_streams:
            return False
        
        self.subscribers[stream_id].append(callback)
        return True
    
    async def get_stream_messages(self, stream_id: str, since: Optional[float] = None) -> List[StreamMessage]:
        """Get messages from stream buffer"""
        if stream_id not in self.message_buffer:
            return []
        
        messages = self.message_buffer[stream_id]
        if since is not None:
            messages = [msg for msg in messages if msg.timestamp > since]
        
        return messages
    
    async def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """Get stream status information"""
        if stream_id not in self.active_streams:
            return None
        
        stream_info = self.active_streams[stream_id].copy()
        config = self.stream_configs[stream_id]
        
        # Calculate latency metrics
        current_time = time.time()
        last_message_time = stream_info.get("last_message")
        latency = None
        if last_message_time:
            latency = (current_time - last_message_time) * 1000  # Convert to ms
        
        return {
            "stream_id": stream_id,
            "status": stream_info["status"].value,
            "created_at": stream_info["created_at"],
            "message_count": stream_info["message_count"],
            "error_count": stream_info["error_count"],
            "buffer_size": len(self.message_buffer[stream_id]),
            "latency_ms": latency,
            "latency_threshold_ms": config.latency_threshold_ms,
            "within_threshold": latency is None or latency <= config.latency_threshold_ms
        }
    
    async def close_stream(self, stream_id: str) -> bool:
        """Close a streaming connection"""
        if stream_id not in self.active_streams:
            return False
        
        self.active_streams[stream_id]["status"] = StreamStatus.COMPLETED
        
        # Clean up resources
        if stream_id in self.message_buffer:
            del self.message_buffer[stream_id]
        if stream_id in self.subscribers:
            del self.subscribers[stream_id]
        if stream_id in self.stream_configs:
            del self.stream_configs[stream_id]
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
        
        logger.info(f"Closed stream {stream_id}")
        return True
    
    async def stream_market_data(self, symbols: List[str], stream_id: str) -> AsyncGenerator[StreamMessage, None]:
        """Stream real-time market data for given symbols"""
        config = self.stream_configs.get(stream_id)
        if not config:
            raise ValueError(f"Stream {stream_id} not configured")
        
        message_id = 0
        start_time = time.time()
        
        try:
            while self.active_streams[stream_id]["status"] == StreamStatus.ACTIVE:
                for symbol in symbols:
                    # Simulate market data (in real implementation, this would fetch from market data provider)
                    market_data = {
                        "symbol": symbol,
                        "price": 100.0 + (time.time() % 10),  # Simulated price
                        "volume": 1000,
                        "timestamp": time.time()
                    }
                    
                    message = StreamMessage(
                        id=f"{stream_id}_{message_id}",
                        type="market_data",
                        data=market_data,
                        timestamp=time.time(),
                        priority=MessagePriority.HIGH
                    )
                    
                    # Check latency
                    processing_time = (time.time() - start_time) * 1000
                    if processing_time > config.latency_threshold_ms:
                        logger.warning(f"Stream {stream_id} latency exceeded threshold: {processing_time}ms")
                    
                    await self.send_message(stream_id, message)
                    yield message
                    
                    message_id += 1
                
                # Wait before next update
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in market data stream {stream_id}: {e}")
            self.active_streams[stream_id]["status"] = StreamStatus.ERROR
            raise
    
    async def stream_analysis_progress(self, ticker: str, stream_id: str) -> AsyncGenerator[StreamMessage, None]:
        """Stream analysis progress updates"""
        config = self.stream_configs.get(stream_id)
        if not config:
            raise ValueError(f"Stream {stream_id} not configured")
        
        message_id = 0
        progress_steps = [
            "Fetching company data",
            "Analyzing financial health",
            "Calculating valuation",
            "Generating recommendations"
        ]
        
        try:
            for i, step in enumerate(progress_steps):
                progress_data = {
                    "ticker": ticker,
                    "step": i + 1,
                    "total_steps": len(progress_steps),
                    "description": step,
                    "progress_percent": ((i + 1) / len(progress_steps)) * 100
                }
                
                message = StreamMessage(
                    id=f"{stream_id}_{message_id}",
                    type="analysis_progress",
                    data=progress_data,
                    timestamp=time.time(),
                    priority=MessagePriority.NORMAL
                )
                
                await self.send_message(stream_id, message)
                yield message
                
                message_id += 1
                await asyncio.sleep(0.5)  # Simulate processing time
                
        except Exception as e:
            logger.error(f"Error in analysis progress stream {stream_id}: {e}")
            self.active_streams[stream_id]["status"] = StreamStatus.ERROR
            raise


# Global streaming service instance
_streaming_service = None


def get_streaming_service() -> StreamingService:
    """Get the global streaming service instance"""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service