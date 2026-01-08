"""
Unit tests for CDN static asset delivery
"""
from app.core.cdn import (
    CDNService,
    AssetType,
    create_cdn_service,
    get_cdn_service,
    reset_cdn_service
)
import pytest
import os
import sys
from unittest.mock import patch
from urllib.parse import urlparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCDNStaticAssets:
    """Test CDN static asset delivery functionality"""

    def setup_method(self):
        """Setup for each test method"""
        # Reset global CDN service before each test
        reset_cdn_service()

    def test_production_environment_uses_cdn_urls(self):
        """
        Test that static assets are served from CDN URLs in production
        Requirements: 5.5
        """
        cdn_base_url = "https://cdn.example.com"

        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'CDN_BASE_URL': cdn_base_url
        }, clear=False):
            cdn_service = create_cdn_service()

            # Should enable CDN in production with proper URL
            assert cdn_service.enable_cdn is True
            assert cdn_service.cdn_base_url == cdn_base_url

            # Test various asset types
            test_assets = [
                "css/styles.css",
                "js/app.js",
                "images/logo.png",
                "fonts/roboto.woff2"
            ]

            for asset_path in test_assets:
                asset_url = cdn_service.get_asset_url(asset_path)

                # Should use CDN URL
                assert asset_url.startswith(cdn_base_url), \
                    f"Asset {asset_path} should use CDN URL, got {asset_url}"

                # Should be properly formatted
                assert asset_path in asset_url, \
                    f"Asset path should be in URL: {asset_url}"

                # Should be valid URL
                parsed = urlparse(asset_url)
                assert parsed.scheme in ['http', 'https'], \
                    f"Asset URL should have valid scheme: {asset_url}"
                assert parsed.netloc, \
                    f"Asset URL should have valid domain: {asset_url}"

    def test_development_environment_uses_local_urls(self):
        """
        Test that static assets use local URLs in development
        Requirements: 5.5
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development'
        }, clear=False):
            cdn_service = create_cdn_service()

            # Should disable CDN in development
            assert cdn_service.enable_cdn is False

            # Test asset URL generation
            asset_path = "css/styles.css"
            asset_url = cdn_service.get_asset_url(asset_path)

            # Should use fallback URL (local)
            assert asset_url.startswith("/static/") or asset_url.startswith(
                "static/"), f"Development should use local URL, got {asset_url}"

            # Should not be CDN URL
            assert not cdn_service.is_cdn_url(asset_url), \
                f"Development URL should not be CDN URL: {asset_url}"

    def test_cdn_fallback_when_no_cdn_configured(self):
        """
        Test fallback to local URLs when CDN is not configured
        Requirements: 5.5
        """
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production'
            # No CDN_BASE_URL configured
        }, clear=False):
            cdn_service = create_cdn_service()

            # Should disable CDN when not configured
            assert cdn_service.enable_cdn is False

            # Should use fallback URLs
            asset_path = "js/app.js"
            asset_url = cdn_service.get_asset_url(asset_path)

            assert asset_url.startswith("/static/") or asset_url.startswith("static/"), \
                f"Should use fallback URL when CDN not configured, got {asset_url}"

    def test_asset_type_detection(self):
        """
        Test correct detection of asset types based on file extensions
        Requirements: 5.5
        """
        cdn_service = CDNService()

        # Test various asset types
        test_cases = [
            ("styles.css", AssetType.CSS),
            ("app.js", AssetType.JS),
            ("module.mjs", AssetType.JS),
            ("logo.png", AssetType.IMAGE),
            ("photo.jpg", AssetType.IMAGE),
            ("icon.svg", AssetType.IMAGE),
            ("font.woff2", AssetType.FONT),
            ("video.mp4", AssetType.VIDEO),
            ("audio.mp3", AssetType.AUDIO),
            ("document.pdf", AssetType.DOCUMENT),
            ("unknown.xyz", AssetType.OTHER)
        ]

        for asset_path, expected_type in test_cases:
            detected_type = cdn_service.get_asset_type(asset_path)
            assert detected_type == expected_type, \
                f"Asset {asset_path} should be detected as {expected_type}, got {detected_type}"

    def test_cache_headers_configuration(self):
        """
        Test that appropriate cache headers are configured for different asset types
        Requirements: 5.5
        """
        cdn_service = CDNService(
            cdn_base_url="https://cdn.example.com",
            enable_cdn=True)

        # Test cache headers for different asset types
        test_cases = [
            ("styles.css", "public, max-age=31536000"),  # 1 year for CSS
            ("app.js", "public, max-age=31536000"),      # 1 year for JS
            ("logo.png", "public, max-age=2592000"),     # 30 days for images
            ("font.woff2", "public, max-age=31536000"),  # 1 year for fonts
            ("video.mp4", "public, max-age=604800"),     # 1 week for video
            ("unknown.xyz", "public, max-age=3600")      # 1 hour for other
        ]

        for asset_path, expected_cache_control in test_cases:
            headers = cdn_service.get_cache_headers(asset_path)

            # Should have cache control header
            assert "Cache-Control" in headers, \
                f"Asset {asset_path} should have Cache-Control header"

            assert headers["Cache-Control"] == expected_cache_control, \
                f"Asset {asset_path} should have cache control {expected_cache_control}, got {headers['Cache-Control']}"

            # Should have asset type header
            assert "X-Asset-Type" in headers, \
                f"Asset {asset_path} should have X-Asset-Type header"

            # Should have CDN status header
            assert "X-CDN-Enabled" in headers, \
                f"Asset {asset_path} should have X-CDN-Enabled header"

            assert headers["X-CDN-Enabled"] == "true", \
                f"CDN should be enabled in headers for {asset_path}"

    def test_batch_asset_url_generation(self):
        """
        Test batch generation of asset URLs for performance
        Requirements: 5.5
        """
        cdn_service = CDNService(
            cdn_base_url="https://cdn.example.com",
            enable_cdn=True
        )

        asset_paths = [
            "css/main.css",
            "css/theme.css",
            "js/app.js",
            "js/vendor.js",
            "images/logo.png",
            "fonts/roboto.woff2"
        ]

        # Generate URLs in batch
        asset_urls = cdn_service.batch_get_asset_urls(asset_paths)

        # Should return URL for each asset
        assert len(asset_urls) == len(asset_paths), \
            "Should return URL for each asset"

        for asset_path in asset_paths:
            assert asset_path in asset_urls, \
                f"Should include URL for {asset_path}"

            url = asset_urls[asset_path]
            assert url.startswith("https://cdn.example.com"), \
                f"Asset {asset_path} should use CDN URL, got {url}"

            assert asset_path in url, \
                f"Asset path should be in URL: {url}"

    def test_asset_info_comprehensive(self):
        """
        Test comprehensive asset information retrieval
        Requirements: 5.5
        """
        cdn_service = CDNService(
            cdn_base_url="https://cdn.example.com",
            enable_cdn=True
        )

        asset_path = "css/styles.css"
        asset_info = cdn_service.get_asset_info(asset_path)

        # Should include all expected fields
        expected_fields = [
            "asset_path", "asset_type", "cdn_url", "fallback_url",
            "is_cdn_enabled", "is_served_from_cdn", "cache_headers"
        ]

        for field in expected_fields:
            assert field in asset_info, \
                f"Asset info should include {field}"

        # Verify field values
        assert asset_info["asset_path"] == asset_path
        assert asset_info["asset_type"] == "css"
        assert asset_info["is_cdn_enabled"] is True
        assert asset_info["is_served_from_cdn"] is True
        assert asset_info["cdn_url"].startswith("https://cdn.example.com")
        assert asset_info["fallback_url"].startswith("/static/")
        assert isinstance(asset_info["cache_headers"], dict)

    def test_cdn_configuration_validation(self):
        """
        Test CDN configuration validation
        Requirements: 5.5
        """
        # Test valid configuration
        valid_cdn = CDNService(
            cdn_base_url="https://cdn.example.com",
            enable_cdn=True
        )

        validation = valid_cdn.validate_cdn_configuration()
        assert validation["valid"] is True, \
            "Valid CDN configuration should pass validation"
        assert len(validation["issues"]) == 0, \
            "Valid configuration should have no issues"

        # Test configuration with empty URL - should auto-disable CDN
        empty_url_cdn = CDNService(
            cdn_base_url="",
            enable_cdn=True
        )

        # CDN should be auto-disabled when URL is empty
        assert empty_url_cdn.enable_cdn is False, \
            "CDN should be auto-disabled when URL is empty"

        validation = empty_url_cdn.validate_cdn_configuration()
        assert validation["valid"] is True, \
            "Configuration with disabled CDN should be valid"

        # Test invalid URL format - manually enable CDN with bad URL
        invalid_url_cdn = CDNService(
            cdn_base_url="not-a-valid-url",
            enable_cdn=True
        )

        validation = invalid_url_cdn.validate_cdn_configuration()
        assert validation["valid"] is False, \
            "Invalid URL format should fail validation"

        # Test missing fallback URL
        with patch.dict(os.environ, {'STATIC_BASE_URL': ''}, clear=False):
            no_fallback_cdn = CDNService(
                cdn_base_url="https://cdn.example.com",
                fallback_base_url=None,
                enable_cdn=True
            )

            validation = no_fallback_cdn.validate_cdn_configuration()
            assert validation["valid"] is False, \
                "Missing fallback URL should fail validation"

    def test_global_cdn_service_singleton(self):
        """
        Test that global CDN service maintains singleton pattern
        Requirements: 5.5
        """
        # Clear any existing service
        reset_cdn_service()

        with patch('app.core.cdn.create_cdn_service') as mock_create:
            mock_cdn = CDNService()
            mock_create.return_value = mock_cdn

            # First call should create service
            cdn1 = get_cdn_service()
            assert cdn1 == mock_cdn
            mock_create.assert_called_once()

            # Second call should return same instance
            cdn2 = get_cdn_service()
            assert cdn2 == mock_cdn
            assert cdn1 is cdn2

            # create_cdn_service should only be called once
            assert mock_create.call_count == 1

    def test_url_path_normalization(self):
        """
        Test that asset paths are properly normalized in URLs
        Requirements: 5.5
        """
        cdn_service = CDNService(
            cdn_base_url="https://cdn.example.com/",
            enable_cdn=True
        )

        # Test various path formats
        test_cases = [
            "css/styles.css",      # Normal path
            "/css/styles.css",     # Leading slash
            "//css/styles.css",    # Double leading slash
            "css//styles.css",     # Double slash in middle
        ]

        expected_url = "https://cdn.example.com/css/styles.css"

        for asset_path in test_cases:
            asset_url = cdn_service.get_asset_url(asset_path)

            # Should normalize to same URL
            assert asset_url == expected_url, \
                f"Path {asset_path} should normalize to {expected_url}, got {asset_url}"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
