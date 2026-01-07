"""
Property-based tests for structured logging compliance
Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
"""
from hypothesis import given, strategies as st, settings
import json
import logging
import io
from typing import Dict, Any

from app.core.logging import (
    StructuredFormatter,
    CorrelationIdFilter,
    setup_logging,
    set_correlation_id,
    get_correlation_id,
    generate_correlation_id,
    LoggerMixin
)


class TestStructuredLoggingCompliance:
    """Test that structured logging consistently includes correlation ID and follows JSON format"""

    @given(
        correlation_id=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
        log_message=st.text(min_size=1, max_size=500),
        log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        extra_fields=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(
                lambda x: x.isidentifier() and x not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
                    'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                    'thread', 'threadName', 'processName', 'process', 'getMessage',
                    'exc_info', 'exc_text', 'stack_info', 'message', 'correlation_id'
                }
            ),
            values=st.one_of(
                st.text(max_size=100),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans()
            ),
            max_size=5
        )
    )
    @settings(max_examples=100)
    def test_structured_logging_format_consistency(
        self,
        correlation_id: str,
        log_message: str,
        log_level: str,
        extra_fields: Dict[str, Any]
    ):
        """
        Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
        For any system operation that generates logs, the log entry should contain a correlation ID
        and follow JSON format with required fields
        **Validates: Requirements 1.4, 9.2**
        """
        # Setup structured formatter
        formatter = StructuredFormatter()

        # Set correlation ID in context
        set_correlation_id(correlation_id.strip())

        # Create log record
        logging.getLogger("test_logger")
        record = logging.LogRecord(
            name="test_logger",
            level=getattr(logging, log_level),
            pathname="test.py",
            lineno=42,
            msg=log_message,
            args=(),
            exc_info=None
        )

        # Add extra fields to record
        for key, value in extra_fields.items():
            setattr(record, key, value)

        # Format the log record
        formatted_log = formatter.format(record)

        # Parse as JSON to verify structure
        log_data = json.loads(formatted_log)

        # Verify required fields are present
        assert "timestamp" in log_data
        assert "level" in log_data
        assert "logger" in log_data
        assert "message" in log_data
        assert "module" in log_data
        assert "function" in log_data
        assert "line" in log_data

        # Verify correlation ID is included
        assert "correlation_id" in log_data
        assert log_data["correlation_id"] == correlation_id.strip()

        # Verify log content
        assert log_data["level"] == log_level
        assert log_data["message"] == log_message
        assert log_data["logger"] == "test_logger"

        # Verify extra fields are in the extra section
        if extra_fields:
            assert "extra" in log_data
            for key, value in extra_fields.items():
                assert log_data["extra"][key] == value

    @given(
        operation_name=st.text(min_size=1, max_size=50),
        operation_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            max_size=3
        )
    )
    @settings(max_examples=100)
    def test_correlation_id_propagation_consistency(
        self,
        operation_name: str,
        operation_data: Dict[str, Any]
    ):
        """
        Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
        For any system operation, correlation ID should be consistently propagated through all log entries
        **Validates: Requirements 1.4, 9.2**
        """
        # Generate correlation ID
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        # Verify correlation ID is retrievable
        assert get_correlation_id() == correlation_id

        # Create multiple log entries with different loggers
        loggers = [
            logging.getLogger("app.service"),
            logging.getLogger("app.data"),
            logging.getLogger("app.analysis")
        ]

        formatter = StructuredFormatter()

        for i, logger in enumerate(loggers):
            # Create log record
            record = logging.LogRecord(
                name=logger.name,
                level=logging.INFO,
                pathname="test.py",
                lineno=i + 1,
                msg=f"{operation_name} step {i + 1}",
                args=(),
                exc_info=None
            )

            # Add operation data
            for key, value in operation_data.items():
                setattr(record, f"operation_{key}", value)

            # Format and verify correlation ID
            formatted_log = formatter.format(record)
            log_data = json.loads(formatted_log)

            # All log entries should have the same correlation ID
            assert log_data["correlation_id"] == correlation_id

    @given(
        log_messages=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100)
    def test_logger_mixin_consistency(self, log_messages: list):
        """
        Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
        For any class using LoggerMixin, logging methods should consistently include correlation ID
        **Validates: Requirements 1.4, 9.2**
        """
        # Create test class with LoggerMixin
        class TestService(LoggerMixin):
            def perform_operation(self, messages: list):
                for i, message in enumerate(messages):
                    self.log_info(f"Processing: {message}", step=i, total=len(messages))

        # Set correlation ID
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        # Capture log output
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(StructuredFormatter())

        service = TestService()
        service.logger.addHandler(handler)
        service.logger.setLevel(logging.INFO)

        # Perform operation
        service.perform_operation(log_messages)

        # Verify all log entries have correlation ID
        log_output = log_stream.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]

        assert len(log_lines) == len(log_messages)

        for line in log_lines:
            log_data = json.loads(line)
            assert log_data["correlation_id"] == correlation_id
            assert "step" in log_data["extra"]
            assert "total" in log_data["extra"]

    @given(
        exception_message=st.text(
            min_size=1,
            max_size=200),
        context_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=15).filter(
                    lambda x: x.isidentifier() and x not in {
                        'name',
                        'msg',
                        'args',
                        'levelname',
                        'levelno',
                        'pathname',
                        'filename',
                        'module',
                        'lineno',
                        'funcName',
                        'created',
                        'msecs',
                        'relativeCreated',
                        'thread',
                        'threadName',
                        'processName',
                        'process',
                        'getMessage',
                        'exc_info',
                        'exc_text',
                        'stack_info',
                        'message',
                        'correlation_id'}),
            values=st.text(
                max_size=50),
            max_size=3))
    @settings(max_examples=100)
    def test_exception_logging_consistency(
        self,
        exception_message: str,
        context_data: Dict[str, str]
    ):
        """
        Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
        For any exception logging, correlation ID and exception details should be consistently included
        **Validates: Requirements 1.4, 9.2**
        """
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        formatter = StructuredFormatter()
        logging.getLogger("test_exception_logger")

        # Create exception
        try:
            raise ValueError(exception_message)
        except ValueError as e:
            # Create log record with exception info
            record = logging.LogRecord(
                name="test_exception_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=100,
                msg="An error occurred during operation",
                args=(),
                exc_info=(type(e), e, e.__traceback__)
            )

            # Add context data
            for key, value in context_data.items():
                setattr(record, key, value)

            # Format log
            formatted_log = formatter.format(record)
            log_data = json.loads(formatted_log)

            # Verify exception logging structure
            assert log_data["correlation_id"] == correlation_id
            assert log_data["level"] == "ERROR"
            assert "exception" in log_data
            assert exception_message in log_data["exception"]

            # Verify context data is preserved
            if context_data:
                assert "extra" in log_data
                for key, value in context_data.items():
                    assert log_data["extra"][key] == value

    def test_correlation_id_filter_consistency(self):
        """
        Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
        CorrelationIdFilter should consistently add correlation ID to log records
        **Validates: Requirements 1.4, 9.2**
        """
        correlation_filter = CorrelationIdFilter()

        # Test with correlation ID set
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None
        )

        # Filter should add correlation ID
        result = correlation_filter.filter(record)
        assert result is True
        assert hasattr(record, 'correlation_id')
        assert record.correlation_id == correlation_id

        # Test without correlation ID
        set_correlation_id(None)

        record2 = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=2,
            msg="test message 2",
            args=(),
            exc_info=None
        )

        # Filter should still return True but no correlation_id attribute
        result = correlation_filter.filter(record2)
        assert result is True
        assert not hasattr(record2, 'correlation_id')

    @given(
        log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR"]),
        structured=st.booleans()
    )
    @settings(max_examples=50)
    def test_setup_logging_consistency(self, log_level: str, structured: bool):
        """
        Feature: tech-stack-modernization, Property 2: Structured Logging Compliance
        setup_logging should consistently configure logging with proper formatters
        **Validates: Requirements 1.4, 9.2**
        """
        # Setup logging with given parameters
        setup_logging(level=log_level, structured=structured)

        # Verify root logger configuration
        root_logger = logging.getLogger()
        assert root_logger.level == getattr(logging, log_level)

        # Verify handlers are configured
        assert len(root_logger.handlers) > 0

        # Check formatter type
        handler = root_logger.handlers[0]
        if structured:
            assert isinstance(handler.formatter, StructuredFormatter)
        else:
            assert not isinstance(handler.formatter, StructuredFormatter)

        # Verify correlation ID filter is added
        filters = [f for f in handler.filters if isinstance(f, CorrelationIdFilter)]
        assert len(filters) > 0
