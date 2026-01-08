"""
Response compression middleware for FastAPI
"""
import gzip
import json
import logging
from typing import Any, Dict, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import io

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware to compress API responses when appropriate"""

    def __init__(
        self,
        app,
        minimum_size: int = 1024,  # Minimum response size to compress (1KB)
        compression_level: int = 6,  # gzip compression level (1-9)
        exclude_media_types: Optional[set] = None
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level
        self.exclude_media_types = exclude_media_types or {
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "video/mp4", "video/mpeg", "audio/mpeg", "audio/wav",
            "application/zip", "application/gzip", "application/x-gzip"
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and compress response if appropriate"""
        # Get the response from the next middleware/endpoint
        response = await call_next(request)

        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response

        # Check if response should be compressed
        if not self._should_compress_response(response):
            return response

        # Get response content
        response_content = await self._get_response_content(response)

        if response_content is None or len(response_content) < self.minimum_size:
            return response

        # Compress the content
        compressed_content = self._compress_content(response_content)

        # Calculate compression ratio
        original_size = len(response_content)
        compressed_size = len(compressed_content)
        compression_ratio = (original_size - compressed_size) / original_size if original_size > 0 else 0

        # Log compression stats
        logger.debug(
            f"Response compressed: {original_size} -> {compressed_size} bytes "
            f"({compression_ratio:.2%} reduction)"
        )

        # Create new response with compressed content
        compressed_response = Response(
            content=compressed_content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

        # Add compression headers
        compressed_response.headers["content-encoding"] = "gzip"
        compressed_response.headers["content-length"] = str(compressed_size)
        compressed_response.headers["vary"] = "Accept-Encoding"

        # Add custom header with compression stats for testing
        compressed_response.headers["x-compression-ratio"] = f"{compression_ratio:.3f}"
        compressed_response.headers["x-original-size"] = str(original_size)
        compressed_response.headers["x-compressed-size"] = str(compressed_size)

        return compressed_response

    def _should_compress_response(self, response: Response) -> bool:
        """Determine if response should be compressed"""
        # Don't compress if already compressed
        if response.headers.get("content-encoding"):
            return False

        # Don't compress certain media types
        media_type = getattr(response, 'media_type', None) or response.headers.get("content-type", "")
        if any(excluded_type in media_type for excluded_type in self.exclude_media_types):
            return False

        # Don't compress error responses below 400 (but do compress 4xx and 5xx)
        if hasattr(response, 'status_code') and response.status_code < 200:
            return False

        return True

    async def _get_response_content(self, response: Response) -> Optional[bytes]:
        """Extract content from response"""
        try:
            if hasattr(response, 'body'):
                # For regular Response objects
                content = response.body
                if isinstance(content, str):
                    return content.encode('utf-8')
                elif isinstance(content, bytes):
                    return content

            elif isinstance(response, JSONResponse):
                # For JSONResponse objects, serialize the content
                if hasattr(response, 'content'):
                    content = json.dumps(response.content, ensure_ascii=False)
                    return content.encode('utf-8')

            elif isinstance(response, StreamingResponse):
                # For streaming responses, collect all chunks
                chunks = []
                async for chunk in response.body_iterator:
                    if isinstance(chunk, str):
                        chunks.append(chunk.encode('utf-8'))
                    elif isinstance(chunk, bytes):
                        chunks.append(chunk)

                if chunks:
                    return b''.join(chunks)

            return None

        except Exception as e:
            logger.error(f"Error extracting response content: {e}")
            return None

    def _compress_content(self, content: bytes) -> bytes:
        """Compress content using gzip"""
        try:
            return gzip.compress(content, compresslevel=self.compression_level)
        except Exception as e:
            logger.error(f"Error compressing content: {e}")
            return content


class CompressionService:
    """Service for handling response compression"""

    def __init__(self, compression_level: int = 6, minimum_size: int = 1024):
        self.compression_level = compression_level
        self.minimum_size = minimum_size

    def compress_data(self, data: Any, force: bool = False) -> Dict[str, Any]:
        """Compress data and return compression statistics"""
        # Serialize data to bytes
        if isinstance(data, (dict, list)):
            content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        elif isinstance(data, str):
            content = data.encode('utf-8')
        elif isinstance(data, bytes):
            content = data
        else:
            content = str(data).encode('utf-8')

        original_size = len(content)

        # Check if compression is worthwhile
        if not force and original_size < self.minimum_size:
            return {
                "compressed": False,
                "original_size": original_size,
                "compressed_size": original_size,
                "compression_ratio": 0.0,
                "content": content,
                "reason": f"Size {original_size} below minimum {self.minimum_size}"
            }

        # Compress the content
        try:
            compressed_content = gzip.compress(content, compresslevel=self.compression_level)
            compressed_size = len(compressed_content)
            compression_ratio = (original_size - compressed_size) / original_size if original_size > 0 else 0

            return {
                "compressed": True,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "compression_ratio": compression_ratio,
                "content": compressed_content,
                "savings_bytes": original_size - compressed_size
            }

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return {
                "compressed": False,
                "original_size": original_size,
                "compressed_size": original_size,
                "compression_ratio": 0.0,
                "content": content,
                "error": str(e)
            }

    def decompress_data(self, compressed_data: bytes) -> Dict[str, Any]:
        """Decompress data and return statistics"""
        try:
            decompressed_content = gzip.decompress(compressed_data)

            return {
                "success": True,
                "compressed_size": len(compressed_data),
                "decompressed_size": len(decompressed_content),
                "content": decompressed_content
            }

        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": compressed_data
            }

    def calculate_compression_efficiency(self, original_size: int, compressed_size: int) -> Dict[str, float]:
        """Calculate compression efficiency metrics"""
        if original_size == 0:
            return {
                "compression_ratio": 0.0,
                "space_savings_percent": 0.0,
                "compression_factor": 1.0
            }

        compression_ratio = (original_size - compressed_size) / original_size
        space_savings_percent = compression_ratio * 100
        compression_factor = original_size / compressed_size if compressed_size > 0 else float('inf')

        return {
            "compression_ratio": compression_ratio,
            "space_savings_percent": space_savings_percent,
            "compression_factor": compression_factor
        }


# Global compression service instance
compression_service = CompressionService()


def get_compression_service() -> CompressionService:
    """Get the global compression service instance"""
    return compression_service
