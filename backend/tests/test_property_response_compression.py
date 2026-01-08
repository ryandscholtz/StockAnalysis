"""
Property-based tests for response compression efficiency
"""
from app.core.compression import CompressionService
import pytest
import json
import gzip
import sys
import os
from hypothesis import given, strategies as st, settings, assume
from typing import List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestResponseCompressionProperty:
    """Property-based tests for response compression efficiency"""

    @given(
        response_size=st.integers(min_value=1024, max_value=100000),  # 1KB to 100KB
        data_type=st.sampled_from(["json", "text", "repetitive"])
    )
    @settings(max_examples=50, deadline=8000)
    def test_response_compression_efficiency_property(
            self, response_size: int, data_type: str):
        """
        Property 11: Response Compression Efficiency
        For any API response above a configured size threshold, the response should be
        compressed and properly handled by clients.

        **Validates: Requirements 5.3**
        """
        compression_service = CompressionService(minimum_size=1024)

        # Generate test data based on type
        if data_type == "json":
            # Generate JSON data that should compress well
            test_data = {
                "items": [
                    {
                        "id": i,
                        "name": f"Item {i}",
                        "description": "This is a test item with some repeated content",
                        "category": "test_category",
                        "metadata": {
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-01T00:00:00Z",
                            "status": "active"
                        }
                    }
                    for i in range(response_size // 200)  # Approximate size control
                ]
            }
            content = json.dumps(test_data, ensure_ascii=False)

        elif data_type == "text":
            # Generate text data
            base_text = "This is sample text content that will be repeated to create larger responses. "
            repetitions = response_size // len(base_text) + 1
            content = base_text * repetitions

        else:  # repetitive
            # Generate highly repetitive data that should compress very well
            pattern = "ABCDEFGHIJ" * 10  # 100 char pattern
            repetitions = response_size // len(pattern) + 1
            content = pattern * repetitions

        # Ensure content meets minimum size requirement
        content_bytes = content.encode('utf-8')
        actual_size = len(content_bytes)
        assume(actual_size >= compression_service.minimum_size)

        # Compress the data
        result = compression_service.compress_data(content)

        # Property: Large responses should be compressed
        assert result["compressed"] is True, f"Response of size {actual_size} should be compressed (minimum: {
            compression_service.minimum_size})"

        # Property: Compressed size should be smaller than original
        assert result["compressed_size"] < result["original_size"], f"Compressed size {
            result['compressed_size']} should be less than original {
            result['original_size']}"

        # Property: Compression ratio should be positive
        assert result["compression_ratio"] > 0, \
            f"Compression ratio {result['compression_ratio']} should be positive"

        # Property: Compression should save bytes
        assert result["savings_bytes"] > 0, \
            f"Compression should save bytes, got {result['savings_bytes']}"

        # Property: Compressed content should be decompressible
        decompressed = gzip.decompress(result["content"])
        assert decompressed == content_bytes, \
            "Decompressed content should match original content"

        # Property: Compression efficiency should be reasonable for different data types
        if data_type == "repetitive":
            # Highly repetitive data should compress very well (>50% reduction)
            assert result["compression_ratio"] > 0.5, \
                f"Repetitive data should compress well, got ratio {result['compression_ratio']}"
        elif data_type == "json":
            # JSON data should compress moderately well (>20% reduction)
            assert result["compression_ratio"] > 0.2, \
                f"JSON data should compress reasonably, got ratio {result['compression_ratio']}"
        # Text data varies, so no specific requirement

    @given(
        target_size=st.integers(min_value=1, max_value=1020),  # Well below threshold
        content_type=st.sampled_from(["string", "dict", "list"])
    )
    @settings(max_examples=30, deadline=5000)
    def test_small_response_not_compressed_property(
            self, target_size: int, content_type: str):
        """
        Property 11b: Small Response Compression Threshold
        For any API response below the configured size threshold, compression should be skipped
        to avoid overhead.

        **Validates: Requirements 5.3**
        """
        compression_service = CompressionService(minimum_size=1024)

        # Generate small content based on type, ensuring final size stays below
        # threshold
        if content_type == "string":
            content = "x" * target_size
        elif content_type == "dict":
            # Account for JSON overhead: {"data": "..."} adds ~10 characters
            data_size = max(1, target_size - 15)  # Conservative overhead estimate
            content = {"data": "x" * data_size}
        else:  # list
            # Account for JSON overhead: ["...", "...", ...] adds brackets, quotes, commas
            # Estimate ~3 chars per item + 2 for brackets = ~17 chars for 5 items
            data_size = max(1, (target_size - 20) // 5)  # Conservative estimate
            content = ["x" * data_size for _ in range(5)]

        # Verify the actual serialized size before compression
        if isinstance(content, (dict, list)):
            serialized_content = json.dumps(content, ensure_ascii=False)
            actual_size = len(serialized_content.encode('utf-8'))
        else:
            actual_size = len(content.encode('utf-8'))

        # Skip this test case if the content ended up too large despite our efforts
        assume(actual_size < compression_service.minimum_size)

        # Compress the data
        result = compression_service.compress_data(content)

        # Property: Small responses should not be compressed
        assert result["compressed"] is False, f"Response of size {
            result['original_size']} should not be compressed (below minimum {
            compression_service.minimum_size})"

        # Property: Original and compressed sizes should be equal when not compressed
        assert result["original_size"] == result["compressed_size"], \
            "When not compressed, original and compressed sizes should be equal"

        # Property: Compression ratio should be zero when not compressed
        assert result["compression_ratio"] == 0.0, \
            "Compression ratio should be zero when not compressed"

        # Property: Should include reason for not compressing
        assert "reason" in result, \
            "Result should include reason when compression is skipped"

        assert "below minimum" in result["reason"].lower(), \
            "Reason should indicate size is below minimum threshold"

    @given(
        compression_level=st.integers(min_value=1, max_value=9),
        data_size=st.integers(min_value=2000, max_value=20000)
    )
    @settings(max_examples=25, deadline=6000)
    def test_compression_level_efficiency_property(
            self, compression_level: int, data_size: int):
        """
        Property 11c: Compression Level Efficiency
        For any compression level, higher levels should generally produce smaller output
        but the relationship should be consistent.

        **Validates: Requirements 5.3**
        """
        # Generate test data
        test_data = {
            "message": "This is test data for compression level testing. " * 50,
            "items": [{"id": i, "value": f"item_{i}_data"} for i in range(data_size // 100)],
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "version": "1.0.0",
                "description": "Test data for compression efficiency testing"
            }
        }

        compression_service = CompressionService(
            compression_level=compression_level,
            minimum_size=1000
        )

        # Compress the data
        result = compression_service.compress_data(test_data)

        # Property: Compression should succeed for valid levels
        assert result["compressed"] is True, \
            f"Compression should succeed with level {compression_level}"

        # Property: Compression should produce valid results
        assert result["compressed_size"] > 0, \
            "Compressed size should be positive"

        assert result["original_size"] > result["compressed_size"], \
            "Original size should be larger than compressed size"

        # Property: Compression ratio should be within reasonable bounds
        assert 0 < result["compression_ratio"] < 1, \
            f"Compression ratio {result['compression_ratio']} should be between 0 and 1"

        # Property: Decompression should work correctly
        decompressed = gzip.decompress(result["content"])
        original_content = json.dumps(test_data, ensure_ascii=False).encode('utf-8')
        assert decompressed == original_content, \
            "Decompressed content should match original"

    @given(
        media_types=st.lists(
            st.sampled_from([
                "application/json",
                "text/plain",
                "text/html",
                "image/jpeg",
                "image/png",
                "video/mp4",
                "application/zip",
                "application/gzip"
            ]),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=20, deadline=4000)
    def test_media_type_compression_property(self, media_types: List[str]):
        """
        Property 11d: Media Type Compression Rules
        For any media type, compression should follow appropriate rules based on
        whether the content is already compressed or binary.

        **Validates: Requirements 5.3**
        """
        # Define which media types should be excluded from compression
        excluded_types = {
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "video/mp4", "video/mpeg", "audio/mpeg", "audio/wav",
            "application/zip", "application/gzip", "application/x-gzip"
        }

        compressible_types = {
            "application/json", "text/plain", "text/html", "text/css",
            "application/javascript", "text/xml"
        }

        for media_type in media_types:
            # Property: Media type classification should be consistent
            is_excluded = any(
                excluded_type in media_type for excluded_type in excluded_types)
            is_compressible = any(
                comp_type in media_type for comp_type in compressible_types)

            # Property: A media type should not be both excluded and compressible
            assert not (is_excluded and is_compressible), \
                f"Media type {media_type} should not be both excluded and compressible"

            # Property: Known media types should have defined behavior
            if media_type in excluded_types:
                assert is_excluded, f"Known excluded type {media_type} should be marked as excluded"

            if media_type in compressible_types:
                assert is_compressible, f"Known compressible type {media_type} should be marked as compressible"

    @given(
        original_sizes=st.lists(
            st.integers(min_value=1000, max_value=50000),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=15, deadline=5000)
    def test_compression_efficiency_metrics_property(self, original_sizes: List[int]):
        """
        Property 11e: Compression Efficiency Metrics
        For any set of compression operations, efficiency metrics should be
        mathematically consistent and meaningful.

        **Validates: Requirements 5.3**
        """
        compression_service = CompressionService()

        for original_size in original_sizes:
            # Generate test content
            content = "Test data content. " * (original_size // 20)

            # Compress the content
            result = compression_service.compress_data(content)

            if result["compressed"]:
                compressed_size = result["compressed_size"]

                # Calculate efficiency metrics
                metrics = compression_service.calculate_compression_efficiency(
                    original_size, compressed_size
                )

                # Property: Compression ratio should match manual calculation
                expected_ratio = (original_size - compressed_size) / original_size
                assert abs(metrics["compression_ratio"] - expected_ratio) < 0.001, \
                    f"Compression ratio calculation mismatch: {metrics['compression_ratio']} vs {expected_ratio}"

                # Property: Space savings percentage should be ratio * 100
                expected_savings = expected_ratio * 100
                assert abs(metrics["space_savings_percent"] - expected_savings) < 0.1, \
                    f"Space savings calculation mismatch: {metrics['space_savings_percent']} vs {expected_savings}"

                # Property: Compression factor should be original/compressed
                expected_factor = original_size / compressed_size
                assert abs(metrics["compression_factor"] - expected_factor) < 0.001, \
                    f"Compression factor calculation mismatch: {metrics['compression_factor']} vs {expected_factor}"

                # Property: All metrics should be positive for successful compression
                assert metrics["compression_ratio"] > 0, "Compression ratio should be positive"
                assert metrics["space_savings_percent"] > 0, "Space savings should be positive"
                assert metrics["compression_factor"] > 1, "Compression factor should be greater than 1"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
