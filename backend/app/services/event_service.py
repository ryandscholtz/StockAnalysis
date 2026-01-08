"""
Event-driven architecture service using AWS EventBridge
"""
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import logging

from app.core.exceptions import ExternalAPIError, BusinessLogicError

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Supported event types"""
    STOCK_ANALYSIS_COMPLETED = "stock.analysis.completed"
    STOCK_ANALYSIS_FAILED = "stock.analysis.failed"
    PDF_PROCESSING_COMPLETED = "pdf.processing.completed"
    PDF_PROCESSING_FAILED = "pdf.processing.failed"
    BATCH_ANALYSIS_STARTED = "batch.analysis.started"
    BATCH_ANALYSIS_COMPLETED = "batch.analysis.completed"
    DATA_QUALITY_ISSUE = "data.quality.issue"
    CACHE_INVALIDATION_REQUIRED = "cache.invalidation.required"


@dataclass
class Event:
    """Event data structure"""
    event_id: str
    event_type: EventType
    source: str
    timestamp: datetime
    data: Dict[str, Any]
    correlation_id: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "correlation_id": self.correlation_id,
            "retry_count": self.retry_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data["data"],
            correlation_id=data.get("correlation_id"),
            retry_count=data.get("retry_count", 0)
        )


class EventHandler:
    """Base class for event handlers"""

    def __init__(self, handler_id: str):
        self.handler_id = handler_id
        self.processed_events: List[str] = []
        self.failed_events: List[str] = []

    async def handle(self, event: Event) -> bool:
        """Handle an event. Return True if successful, False otherwise"""
        try:
            result = await self.process_event(event)
            if result:
                self.processed_events.append(event.event_id)
                logger.info(f"Handler {self.handler_id} successfully processed event {event.event_id}")
            else:
                self.failed_events.append(event.event_id)
                logger.error(f"Handler {self.handler_id} failed to process event {event.event_id}")
            return result
        except Exception as e:
            self.failed_events.append(event.event_id)
            logger.error(f"Handler {self.handler_id} exception processing event {event.event_id}: {e}")
            return False

    async def process_event(self, event: Event) -> bool:
        """Override this method to implement event processing logic"""
        raise NotImplementedError("Subclasses must implement process_event")


class MockEventBridgeService:
    """Mock EventBridge service for testing and development"""

    def __init__(self):
        self.published_events: List[Event] = []
        self.event_handlers: Dict[EventType, List[EventHandler]] = {}
        self.processing_enabled = True
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds

    def register_handler(self, event_type: EventType, handler: EventHandler):
        """Register an event handler for a specific event type"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler {handler.handler_id} for event type {event_type.value}")

    async def publish_event(self, event: Event) -> bool:
        """Publish an event to EventBridge"""
        try:
            # Store the event
            self.published_events.append(event)

            # Process the event if processing is enabled
            if self.processing_enabled:
                await self._process_event(event)

            logger.info(f"Published event {event.event_id} of type {event.event_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_id}: {e}")
            raise ExternalAPIError(f"Failed to publish event: {e}", "eventbridge")

    async def _process_event(self, event: Event):
        """Process an event by calling all registered handlers"""
        handlers = self.event_handlers.get(event.event_type, [])

        if not handlers:
            logger.warning(f"No handlers registered for event type {event.event_type.value}")
            return

        # Process event with all handlers
        for handler in handlers:
            success = await self._process_with_retry(handler, event)
            if not success:
                logger.error(f"Handler {handler.handler_id} failed to process event {event.event_id} after retries")

    async def _process_with_retry(self, handler: EventHandler, event: Event) -> bool:
        """Process event with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                success = await handler.handle(event)
                if success:
                    return True

                if attempt < self.max_retries:
                    logger.info(f"Retrying handler {handler.handler_id} for event {event.event_id}, attempt {attempt + 1}")
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff

            except Exception as e:
                logger.error(f"Handler {handler.handler_id} exception on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))

        return False

    def get_published_events(self, event_type: Optional[EventType] = None) -> List[Event]:
        """Get published events, optionally filtered by type"""
        if event_type is None:
            return self.published_events.copy()
        return [e for e in self.published_events if e.event_type == event_type]

    def clear_events(self):
        """Clear all published events (for testing)"""
        self.published_events.clear()

    def set_processing_enabled(self, enabled: bool):
        """Enable or disable event processing (for testing)"""
        self.processing_enabled = enabled


class StockAnalysisEventHandler(EventHandler):
    """Handler for stock analysis events"""

    def __init__(self):
        super().__init__("stock_analysis_handler")
        self.analysis_results: Dict[str, Any] = {}

    async def process_event(self, event: Event) -> bool:
        """Process stock analysis events"""
        if event.event_type == EventType.STOCK_ANALYSIS_COMPLETED:
            ticker = event.data.get("ticker")
            if not ticker:
                return False

            self.analysis_results[ticker] = {
                "status": "completed",
                "timestamp": event.timestamp,
                "data": event.data
            }
            return True

        elif event.event_type == EventType.STOCK_ANALYSIS_FAILED:
            ticker = event.data.get("ticker")
            if not ticker:
                return False

            self.analysis_results[ticker] = {
                "status": "failed",
                "timestamp": event.timestamp,
                "error": event.data.get("error", "Unknown error")
            }
            return True

        return False


class CacheInvalidationEventHandler(EventHandler):
    """Handler for cache invalidation events"""

    def __init__(self):
        super().__init__("cache_invalidation_handler")
        self.invalidated_keys: List[str] = []

    async def process_event(self, event: Event) -> bool:
        """Process cache invalidation events"""
        if event.event_type == EventType.CACHE_INVALIDATION_REQUIRED:
            cache_keys = event.data.get("cache_keys", [])
            if not cache_keys:
                return False

            # Simulate cache invalidation
            self.invalidated_keys.extend(cache_keys)
            return True

        return False


class DataQualityEventHandler(EventHandler):
    """Handler for data quality events"""

    def __init__(self):
        super().__init__("data_quality_handler")
        self.quality_issues: List[Dict[str, Any]] = []

    async def process_event(self, event: Event) -> bool:
        """Process data quality events"""
        if event.event_type == EventType.DATA_QUALITY_ISSUE:
            issue_data = event.data.get("issue")
            if not issue_data:
                return False

            self.quality_issues.append({
                "timestamp": event.timestamp,
                "issue": issue_data,
                "source": event.source
            })
            return True

        return False


# Global event service instance
event_service = MockEventBridgeService()

# Register default handlers
event_service.register_handler(EventType.STOCK_ANALYSIS_COMPLETED, StockAnalysisEventHandler())
event_service.register_handler(EventType.STOCK_ANALYSIS_FAILED, StockAnalysisEventHandler())
event_service.register_handler(EventType.CACHE_INVALIDATION_REQUIRED, CacheInvalidationEventHandler())
event_service.register_handler(EventType.DATA_QUALITY_ISSUE, DataQualityEventHandler())


async def publish_stock_analysis_completed(ticker: str, analysis_data: Dict[str, Any], correlation_id: Optional[str] = None):
    """Convenience function to publish stock analysis completed event"""
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.STOCK_ANALYSIS_COMPLETED,
        source="stock_analysis_service",
        timestamp=datetime.now(),
        data={"ticker": ticker, "analysis": analysis_data},
        correlation_id=correlation_id
    )
    await event_service.publish_event(event)


async def publish_data_quality_issue(issue_description: str, affected_data: Dict[str, Any], correlation_id: Optional[str] = None):
    """Convenience function to publish data quality issue event"""
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.DATA_QUALITY_ISSUE,
        source="data_validation_service",
        timestamp=datetime.now(),
        data={"issue": issue_description, "affected_data": affected_data},
        correlation_id=correlation_id
    )
    await event_service.publish_event(event)


async def publish_cache_invalidation_required(cache_keys: List[str], reason: str, correlation_id: Optional[str] = None):
    """Convenience function to publish cache invalidation event"""
    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=EventType.CACHE_INVALIDATION_REQUIRED,
        source="cache_manager",
        timestamp=datetime.now(),
        data={"cache_keys": cache_keys, "reason": reason},
        correlation_id=correlation_id
    )
    await event_service.publish_event(event)
