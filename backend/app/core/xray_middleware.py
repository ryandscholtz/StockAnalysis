"""
AWS X-Ray middleware for FastAPI application
Provides distributed tracing capabilities
"""
import os
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core.context import Context
from aws_xray_sdk.core.models import http
from aws_xray_sdk.core.utils import stacktrace
import json

logger = logging.getLogger(__name__)


class XRayMiddleware(BaseHTTPMiddleware):
    """
    X-Ray middleware for FastAPI that creates trace segments for each request
    """

    def __init__(self, app, service_name: str = "stock-analysis-api"):
        super().__init__(app)
        self.service_name = service_name
        self._setup_xray()

    def _setup_xray(self):
        """Configure X-Ray SDK"""
        try:
            # Configure X-Ray recorder
            xray_recorder.configure(
                service=self.service_name,
                dynamic_naming=f"*{self.service_name}*",
                context=Context(),
                plugins=('EC2Plugin', 'ECSPlugin'),
                daemon_address=os.getenv('AWS_XRAY_DAEMON_ADDRESS', '127.0.0.1:2000'),
                use_ssl=False
            )

            # Patch AWS SDK and other libraries for automatic tracing
            libraries_to_patch = ['boto3', 'botocore', 'requests', 'httpx', 'sqlite3']
            patch_all(libraries_to_patch)

            logger.info("X-Ray SDK configured successfully", extra={
                "service_name": self.service_name,
                "daemon_address": os.getenv('AWS_XRAY_DAEMON_ADDRESS', '127.0.0.1:2000')
            })

        except Exception as e:
            logger.warning("Failed to configure X-Ray SDK", extra={"error": str(e)})

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with X-Ray tracing"""

        # Skip tracing for health checks and static files
        if self._should_skip_tracing(request):
            return await call_next(request)

        # Create trace segment
        segment_name = f"{request.method} {request.url.path}"

        try:
            # Begin segment
            segment = xray_recorder.begin_segment(
                name=segment_name,
                traceid=self._extract_trace_id(request),
                parent_id=self._extract_parent_id(request)
            )

            # Add HTTP request metadata
            segment.put_http_meta(http.URL, str(request.url))
            segment.put_http_meta(http.METHOD, request.method)
            segment.put_http_meta(http.USER_AGENT, request.headers.get('user-agent', ''))

            # Add custom annotations for filtering
            segment.put_annotation('method', request.method)
            segment.put_annotation('path', request.url.path)
            segment.put_annotation('service', self.service_name)

            # Add correlation ID if present
            correlation_id = request.headers.get('x-correlation-id')
            if correlation_id:
                segment.put_annotation('correlation_id', correlation_id)

            # Add user information if available
            user_id = getattr(request.state, 'user_id', None)
            if user_id:
                segment.put_annotation('user_id', user_id)

            # Process request
            response = await call_next(request)

            # Add response metadata
            segment.put_http_meta(http.STATUS, response.status_code)

            # Add error information if response indicates error
            if response.status_code >= 400:
                segment.add_exception(
                    Exception(f"HTTP {response.status_code}"),
                    stack=stacktrace.get_stacktrace(limit=10)
                )
                segment.put_annotation('error', True)
                segment.put_annotation('error_code', response.status_code)
            else:
                segment.put_annotation('error', False)

            return response

        except Exception as e:
            # Add exception to segment
            if 'segment' in locals():
                segment.add_exception(e, stack=stacktrace.get_stacktrace(limit=10))
                segment.put_annotation('error', True)
                segment.put_annotation('exception_type', type(e).__name__)

            logger.error("Error in X-Ray middleware", extra={
                "error": str(e),
                "path": request.url.path,
                "method": request.method
            })
            raise

        finally:
            # End segment
            try:
                xray_recorder.end_segment()
            except Exception as e:
                logger.warning("Failed to end X-Ray segment", extra={"error": str(e)})

    def _should_skip_tracing(self, request: Request) -> bool:
        """Determine if request should be traced"""
        skip_paths = {'/health', '/metrics', '/favicon.ico', '/robots.txt'}
        return (
            request.url.path in skip_paths or
            request.url.path.startswith('/static/') or
            request.url.path.startswith('/docs') or
            request.url.path.startswith('/redoc')
        )

    def _extract_trace_id(self, request: Request) -> str:
        """Extract trace ID from request headers"""
        # X-Ray trace header format: Root=1-5e1b4151-5ac6c58f40c1e5b26216371d;Parent=70de5b6f19ff9a0a;Sampled=1
        trace_header = request.headers.get('X-Amzn-Trace-Id', '')
        if trace_header:
            parts = trace_header.split(';')
            for part in parts:
                if part.startswith('Root='):
                    return part.split('=')[1]
        return None

    def _extract_parent_id(self, request: Request) -> str:
        """Extract parent ID from request headers"""
        trace_header = request.headers.get('X-Amzn-Trace-Id', '')
        if trace_header:
            parts = trace_header.split(';')
            for part in parts:
                if part.startswith('Parent='):
                    return part.split('=')[1]
        return None


def create_database_subsegment(operation: str, table_name: str = None):
    """
    Create a subsegment for database operations

    Args:
        operation: Database operation (e.g., 'query', 'insert', 'update', 'delete')
        table_name: Name of the table being accessed
    """
    try:
        subsegment_name = f"database.{operation}"
        if table_name:
            subsegment_name += f".{table_name}"

        subsegment = xray_recorder.begin_subsegment(subsegment_name)
        subsegment.put_annotation('operation', operation)
        if table_name:
            subsegment.put_annotation('table', table_name)

        return subsegment
    except Exception as e:
        logger.warning("Failed to create database subsegment", extra={"error": str(e)})
        return None


def create_external_api_subsegment(service: str, operation: str):
    """
    Create a subsegment for external API calls

    Args:
        service: External service name (e.g., 'yahoo_finance', 'alpha_vantage')
        operation: API operation being performed
    """
    try:
        subsegment_name = f"external.{service}.{operation}"
        subsegment = xray_recorder.begin_subsegment(subsegment_name)
        subsegment.put_annotation('service', service)
        subsegment.put_annotation('operation', operation)
        subsegment.put_annotation('external', True)

        return subsegment
    except Exception as e:
        logger.warning("Failed to create external API subsegment", extra={"error": str(e)})
        return None


def end_subsegment(subsegment, error: Exception = None):
    """
    End a subsegment with optional error handling

    Args:
        subsegment: The subsegment to end
        error: Optional exception that occurred
    """
    if not subsegment:
        return

    try:
        if error:
            subsegment.add_exception(error, stack=stacktrace.get_stacktrace(limit=10))
            subsegment.put_annotation('error', True)
            subsegment.put_annotation('exception_type', type(error).__name__)
        else:
            subsegment.put_annotation('error', False)

        xray_recorder.end_subsegment()
    except Exception as e:
        logger.warning("Failed to end subsegment", extra={"error": str(e)})


# Decorator for tracing functions
def trace_function(name: str = None, annotations: dict = None):
    """
    Decorator to trace function execution

    Args:
        name: Custom name for the subsegment
        annotations: Additional annotations to add
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            subsegment_name = name or f"{func.__module__}.{func.__name__}"

            try:
                subsegment = xray_recorder.begin_subsegment(subsegment_name)
                subsegment.put_annotation('function', func.__name__)
                subsegment.put_annotation('module', func.__module__)

                if annotations:
                    for key, value in annotations.items():
                        subsegment.put_annotation(key, value)

                result = func(*args, **kwargs)
                subsegment.put_annotation('error', False)
                return result

            except Exception as e:
                if 'subsegment' in locals():
                    subsegment.add_exception(e, stack=stacktrace.get_stacktrace(limit=10))
                    subsegment.put_annotation('error', True)
                    subsegment.put_annotation('exception_type', type(e).__name__)
                raise
            finally:
                try:
                    xray_recorder.end_subsegment()
                except:
                    pass

        return wrapper
    return decorator


# Async version of the decorator
def trace_async_function(name: str = None, annotations: dict = None):
    """
    Decorator to trace async function execution

    Args:
        name: Custom name for the subsegment
        annotations: Additional annotations to add
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            subsegment_name = name or f"{func.__module__}.{func.__name__}"

            try:
                subsegment = xray_recorder.begin_subsegment(subsegment_name)
                subsegment.put_annotation('function', func.__name__)
                subsegment.put_annotation('module', func.__module__)
                subsegment.put_annotation('async', True)

                if annotations:
                    for key, value in annotations.items():
                        subsegment.put_annotation(key, value)

                result = await func(*args, **kwargs)
                subsegment.put_annotation('error', False)
                return result

            except Exception as e:
                if 'subsegment' in locals():
                    subsegment.add_exception(e, stack=stacktrace.get_stacktrace(limit=10))
                    subsegment.put_annotation('error', True)
                    subsegment.put_annotation('exception_type', type(e).__name__)
                raise
            finally:
                try:
                    xray_recorder.end_subsegment()
                except:
                    pass

        return wrapper
    return decorator
