"""
Property-based tests for error handling uniformity
Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
"""
import pytest
from hypothesis import given, strategies as st, settings
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError
from unittest.mock import Mock, MagicMock
import json
import asyncio
from typing import Dict, Any

from app.core.exceptions import (
    AppException,
    ValidationError,
    ExternalAPIError,
    DatabaseError,
    BusinessLogicError,
    ErrorCategory,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler
)


class TestErrorHandlingUniformity:
    """Test that error handling consistently transforms errors into uniform format with proper HTTP status codes"""
    
    @given(
        error_message=st.text(min_size=1, max_size=200),
        status_code=st.integers(min_value=400, max_value=599),
        category=st.sampled_from(list(ErrorCategory)),
        details=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            max_size=3
        )
    )
    @settings(max_examples=100)
    def test_app_exception_handler_uniformity(
        self, 
        error_message: str, 
        status_code: int, 
        category: ErrorCategory,
        details: Dict[str, Any]
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any AppException, the handler should consistently return uniform error format with correlation ID
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        request.client.host = "127.0.0.1"
        
        # Create AppException
        exception = AppException(
            message=error_message,
            category=category,
            status_code=status_code,
            details=details
        )
        
        # Handle the exception synchronously using asyncio.run
        async def run_handler():
            return await app_exception_handler(request, exception)
        
        response = asyncio.run(run_handler())
        
        # Verify response structure
        assert isinstance(response, JSONResponse)
        assert response.status_code == status_code
        
        # Verify response content structure
        content = json.loads(response.body.decode())
        assert "error" in content
        
        error_data = content["error"]
        assert error_data["message"] == error_message
        assert error_data["category"] == category.value
        assert "correlation_id" in error_data
        assert error_data["details"] == details
        
        # Verify correlation ID header
        assert "x-correlation-id" in response.headers
        assert response.headers["x-correlation-id"] == error_data["correlation_id"]
    
    @given(
        field_name=st.text(min_size=1, max_size=50),
        field_value=st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans()
        ),
        validation_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_validation_error_uniformity(
        self, 
        field_name: str, 
        field_value, 
        validation_message: str
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any validation error, the handler should consistently format field-specific error information
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/validate"
        request.method = "POST"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create ValidationError
        validation_error = ValidationError(
            message=validation_message,
            field=field_name,
            value=field_value
        )
        
        # Handle the exception synchronously
        async def run_handler():
            return await app_exception_handler(request, validation_error)
        
        response = asyncio.run(run_handler())
        
        # Verify uniform error structure
        assert response.status_code == 400
        content = json.loads(response.body.decode())
        
        error_data = content["error"]
        assert error_data["message"] == validation_message
        assert error_data["category"] == "validation"
        assert error_data["details"]["field"] == field_name
        assert error_data["details"]["value"] == str(field_value)
        assert "correlation_id" in error_data
    
    @given(
        service_name=st.text(min_size=1, max_size=50),
        api_error_message=st.text(min_size=1, max_size=200),
        http_status=st.integers(min_value=500, max_value=599)
    )
    @settings(max_examples=100)
    def test_external_api_error_uniformity(
        self, 
        service_name: str, 
        api_error_message: str, 
        http_status: int
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any external API error, the handler should consistently include service information
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/external"
        request.method = "GET"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create ExternalAPIError
        api_error = ExternalAPIError(
            message=api_error_message,
            service=service_name,
            status_code=http_status
        )
        
        # Handle the exception synchronously
        async def run_handler():
            return await app_exception_handler(request, api_error)
        
        response = asyncio.run(run_handler())
        
        # Verify uniform error structure
        assert response.status_code == http_status
        content = json.loads(response.body.decode())
        
        error_data = content["error"]
        assert error_data["message"] == api_error_message
        assert error_data["category"] == "external_api"
        assert error_data["details"]["service"] == service_name
        assert "correlation_id" in error_data
    
    @given(
        database_operation=st.text(min_size=1, max_size=50),
        db_error_message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_database_error_uniformity(
        self, 
        database_operation: str, 
        db_error_message: str
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any database error, the handler should consistently include operation context
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/database"
        request.method = "POST"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create DatabaseError
        db_error = DatabaseError(
            message=db_error_message,
            operation=database_operation
        )
        
        # Handle the exception synchronously
        async def run_handler():
            return await app_exception_handler(request, db_error)
        
        response = asyncio.run(run_handler())
        
        # Verify uniform error structure
        assert response.status_code == 500
        content = json.loads(response.body.decode())
        
        error_data = content["error"]
        assert error_data["message"] == db_error_message
        assert error_data["category"] == "database"
        assert error_data["details"]["operation"] == database_operation
        assert "correlation_id" in error_data
    
    @given(
        business_error_message=st.text(min_size=1, max_size=200),
        business_context=st.dictionaries(
            keys=st.text(min_size=1, max_size=20).filter(lambda x: x.isidentifier()),
            values=st.text(max_size=50),
            max_size=3
        )
    )
    @settings(max_examples=100)
    def test_business_logic_error_uniformity(
        self, 
        business_error_message: str, 
        business_context: Dict[str, str]
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any business logic error, the handler should consistently include business context
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/business"
        request.method = "POST"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create BusinessLogicError
        business_error = BusinessLogicError(
            message=business_error_message,
            context=business_context
        )
        
        # Handle the exception synchronously
        async def run_handler():
            return await app_exception_handler(request, business_error)
        
        response = asyncio.run(run_handler())
        
        # Verify uniform error structure
        assert response.status_code == 422
        content = json.loads(response.body.decode())
        
        error_data = content["error"]
        assert error_data["message"] == business_error_message
        assert error_data["category"] == "business_logic"
        assert error_data["details"] == business_context
        assert "correlation_id" in error_data
    
    @given(
        http_status=st.integers(min_value=400, max_value=599),
        http_detail=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100)
    def test_http_exception_handler_uniformity(
        self, 
        http_status: int, 
        http_detail: str
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any HTTP exception, the handler should consistently transform to uniform format
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/http"
        request.method = "GET"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create HTTPException
        http_exception = StarletteHTTPException(
            status_code=http_status,
            detail=http_detail
        )
        
        # Handle the exception synchronously
        async def run_handler():
            return await http_exception_handler(request, http_exception)
        
        response = asyncio.run(run_handler())
        
        # Verify uniform error structure
        assert response.status_code == http_status
        content = json.loads(response.body.decode())
        
        error_data = content["error"]
        assert error_data["message"] == http_detail
        assert error_data["category"] == "http_error"
        assert error_data["details"] == {}
        assert "correlation_id" in error_data
    
    @given(
        exception_message=st.text(min_size=1, max_size=200),
        exception_type=st.sampled_from([ValueError, TypeError, KeyError, AttributeError])
    )
    @settings(max_examples=100)
    def test_generic_exception_handler_uniformity(
        self, 
        exception_message: str, 
        exception_type: type
    ):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any unhandled exception, the handler should consistently return safe error format
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/api/generic"
        request.method = "POST"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create generic exception
        generic_exception = exception_type(exception_message)
        
        # Handle the exception synchronously
        async def run_handler():
            return await generic_exception_handler(request, generic_exception)
        
        response = asyncio.run(run_handler())
        
        # Verify uniform error structure (should not expose internal details)
        assert response.status_code == 500
        content = json.loads(response.body.decode())
        
        error_data = content["error"]
        assert error_data["message"] == "Internal server error"  # Safe message
        assert error_data["category"] == "internal"
        assert error_data["details"] == {}  # No internal details exposed
        assert "correlation_id" in error_data
    
    @given(
        correlation_id=st.text(
            min_size=1, 
            max_size=100,
            alphabet=st.characters(min_codepoint=32, max_codepoint=126)  # ASCII printable characters only
        ).filter(lambda x: x.strip())
    )
    @settings(max_examples=100)
    def test_correlation_id_preservation_uniformity(self, correlation_id: str):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For any error with existing correlation ID, the handler should preserve it consistently
        **Validates: Requirements 1.5, 3.6**
        """
        # Create mock request with existing correlation ID
        request = Mock(spec=Request)
        request.url.path = "/api/correlation"
        request.method = "GET"
        # Mock headers.get to return the provided correlation ID
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return correlation_id.strip()
            return None
        request.headers.get.side_effect = mock_headers_get
        
        # Create exception
        exception = AppException(
            message="Test error with correlation ID",
            category=ErrorCategory.INTERNAL,
            correlation_id=correlation_id.strip()
        )
        
        # Handle the exception synchronously
        async def run_handler():
            return await app_exception_handler(request, exception)
        
        response = asyncio.run(run_handler())
        
        # Verify correlation ID is preserved
        content = json.loads(response.body.decode())
        error_data = content["error"]
        
        assert error_data["correlation_id"] == correlation_id.strip()
        assert response.headers["x-correlation-id"] == correlation_id.strip()
    
    def test_error_category_consistency(self):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        All error categories should be consistently defined and usable
        **Validates: Requirements 1.5, 3.6**
        """
        # Test all error categories are valid
        categories = list(ErrorCategory)
        assert len(categories) > 0
        
        # Each category should have a string value
        for category in categories:
            assert isinstance(category.value, str)
            assert len(category.value) > 0
        
        # Test creating exceptions with each category
        for category in categories:
            exception = AppException(
                message=f"Test error for {category.value}",
                category=category,
                status_code=400
            )
            assert exception.category == category
            assert exception.category.value == category.value
    
    @given(
        error_messages=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=50)
    def test_multiple_error_handling_consistency(self, error_messages: list):
        """
        Feature: tech-stack-modernization, Property 3: Error Handling Uniformity
        For multiple errors in sequence, each should be handled with consistent format
        **Validates: Requirements 1.5, 3.6**
        """
        request = Mock(spec=Request)
        request.url.path = "/api/multiple"
        request.method = "POST"
        # Mock headers.get to properly handle default parameter
        def mock_headers_get(key, default=None):
            if key == "x-correlation-id":
                return default  # Return the default value when no correlation ID exists
            return None
        request.headers.get.side_effect = mock_headers_get
        
        responses = []
        
        # Handle multiple different error types
        for i, message in enumerate(error_messages):
            if i % 4 == 0:
                error = ValidationError(message, "field", "value")
            elif i % 4 == 1:
                error = ExternalAPIError(message, "test_service")
            elif i % 4 == 2:
                error = DatabaseError(message, "test_operation")
            else:
                error = BusinessLogicError(message)
            
            async def run_handler():
                return await app_exception_handler(request, error)
            
            response = asyncio.run(run_handler())
            responses.append(response)
        
        # Verify all responses have consistent structure
        for response in responses:
            assert isinstance(response, JSONResponse)
            content = json.loads(response.body.decode())
            
            # All should have the same error structure
            assert "error" in content
            error_data = content["error"]
            assert "message" in error_data
            assert "category" in error_data
            assert "correlation_id" in error_data
            assert "details" in error_data
            
            # All should have correlation ID header
            assert "x-correlation-id" in response.headers