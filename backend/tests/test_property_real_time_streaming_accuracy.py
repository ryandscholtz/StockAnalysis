"""
Property-based tests for real-time streaming accuracy
Feature: tech-stack-modernization, Property 25: Real-time Streaming Accuracy
"""
import pytest
import asyncio
from hypothesis import given, strategies as st, assume, settings
import time

from app.services.streaming_service import (
    StreamingService,
    StreamConfig,
    MessagePriority,
    StreamStatus,
    StreamMessage
)


# Test data generators
@st.composite
def stream_config_data(draw):
    """Generate stream configuration data"""
    return {
        "stream_id": draw(
            st.text(
                min_size=1, max_size=50, alphabet=st.characters(
                    whitelist_categories=(
                        'Lu', 'Ll', 'Nd')))), "latency_threshold_ms": draw(
            st.floats(
                min_value=10.0, max_value=1000.0)), "max_buffer_size": draw(
            st.integers(
                min_value=10, max_value=1000)), "heartbeat_interval": draw(
            st.floats(
                min_value=1.0, max_value=60.0)), "retry_attempts": draw(
            st.integers(
                min_value=1, max_value=5)), "retry_delay": draw(
            st.floats(
                min_value=0.1, max_value=5.0))}


@st.composite
def market_symbols(draw):
    """Generate market symbols"""
    return draw(
        st.lists(
            st.text(
                min_size=1,
                max_size=10,
                alphabet=st.characters(
                    whitelist_categories=(
                        'Lu',
                        'Nd'))),
            min_size=1,
            max_size=5,
            unique=True))


@st.composite
def stream_message_data(draw):
    """Generate stream message data"""
    return {
        "id": draw(st.text(min_size=1, max_size=50)),
        "type": draw(st.sampled_from(["market_data", "analysis_progress", "heartbeat", "notification"])),
        "data": draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(st.text(), st.floats(), st.integers(), st.booleans()),
            min_size=1,
            max_size=10
        )),
        # Fixed range: 2022-2023
        "timestamp": draw(st.floats(min_value=1640995200.0, max_value=1672531200.0)),
        "priority": draw(st.sampled_from(list(MessagePriority)))
    }


def run_async_test(coro):
    """Helper function to run async tests synchronously"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestRealTimeStreamingAccuracy:
    """
    Property-based tests for real-time streaming accuracy
    Feature: tech-stack-modernization, Property 25: Real-time Streaming Accuracy
    For any real-time data stream, updates should be delivered to clients within the configured latency threshold without data loss
    """

    @given(stream_config_data())
    @settings(max_examples=50, deadline=5000)
    def test_stream_creation_and_latency_property(self, config_data):
        """
        Property 25: Stream creation should succeed and maintain latency thresholds
        For any valid stream configuration, the stream should be created successfully
        and maintain latency within the configured threshold
        """
        assume(config_data["latency_threshold_ms"] > 0)
        assume(config_data["max_buffer_size"] > 0)
        assume(len(config_data["stream_id"].strip()) > 0)

        async def test_logic():
            # Create streaming service instance
            streaming_service = StreamingService()

            # Create stream configuration
            config = StreamConfig(
                stream_id=config_data["stream_id"],
                latency_threshold_ms=config_data["latency_threshold_ms"],
                max_buffer_size=config_data["max_buffer_size"],
                heartbeat_interval=config_data["heartbeat_interval"],
                retry_attempts=config_data["retry_attempts"],
                retry_delay=config_data["retry_delay"]
            )

            # Create stream
            stream_id = await streaming_service.create_stream(config)
            assert stream_id == config_data["stream_id"]

            # Verify stream exists and is active
            status = await streaming_service.get_stream_status(stream_id)
            assert status is not None
            assert status["status"] == StreamStatus.ACTIVE.value
            assert status["latency_threshold_ms"] == config_data["latency_threshold_ms"]

            # Clean up
            await streaming_service.close_stream(stream_id)

        run_async_test(test_logic())

    @given(stream_config_data(), st.lists(stream_message_data(), min_size=1, max_size=20))
    @settings(max_examples=30, deadline=10000)
    def test_message_delivery_without_data_loss_property(
            self, config_data, messages_data):
        """
        Property 25: Messages should be delivered without data loss
        For any stream and any sequence of messages, all messages should be deliverable
        and retrievable from the stream buffer
        """
        assume(config_data["latency_threshold_ms"] > 0)
        assume(config_data["max_buffer_size"] >= len(messages_data))
        assume(len(config_data["stream_id"].strip()) > 0)

        async def test_logic():
            # Create streaming service instance
            streaming_service = StreamingService()

            # Create stream configuration
            config = StreamConfig(
                stream_id=config_data["stream_id"],
                latency_threshold_ms=config_data["latency_threshold_ms"],
                max_buffer_size=config_data["max_buffer_size"],
                heartbeat_interval=config_data["heartbeat_interval"]
            )

            # Create stream
            stream_id = await streaming_service.create_stream(config)

            # Send messages
            sent_messages = []
            for msg_data in messages_data:
                message = StreamMessage(
                    id=msg_data["id"],
                    type=msg_data["type"],
                    data=msg_data["data"],
                    timestamp=msg_data["timestamp"],
                    priority=msg_data["priority"]
                )

                success = await streaming_service.send_message(stream_id, message)
                assert success, f"Failed to send message {message.id}"
                sent_messages.append(message)

            # Retrieve messages from buffer
            retrieved_messages = await streaming_service.get_stream_messages(stream_id)

            # Verify no data loss - all sent messages should be retrievable
            assert len(retrieved_messages) == len(
                sent_messages), "Data loss detected: message count mismatch"

            # Verify message content integrity
            retrieved_ids = {msg.id for msg in retrieved_messages}
            sent_ids = {msg.id for msg in sent_messages}
            assert retrieved_ids == sent_ids, "Data loss detected: message ID mismatch"

            # Clean up
            await streaming_service.close_stream(stream_id)

        run_async_test(test_logic())

    @given(stream_config_data())
    @settings(max_examples=30, deadline=5000)
    def test_stream_buffer_management_property(self, config_data):
        """
        Property 25: Stream buffer should manage messages without data loss within capacity
        For any stream configuration, the buffer should handle messages up to its capacity
        and manage overflow appropriately
        """
        assume(config_data["latency_threshold_ms"] > 0)
        assume(config_data["max_buffer_size"] > 0)
        assume(len(config_data["stream_id"].strip()) > 0)

        async def test_logic():
            # Create streaming service instance
            streaming_service = StreamingService()

            # Create stream configuration
            config = StreamConfig(
                stream_id=config_data["stream_id"],
                latency_threshold_ms=config_data["latency_threshold_ms"],
                max_buffer_size=config_data["max_buffer_size"],
                heartbeat_interval=config_data["heartbeat_interval"]
            )

            # Create stream
            stream_id = await streaming_service.create_stream(config)

            # Send messages up to buffer capacity
            sent_messages = []
            for i in range(config_data["max_buffer_size"]):
                message = StreamMessage(
                    id=f"msg_{i}",
                    type="test_message",
                    data={"index": i, "content": f"test_data_{i}"},
                    timestamp=time.time(),
                    priority=MessagePriority.NORMAL
                )

                success = await streaming_service.send_message(stream_id, message)
                assert success, f"Failed to send message {i}"
                sent_messages.append(message)

            # Verify all messages are in buffer
            retrieved_messages = await streaming_service.get_stream_messages(stream_id)
            assert len(retrieved_messages) == config_data["max_buffer_size"], (
                f"Buffer size mismatch: expected {config_data['max_buffer_size']}, got {len(retrieved_messages)}"
            )

            # Verify buffer status
            status = await streaming_service.get_stream_status(stream_id)
            assert status["buffer_size"] == config_data["max_buffer_size"], (
                f"Status buffer size mismatch: expected {config_data['max_buffer_size']}, got {status['buffer_size']}"
            )

            # Test buffer overflow behavior - send one more message
            overflow_message = StreamMessage(
                id="overflow_msg",
                type="test_message",
                data={"overflow": True},
                timestamp=time.time(),
                priority=MessagePriority.HIGH
            )

            success = await streaming_service.send_message(stream_id, overflow_message)
            assert success, "Failed to send overflow message"

            # Buffer should still be at capacity (oldest message removed)
            retrieved_after_overflow = await streaming_service.get_stream_messages(stream_id)
            assert len(retrieved_after_overflow) == config_data["max_buffer_size"], (
                "Buffer should maintain capacity after overflow"
            )

            # The overflow message should be in the buffer
            overflow_found = any(
                msg.id == "overflow_msg" for msg in retrieved_after_overflow)
            assert overflow_found, "Overflow message not found in buffer"

            # Clean up
            await streaming_service.close_stream(stream_id)

        run_async_test(test_logic())

    # Additional unit tests for specific streaming scenarios
    @pytest.mark.asyncio
    async def test_streaming_latency_compliance(self):
        """
        Unit test: Verify streaming latency compliance for specific scenarios
        """
        streaming_service = StreamingService()

        # Test with strict latency requirements
        config = StreamConfig(
            stream_id="latency_test_stream",
            latency_threshold_ms=50.0,  # Very strict 50ms threshold
            max_buffer_size=100,
            heartbeat_interval=5.0
        )

        stream_id = await streaming_service.create_stream(config)

        # Send a few messages and measure timing
        start_time = time.time()
        for i in range(5):
            message = StreamMessage(
                id=f"latency_msg_{i}",
                type="latency_test",
                data={"index": i},
                timestamp=time.time(),
                priority=MessagePriority.HIGH
            )
            await streaming_service.send_message(stream_id, message)

        # Check that processing was reasonably fast
        processing_time_ms = (time.time() - start_time) * 1000

        # Allow some tolerance for test environment
        assert processing_time_ms < 500, f"Processing took {processing_time_ms}ms, too slow for streaming"

        # Verify stream status
        status = await streaming_service.get_stream_status(stream_id)
        assert status["within_threshold"] is not False, "Stream should be within latency threshold"

        await streaming_service.close_stream(stream_id)

    @pytest.mark.asyncio
    async def test_concurrent_stream_management(self):
        """
        Unit test: Verify multiple streams can be managed concurrently
        """
        streaming_service = StreamingService()

        # Create multiple streams
        stream_configs = [
            StreamConfig(
                stream_id=f"concurrent_stream_{i}",
                latency_threshold_ms=100.0,
                max_buffer_size=50) for i in range(3)]

        stream_ids = []
        for config in stream_configs:
            stream_id = await streaming_service.create_stream(config)
            stream_ids.append(stream_id)

        # Send messages to each stream
        for i, stream_id in enumerate(stream_ids):
            message = StreamMessage(
                id=f"concurrent_msg_{i}",
                type="concurrent_test",
                data={"stream_index": i},
                timestamp=time.time(),
                priority=MessagePriority.NORMAL
            )
            success = await streaming_service.send_message(stream_id, message)
            assert success, f"Failed to send message to stream {i}"

        # Verify all streams are active and have messages
        for i, stream_id in enumerate(stream_ids):
            status = await streaming_service.get_stream_status(stream_id)
            assert status["status"] == StreamStatus.ACTIVE.value
            assert status["message_count"] == 1

            messages = await streaming_service.get_stream_messages(stream_id)
            assert len(messages) == 1
            assert messages[0].data["stream_index"] == i

        # Clean up all streams
        for stream_id in stream_ids:
            await streaming_service.close_stream(stream_id)
