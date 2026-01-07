"""
Property-based tests for event-driven architecture reliability
Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
"""
import pytest
from hypothesis import given, strategies as st, settings
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import uuid

from app.services.event_service import (
    Event,
    EventType,
    EventHandler,
    MockEventBridgeService,
    StockAnalysisEventHandler,
    CacheInvalidationEventHandler,
    DataQualityEventHandler)

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


class _TestEventHandler(EventHandler):
    """Test event handler for property testing"""

    def __init__(self, handler_id: str, should_fail: bool = False):
        super().__init__(handler_id)
        self.should_fail = should_fail
        self.processed_data: List[Dict[str, Any]] = []

    async def process_event(self, event: Event) -> bool:
        """Process event - can be configured to fail for testing"""
        if self.should_fail:
            return False

        self.processed_data.append(event.data)
        return True


class TestEventDrivenArchitectureReliability:
    """Test that event-driven architecture reliably processes events without data loss"""

    @given(
        event_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20).filter(
                lambda x: x.isidentifier()),
            values=st.one_of(
                st.text(
                    max_size=100),
                st.integers(
                    min_value=0,
                    max_value=1000000),
                st.floats(
                    min_value=0.0,
                    max_value=1000000.0,
                    allow_nan=False,
                    allow_infinity=False),
                st.booleans()),
            min_size=1,
            max_size=5),
        event_type=st.sampled_from(
            list(EventType)),
        source=st.text(
            min_size=1,
            max_size=50),
        num_handlers=st.integers(
            min_value=1,
            max_value=5))
    @settings(max_examples=100)
    def test_event_processing_without_data_loss(
        self,
        event_data: Dict[str, Any],
        event_type: EventType,
        source: str,
        num_handlers: int
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any event published to EventBridge, the event should be processed by all registered handlers without data loss
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service for this test
            event_service = MockEventBridgeService()

            # Register multiple handlers for the event type
            handlers = []
            for i in range(num_handlers):
                handler = _TestEventHandler(f"test_handler_{i}")
                handlers.append(handler)
                event_service.register_handler(event_type, handler)

            # Create and publish event
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                source=source,
                timestamp=datetime.now(),
                data=event_data,
                correlation_id=str(uuid.uuid4())
            )

            # Publish event
            success = await event_service.publish_event(event)
            assert success, "Event publishing should succeed"

            # Verify event was stored
            published_events = event_service.get_published_events(event_type)
            assert len(published_events) == 1
            assert published_events[0].event_id == event.event_id
            assert published_events[0].data == event_data

            # Verify all handlers processed the event
            for handler in handlers:
                assert event.event_id in handler.processed_events
                assert event.event_id not in handler.failed_events
                assert len(handler.processed_data) == 1
                assert handler.processed_data[0] == event_data

        # Run the async test
        asyncio.run(run_test())

    @given(
        events_data=st.lists(
            st.dictionaries(
                keys=st.text(
                    min_size=1,
                    max_size=20).filter(
                    lambda x: x.isidentifier()),
                values=st.one_of(
                    st.text(
                        max_size=50),
                    st.integers(
                        min_value=0,
                        max_value=1000)),
                min_size=1,
                max_size=3),
            min_size=1,
            max_size=10),
        event_type=st.sampled_from(
            list(EventType)))
    @settings(max_examples=100)
    def test_multiple_events_processing_reliability(
        self,
        events_data: List[Dict[str, Any]],
        event_type: EventType
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any sequence of events, all events should be processed reliably in order
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service
            event_service = MockEventBridgeService()

            # Register handler
            handler = _TestEventHandler("sequence_handler")
            event_service.register_handler(event_type, handler)

            # Publish all events
            event_ids = []
            for i, data in enumerate(events_data):
                event = Event(
                    event_id=str(uuid.uuid4()),
                    event_type=event_type,
                    source=f"test_source_{i}",
                    timestamp=datetime.now(),
                    data=data,
                    correlation_id=str(uuid.uuid4())
                )
                event_ids.append(event.event_id)

                success = await event_service.publish_event(event)
                assert success, f"Event {i} publishing should succeed"

            # Verify all events were processed
            assert len(handler.processed_events) == len(events_data)
            assert len(handler.processed_data) == len(events_data)

            # Verify no events failed
            assert len(handler.failed_events) == 0

            # Verify all event IDs were processed
            for event_id in event_ids:
                assert event_id in handler.processed_events

            # Verify data integrity
            for i, expected_data in enumerate(events_data):
                assert handler.processed_data[i] == expected_data

        # Run the async test
        asyncio.run(run_test())

    @given(
        event_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.text(max_size=50),
            min_size=1,
            max_size=3
        ),
        num_successful_handlers=st.integers(min_value=1, max_value=3),
        num_failing_handlers=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100, deadline=None)  # Disable deadline for this test
    def test_partial_handler_failure_resilience(
        self,
        event_data: Dict[str, Any],
        num_successful_handlers: int,
        num_failing_handlers: int
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any event with mixed handler success/failure, successful handlers should still process the event
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service with reduced retry settings
            event_service = MockEventBridgeService()
            event_service.max_retries = 1  # Reduce retries for faster testing
            event_service.retry_delay = 0.01  # Reduce delay for faster testing

            # Register successful handlers
            successful_handlers = []
            for i in range(num_successful_handlers):
                handler = _TestEventHandler(f"success_handler_{i}", should_fail=False)
                successful_handlers.append(handler)
                event_service.register_handler(
                    EventType.STOCK_ANALYSIS_COMPLETED, handler)

            # Register failing handlers
            failing_handlers = []
            for i in range(num_failing_handlers):
                handler = _TestEventHandler(f"failing_handler_{i}", should_fail=True)
                failing_handlers.append(handler)
                event_service.register_handler(
                    EventType.STOCK_ANALYSIS_COMPLETED, handler)

            # Create and publish event
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.STOCK_ANALYSIS_COMPLETED,
                source="test_source",
                timestamp=datetime.now(),
                data=event_data,
                correlation_id=str(uuid.uuid4())
            )

            success = await event_service.publish_event(event)
            assert success, "Event publishing should succeed even with failing handlers"

            # Verify successful handlers processed the event
            for handler in successful_handlers:
                assert event.event_id in handler.processed_events
                assert event.event_id not in handler.failed_events
                assert len(handler.processed_data) == 1
                assert handler.processed_data[0] == event_data

            # Verify failing handlers failed as expected
            for handler in failing_handlers:
                assert event.event_id not in handler.processed_events
                assert event.event_id in handler.failed_events
                assert len(handler.processed_data) == 0

        # Run the async test
        asyncio.run(run_test())

    @given(
        ticker=st.text(min_size=1, max_size=10).filter(lambda x: x.isalnum()),
        analysis_data=st.dictionaries(
            keys=st.sampled_from(["fair_value", "current_price", "recommendation", "score"]),
            values=st.one_of(
                st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
                st.text(min_size=1, max_size=20),
                st.integers(min_value=1, max_value=10)
            ),
            min_size=1,
            max_size=4
        )
    )
    @settings(max_examples=100)
    def test_stock_analysis_event_handler_reliability(
        self,
        ticker: str,
        analysis_data: Dict[str, Any]
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any stock analysis completion event, the handler should reliably process and store the results
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service with stock analysis handler
            event_service = MockEventBridgeService()
            handler = StockAnalysisEventHandler()
            event_service.register_handler(EventType.STOCK_ANALYSIS_COMPLETED, handler)

            # Create and publish event directly (not using global convenience function)
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.STOCK_ANALYSIS_COMPLETED,
                source="stock_analysis_service",
                timestamp=datetime.now(),
                data={"ticker": ticker, "analysis": analysis_data},
                correlation_id=str(uuid.uuid4())
            )

            await event_service.publish_event(event)

            # Wait a moment for processing
            await asyncio.sleep(0.1)

            # Verify handler processed the event
            assert ticker in handler.analysis_results
            result = handler.analysis_results[ticker]
            assert result["status"] == "completed"
            assert result["data"]["ticker"] == ticker
            assert result["data"]["analysis"] == analysis_data

            # Verify event was published
            published_events = event_service.get_published_events(
                EventType.STOCK_ANALYSIS_COMPLETED)
            assert len(published_events) == 1
            assert published_events[0].data["ticker"] == ticker
            assert published_events[0].correlation_id == event.correlation_id

        # Run the async test
        asyncio.run(run_test())

    @given(
        cache_keys=st.lists(
            st.text(min_size=1, max_size=50).filter(lambda x: ":" in x or x.isalnum()),
            min_size=1,
            max_size=10
        ),
        reason=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100)
    def test_cache_invalidation_event_reliability(
        self,
        cache_keys: List[str],
        reason: str
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any cache invalidation event, the handler should reliably invalidate all specified keys
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service with cache invalidation handler
            event_service = MockEventBridgeService()
            handler = CacheInvalidationEventHandler()
            event_service.register_handler(
                EventType.CACHE_INVALIDATION_REQUIRED, handler)

            # Create and publish event directly
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.CACHE_INVALIDATION_REQUIRED,
                source="cache_manager",
                timestamp=datetime.now(),
                data={"cache_keys": cache_keys, "reason": reason},
                correlation_id=str(uuid.uuid4())
            )

            await event_service.publish_event(event)

            # Wait a moment for processing
            await asyncio.sleep(0.1)

            # Verify handler processed all cache keys
            for key in cache_keys:
                assert key in handler.invalidated_keys

            # Verify event was published
            published_events = event_service.get_published_events(
                EventType.CACHE_INVALIDATION_REQUIRED)
            assert len(published_events) == 1
            assert published_events[0].data["cache_keys"] == cache_keys
            assert published_events[0].data["reason"] == reason
            assert published_events[0].correlation_id == event.correlation_id

        # Run the async test
        asyncio.run(run_test())

    @given(
        issue_description=st.text(min_size=1, max_size=200),
        affected_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_data_quality_event_reliability(
        self,
        issue_description: str,
        affected_data: Dict[str, Any]
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any data quality issue event, the handler should reliably record the issue for investigation
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service with data quality handler
            event_service = MockEventBridgeService()
            handler = DataQualityEventHandler()
            event_service.register_handler(EventType.DATA_QUALITY_ISSUE, handler)

            # Create and publish event directly
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=EventType.DATA_QUALITY_ISSUE,
                source="data_validation_service",
                timestamp=datetime.now(),
                data={"issue": issue_description, "affected_data": affected_data},
                correlation_id=str(uuid.uuid4())
            )

            await event_service.publish_event(event)

            # Wait a moment for processing
            await asyncio.sleep(0.1)

            # Verify handler recorded the issue
            assert len(handler.quality_issues) == 1
            issue = handler.quality_issues[0]
            assert issue["issue"] == issue_description
            assert issue["source"] == "data_validation_service"

            # Verify event was published
            published_events = event_service.get_published_events(
                EventType.DATA_QUALITY_ISSUE)
            assert len(published_events) == 1
            assert published_events[0].data["issue"] == issue_description
            assert published_events[0].data["affected_data"] == affected_data
            assert published_events[0].correlation_id == event.correlation_id

        # Run the async test
        asyncio.run(run_test())

    @given(
        event_count=st.integers(min_value=1, max_value=20),
        handler_count=st.integers(min_value=1, max_value=5)
    )
    @settings(max_examples=50)
    def test_high_volume_event_processing_reliability(
        self,
        event_count: int,
        handler_count: int
    ):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any high volume of events, all events should be processed by all handlers without loss
        **Validates: Requirements 10.2**
        """
        async def run_test():
            # Create fresh event service
            event_service = MockEventBridgeService()

            # Register multiple handlers
            handlers = []
            for i in range(handler_count):
                handler = _TestEventHandler(f"volume_handler_{i}")
                handlers.append(handler)
                event_service.register_handler(
                    EventType.BATCH_ANALYSIS_COMPLETED, handler)

            # Publish many events concurrently
            tasks = []
            event_ids = []

            for i in range(event_count):
                event = Event(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.BATCH_ANALYSIS_COMPLETED,
                    source=f"batch_source_{i}",
                    timestamp=datetime.now(),
                    data={"batch_id": i, "status": "completed"},
                    correlation_id=str(uuid.uuid4())
                )
                event_ids.append(event.event_id)
                tasks.append(event_service.publish_event(event))

            # Wait for all events to be published and processed
            results = await asyncio.gather(*tasks)
            assert all(results), "All events should be published successfully"

            # Verify all handlers processed all events
            for handler in handlers:
                assert len(handler.processed_events) == event_count
                assert len(handler.failed_events) == 0
                assert len(handler.processed_data) == event_count

                # Verify all event IDs were processed
                for event_id in event_ids:
                    assert event_id in handler.processed_events

            # Verify all events were stored
            published_events = event_service.get_published_events(
                EventType.BATCH_ANALYSIS_COMPLETED)
            assert len(published_events) == event_count

        # Run the async test
        asyncio.run(run_test())

    def test_event_serialization_reliability(self):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        For any event, serialization and deserialization should preserve all data without loss
        **Validates: Requirements 10.2**
        """
        # Create test event
        original_event = Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.STOCK_ANALYSIS_COMPLETED,
            source="test_source",
            timestamp=datetime.now(),
            data={"ticker": "AAPL", "price": 150.0, "analysis": {"score": 8.5}},
            correlation_id=str(uuid.uuid4()),
            retry_count=2
        )

        # Serialize to dictionary
        event_dict = original_event.to_dict()

        # Deserialize back to event
        restored_event = Event.from_dict(event_dict)

        # Verify all fields are preserved
        assert restored_event.event_id == original_event.event_id
        assert restored_event.event_type == original_event.event_type
        assert restored_event.source == original_event.source
        assert restored_event.timestamp == original_event.timestamp
        assert restored_event.data == original_event.data
        assert restored_event.correlation_id == original_event.correlation_id
        assert restored_event.retry_count == original_event.retry_count

    @pytest.mark.asyncio
    async def test_event_processing_disabled_reliability(self):
        """
        Feature: tech-stack-modernization, Property 22: Event-Driven Architecture Reliability
        When event processing is disabled, events should still be stored for later processing
        **Validates: Requirements 10.2**
        """
        # Create event service with processing disabled
        event_service = MockEventBridgeService()
        event_service.set_processing_enabled(False)

        handler = _TestEventHandler("disabled_handler")
        event_service.register_handler(EventType.STOCK_ANALYSIS_COMPLETED, handler)

        # Publish event
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=EventType.STOCK_ANALYSIS_COMPLETED,
            source="test_source",
            timestamp=datetime.now(),
            data={"ticker": "AAPL"},
            correlation_id=str(uuid.uuid4())
        )

        success = await event_service.publish_event(event)
        assert success, "Event should be published even when processing is disabled"

        # Verify event was stored but not processed
        published_events = event_service.get_published_events()
        assert len(published_events) == 1
        assert len(handler.processed_events) == 0

        # Enable processing and verify event can be processed later
        event_service.set_processing_enabled(True)
        await event_service._process_event(event)

        # Now handler should have processed the event
        assert len(handler.processed_events) == 1
        assert event.event_id in handler.processed_events
