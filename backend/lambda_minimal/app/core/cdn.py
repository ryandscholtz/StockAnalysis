"""
CDN service for static asset delivery
"""
import os
import logging
from typing import Optional, Dict, List
from urllib.parse import urljoin, urlparse
from enum import Enum

logger = logging.getLogger(__name__)


class AssetType(str, Enum):
    """Types of static assets"""
    CSS = "css"
    JS = "js"
    IMAGE = "image"
    FONT = "font"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"


class CDNService:
    """Service for managing CDN static asset delivery"""

    def __init__(
        self,
        cdn_base_url: Optional[str] = None,
        fallback_base_url: Optional[str] = None,
        enable_cdn: bool = True
    ):
        self.cdn_base_url = cdn_base_url or os.getenv("CDN_BASE_URL", "")
        self.fallback_base_url = fallback_base_url or os.getenv("STATIC_BASE_URL", "/static")

        # Only enable CDN if we have a valid base URL
        self.enable_cdn = enable_cdn and bool(self.cdn_base_url.strip() if self.cdn_base_url else False)

        # Asset type mappings
        self.asset_extensions = {
            AssetType.CSS: [".css"],
            AssetType.JS: [".js", ".mjs"],
            AssetType.IMAGE: [".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico"],
            AssetType.FONT: [".woff", ".woff2", ".ttf", ".otf", ".eot"],
            AssetType.VIDEO: [".mp4", ".webm", ".ogg", ".avi", ".mov"],
            AssetType.AUDIO: [".mp3", ".wav", ".ogg", ".m4a"],
            AssetType.DOCUMENT: [".pdf", ".doc", ".docx", ".txt"],
        }

        # CDN configuration per asset type
        self.cdn_config = {
            AssetType.CSS: {"cache_control": "public, max-age=31536000"},  # 1 year
            AssetType.JS: {"cache_control": "public, max-age=31536000"},   # 1 year
            AssetType.IMAGE: {"cache_control": "public, max-age=2592000"}, # 30 days
            AssetType.FONT: {"cache_control": "public, max-age=31536000"}, # 1 year
            AssetType.VIDEO: {"cache_control": "public, max-age=604800"},  # 1 week
            AssetType.AUDIO: {"cache_control": "public, max-age=604800"},  # 1 week
            AssetType.DOCUMENT: {"cache_control": "public, max-age=86400"}, # 1 day
            AssetType.OTHER: {"cache_control": "public, max-age=3600"},    # 1 hour
        }

        logger.info(f"CDN Service initialized - CDN enabled: {self.enable_cdn}, Base URL: {self.cdn_base_url}")

    def get_asset_url(self, asset_path: str, force_cdn: bool = False) -> str:
        """Get the URL for a static asset, using CDN if available"""
        # Clean the asset path
        asset_path = asset_path.lstrip('/')

        # Determine if we should use CDN
        use_cdn = (self.enable_cdn or force_cdn) and self.cdn_base_url

        if use_cdn:
            # Use CDN URL
            cdn_url = urljoin(self.cdn_base_url.rstrip('/') + '/', asset_path)
            logger.debug(f"Asset URL (CDN): {asset_path} -> {cdn_url}")
            return cdn_url
        else:
            # Use fallback URL
            fallback_url = urljoin(self.fallback_base_url.rstrip('/') + '/', asset_path)
            logger.debug(f"Asset URL (fallback): {asset_path} -> {fallback_url}")
            return fallback_url

    def get_asset_type(self, asset_path: str) -> AssetType:
        """Determine the asset type based on file extension"""
        # Get file extension
        _, ext = os.path.splitext(asset_path.lower())

        # Find matching asset type
        for asset_type, extensions in self.asset_extensions.items():
            if ext in extensions:
                return asset_type

        return AssetType.OTHER

    def get_cache_headers(self, asset_path: str) -> Dict[str, str]:
        """Get appropriate cache headers for an asset"""
        asset_type = self.get_asset_type(asset_path)
        config = self.cdn_config.get(asset_type, self.cdn_config[AssetType.OTHER])

        headers = {
            "Cache-Control": config["cache_control"],
            "X-Asset-Type": asset_type.value
        }

        # Add CDN headers if using CDN
        if self.enable_cdn and self.cdn_base_url:
            headers["X-CDN-Enabled"] = "true"
            headers["X-CDN-Base-URL"] = self.cdn_base_url
        else:
            headers["X-CDN-Enabled"] = "false"

        return headers

    def is_cdn_url(self, url: str) -> bool:
        """Check if a URL is served from CDN"""
        if not self.cdn_base_url:
            return False

        parsed_url = urlparse(url)
        parsed_cdn = urlparse(self.cdn_base_url)

        return (
            parsed_url.netloc == parsed_cdn.netloc and
            url.startswith(self.cdn_base_url)
        )

    def get_asset_info(self, asset_path: str) -> Dict[str, any]:
        """Get comprehensive information about an asset"""
        asset_type = self.get_asset_type(asset_path)
        cdn_url = self.get_asset_url(asset_path)

        # Force fallback URL generation
        original_enable = self.enable_cdn
        self.enable_cdn = False
        fallback_url = self.get_asset_url(asset_path)
        self.enable_cdn = original_enable

        cache_headers = self.get_cache_headers(asset_path)

        return {
            "asset_path": asset_path,
            "asset_type": asset_type.value,
            "cdn_url": cdn_url,
            "fallback_url": fallback_url,
            "is_cdn_enabled": self.enable_cdn,
            "is_served_from_cdn": self.is_cdn_url(cdn_url),
            "cache_headers": cache_headers
        }

    def batch_get_asset_urls(self, asset_paths: List[str]) -> Dict[str, str]:
        """Get URLs for multiple assets at once"""
        return {
            path: self.get_asset_url(path)
            for path in asset_paths
        }

    def validate_cdn_configuration(self) -> Dict[str, any]:
        """Validate CDN configuration and return status"""
        issues = []

        # Check CDN base URL format
        if self.enable_cdn:
            if not self.cdn_base_url or not self.cdn_base_url.strip():
                issues.append("CDN enabled but no base URL configured")
            else:
                parsed = urlparse(self.cdn_base_url)
                if not parsed.scheme or not parsed.netloc:
                    issues.append(f"Invalid CDN base URL format: {self.cdn_base_url}")

        # Check fallback URL
        if not self.fallback_base_url or not self.fallback_base_url.strip():
            issues.append("No fallback base URL configured")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "cdn_enabled": self.enable_cdn,
            "cdn_base_url": self.cdn_base_url,
            "fallback_base_url": self.fallback_base_url
        }


def create_cdn_service() -> CDNService:
    """Factory function to create CDN service based on environment"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        # In production, CDN should be enabled with proper URLs
        cdn_base_url = os.getenv("CDN_BASE_URL")
        enable_cdn = cdn_base_url is not None

        if enable_cdn:
            logger.info(f"Creating CDN service for production with CDN: {cdn_base_url}")
        else:
            logger.warning("Production environment but no CDN configured")

        return CDNService(
            cdn_base_url=cdn_base_url,
            enable_cdn=enable_cdn
        )
    else:
        # In development, CDN is typically disabled
        logger.info("Creating CDN service for development (CDN disabled)")
        return CDNService(enable_cdn=False)


# Global CDN service instance
_cdn_service: Optional[CDNService] = None


def get_cdn_service() -> CDNService:
    """Get the global CDN service instance"""
    global _cdn_service

    if _cdn_service is None:
        _cdn_service = create_cdn_service()

    return _cdn_service


def reset_cdn_service():
    """Reset the global CDN service (for testing)"""
    global _cdn_service
    _cdn_service = None
