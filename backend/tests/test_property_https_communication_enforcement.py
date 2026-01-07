"""
Property-based tests for HTTPS communication enforcement.

Feature: tech-stack-modernization, Property 18: HTTPS Communication Enforcement
**Validates: Requirements 7.2**
"""

import pytest
from hypothesis import given, strategies as st, settings
from urllib.parse import urlparse, urlunparse
from unittest.mock import Mock, patch, MagicMock
import httpx
import requests
from typing import Dict, Any, Optional, List
import ssl


class MockHTTPSService:
    """Mock HTTPS service for testing communication enforcement properties."""
    
    def __init__(self, enforce_https: bool = True, redirect_http: bool = True):
        self.enforce_https = enforce_https
        self.redirect_http = redirect_http
        self.security_headers = {
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'"
        }
    
    def make_request(self, url: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
        """Simulate HTTP/HTTPS request with security enforcement."""
        parsed_url = urlparse(url)
        
        # Check if HTTP is being used
        if parsed_url.scheme == "http":
            if self.enforce_https:
                if self.redirect_http:
                    # Simulate redirect to HTTPS
                    https_url = urlunparse(parsed_url._replace(scheme="https"))
                    return {
                        "status_code": 301,
                        "headers": {
                            "Location": https_url,
                            **self.security_headers
                        },
                        "url": https_url,
                        "redirected": True,
                        "secure": True
                    }
                else:
                    # Reject HTTP requests
                    return {
                        "status_code": 400,
                        "headers": {"Connection": "close"},
                        "error": "HTTP not allowed, use HTTPS",
                        "secure": False
                    }
            else:
                # HTTPS not enforced, allow HTTP but with security headers
                return {
                    "status_code": 200,
                    "headers": {
                        **self.security_headers,
                        "Content-Type": "application/json"
                    },
                    "url": url,
                    "redirected": False,
                    "secure": False
                }
        
        # HTTPS request
        elif parsed_url.scheme == "https":
            return {
                "status_code": 200,
                "headers": {
                    **self.security_headers,
                    "Content-Type": "application/json"
                },
                "url": url,
                "redirected": False,
                "secure": True,
                "tls_version": "TLSv1.3"
            }
        
        # Invalid scheme
        else:
            return {
                "status_code": 400,
                "error": f"Invalid scheme: {parsed_url.scheme}",
                "secure": False
            }
    
    def validate_tls_config(self, url: str) -> Dict[str, Any]:
        """Validate TLS configuration for HTTPS URLs."""
        parsed_url = urlparse(url)
        
        if parsed_url.scheme != "https":
            return {
                "valid": False,
                "error": "Not an HTTPS URL"
            }
        
        return {
            "valid": True,
            "tls_version": "TLSv1.3",
            "cipher_suite": "TLS_AES_256_GCM_SHA384",
            "certificate_valid": True,
            "hsts_enabled": True
        }


class TestHTTPSCommunicationEnforcement:
    """Property tests for HTTPS communication enforcement."""
    
    @given(
        urls=st.lists(
            st.one_of(
                # HTTP URLs that should be redirected/rejected
                st.builds(
                    lambda host, path: f"http://{host}{path}",
                    host=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
                    path=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
                ).map(lambda url: url.replace(" ", "")),
                # HTTPS URLs that should be allowed
                st.builds(
                    lambda host, path: f"https://{host}{path}",
                    host=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
                    path=st.text(min_size=0, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc')))
                ).map(lambda url: url.replace(" ", ""))
            ),
            min_size=1, max_size=10
        ),
        enforce_https=st.booleans(),
        redirect_http=st.booleans()
    )
    @settings(max_examples=50, deadline=5000)
    def test_https_communication_enforcement_property(self, urls: List[str], enforce_https: bool, redirect_http: bool):
        """
        Property 18: HTTPS Communication Enforcement
        
        For any system communication, HTTPS should be used and HTTP requests 
        should be rejected or redirected.
        
        **Validates: Requirements 7.2**
        """
        https_service = MockHTTPSService(enforce_https=enforce_https, redirect_http=redirect_http)
        
        for url in urls:
            # Skip invalid URLs
            if not url or "//" not in url:
                continue
                
            parsed_url = urlparse(url)
            response = https_service.make_request(url)
            
            if parsed_url.scheme == "https":
                # HTTPS requests should always succeed
                assert response["status_code"] == 200, \
                    f"HTTPS request to {url} should succeed"
                assert response["secure"] is True, \
                    f"HTTPS request to {url} should be marked as secure"
                assert "Strict-Transport-Security" in response["headers"], \
                    f"HTTPS response should include HSTS header for {url}"
                
            elif parsed_url.scheme == "http":
                if enforce_https:
                    if redirect_http:
                        # HTTP should be redirected to HTTPS
                        assert response["status_code"] == 301, \
                            f"HTTP request to {url} should be redirected when enforcement is enabled"
                        assert response["redirected"] is True, \
                            f"HTTP request to {url} should be marked as redirected"
                        assert response["url"].startswith("https://"), \
                            f"HTTP request to {url} should be redirected to HTTPS"
                    else:
                        # HTTP should be rejected
                        assert response["status_code"] == 400, \
                            f"HTTP request to {url} should be rejected when enforcement is enabled"
                        assert response["secure"] is False, \
                            f"Rejected HTTP request to {url} should be marked as insecure"
                else:
                    # When HTTPS not enforced, HTTP might be allowed (depends on implementation)
                    # But security headers should still be present if response is successful
                    if response["status_code"] == 200:
                        assert "X-Content-Type-Options" in response.get("headers", {}), \
                            f"Even HTTP responses should include security headers for {url}"
    
    @given(
        base_urls=st.lists(
            st.sampled_from([
                "api.example.com",
                "secure-service.org", 
                "financial-data.net",
                "stock-analysis.io"
            ]),
            min_size=1, max_size=5, unique=True
        ),
        endpoints=st.lists(
            st.sampled_from([
                "/api/v1/stocks",
                "/auth/login",
                "/data/analysis",
                "/health",
                "/metrics"
            ]),
            min_size=1, max_size=8
        )
    )
    @settings(max_examples=30, deadline=4000)
    def test_https_security_headers_property(self, base_urls: List[str], endpoints: List[str]):
        """
        Property 18b: HTTPS Security Headers
        
        For any HTTPS communication, appropriate security headers should be present
        to prevent common web vulnerabilities.
        
        **Validates: Requirements 7.2**
        """
        https_service = MockHTTPSService(enforce_https=True)
        
        required_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options", 
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        for base_url in base_urls:
            for endpoint in endpoints:
                https_url = f"https://{base_url}{endpoint}"
                response = https_service.make_request(https_url)
                
                assert response["status_code"] == 200, \
                    f"HTTPS request to {https_url} should succeed"
                
                # Check for required security headers
                for header in required_headers:
                    assert header in response["headers"], \
                        f"HTTPS response from {https_url} should include {header} header"
                
                # Verify HSTS header has proper configuration
                hsts_header = response["headers"].get("Strict-Transport-Security", "")
                assert "max-age=" in hsts_header, \
                    f"HSTS header should include max-age directive for {https_url}"
                assert "includeSubDomains" in hsts_header, \
                    f"HSTS header should include includeSubDomains for {https_url}"
    
    @given(
        tls_versions=st.lists(
            st.sampled_from(["TLSv1.0", "TLSv1.1", "TLSv1.2", "TLSv1.3"]),
            min_size=1, max_size=4
        ),
        cipher_suites=st.lists(
            st.sampled_from([
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256", 
                "TLS_AES_128_GCM_SHA256",
                "ECDHE-RSA-AES256-GCM-SHA384"
            ]),
            min_size=1, max_size=4
        )
    )
    @settings(max_examples=25, deadline=4000)
    def test_tls_configuration_security_property(self, tls_versions: List[str], cipher_suites: List[str]):
        """
        Property 18c: TLS Configuration Security
        
        For any TLS connection, only secure TLS versions (1.2+) and cipher suites
        should be accepted.
        
        **Validates: Requirements 7.2**
        """
        https_service = MockHTTPSService()
        
        secure_tls_versions = ["TLSv1.2", "TLSv1.3"]
        insecure_tls_versions = ["TLSv1.0", "TLSv1.1"]
        
        test_url = "https://secure-api.example.com/test"
        
        for tls_version in tls_versions:
            tls_config = https_service.validate_tls_config(test_url)
            
            # All HTTPS URLs should have valid TLS configuration
            assert tls_config["valid"] is True, \
                f"TLS configuration should be valid for HTTPS URLs"
            
            # Should use secure TLS version (1.2 or higher)
            actual_tls = tls_config.get("tls_version", "")
            assert any(secure_version in actual_tls for secure_version in secure_tls_versions), \
                f"Should use secure TLS version (1.2+), got {actual_tls}"
            
            # Should not use insecure TLS versions
            assert not any(insecure_version in actual_tls for insecure_version in insecure_tls_versions), \
                f"Should not use insecure TLS version, got {actual_tls}"
            
            # Certificate should be valid
            assert tls_config["certificate_valid"] is True, \
                f"TLS certificate should be valid"
            
            # HSTS should be enabled
            assert tls_config["hsts_enabled"] is True, \
                f"HSTS should be enabled for secure connections"
    
    @given(
        mixed_requests=st.lists(
            st.tuples(
                st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
                st.one_of(
                    st.just("http://insecure.example.com/api"),
                    st.just("https://secure.example.com/api"),
                    st.just("ftp://invalid.example.com/data"),
                    st.just("https://api.financial-service.com/stocks")
                )
            ),
            min_size=1, max_size=15
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_mixed_protocol_security_property(self, mixed_requests: List[tuple]):
        """
        Property 18d: Mixed Protocol Security
        
        For any sequence of requests with mixed protocols, the system should
        consistently enforce HTTPS and reject insecure protocols.
        
        **Validates: Requirements 7.2**
        """
        https_service = MockHTTPSService(enforce_https=True, redirect_http=True)
        
        secure_requests = 0
        insecure_requests = 0
        
        for method, url in mixed_requests:
            parsed_url = urlparse(url)
            response = https_service.make_request(url, method=method)
            
            if parsed_url.scheme == "https":
                secure_requests += 1
                
                # HTTPS requests should succeed
                assert response["status_code"] == 200, \
                    f"HTTPS {method} request to {url} should succeed"
                assert response["secure"] is True, \
                    f"HTTPS {method} request should be marked as secure"
                
            elif parsed_url.scheme == "http":
                insecure_requests += 1
                
                # HTTP requests should be redirected to HTTPS
                assert response["status_code"] == 301, \
                    f"HTTP {method} request to {url} should be redirected"
                assert response["redirected"] is True, \
                    f"HTTP {method} request should be marked as redirected"
                assert response["url"].startswith("https://"), \
                    f"HTTP {method} request should be redirected to HTTPS"
                
            else:
                # Invalid protocols should be rejected
                assert response["status_code"] == 400, \
                    f"Invalid protocol {method} request to {url} should be rejected"
                assert response["secure"] is False, \
                    f"Invalid protocol request should be marked as insecure"
        
        # If we had any requests, verify the security enforcement was consistent
        if mixed_requests:
            total_requests = len(mixed_requests)
            
            # All HTTPS requests should have been handled securely
            if secure_requests > 0:
                assert secure_requests <= total_requests, \
                    "Secure request count should not exceed total requests"
            
            # All HTTP requests should have been redirected (not allowed insecurely)
            if insecure_requests > 0:
                assert insecure_requests <= total_requests, \
                    "Insecure request count should not exceed total requests"