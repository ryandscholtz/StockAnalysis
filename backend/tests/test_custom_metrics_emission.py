"""
Test custom metrics emission functionality
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.core.metrics import (
    CloudWatchMetricsService,
    MetricsCollector,
    MetricData,
    MetricUnit,
    record_api_response_time,
    record_error,
    record_cache_hit,
    record_cache_miss,
    record_analysis_completion
)


class TestMetricsCollector:
    """Test the metrics collector functionality"""

    @pytest.fixture
    def collector(self):
        return MetricsCollector()

    @pytest.mark.asyncio
    async def test_record_api_response_time(self, collector):
        """Test recording API response time"""
        await collector.record_api_response_time("/test", "GET", 150.5, 200)

        metrics = await collector.get_buffered_metrics("api_performance")
        assert len(metrics) == 1

        metric = metrics[0]
        assert metric.name == "APIResponseTime"
        assert metric.value == 150.5
        assert metric.unit == MetricUnit.MILLISECONDS
        assert metric.dimensions["Endpoint"] == "/test"
        assert metric.dimensions["Method"] == "GET"
        assert metric.dimensions["StatusCode"] == "200"

    @pytest.mark.asyncio
    async def test_record_error(self, collector):
        """Test recording errors"""
        await collector.record_error("validation_error", "/test")

        metrics = await collector.get_buffered_metrics("errors")
        assert len(metrics) == 1

        metric = metrics[0]
        assert metric.name == "ErrorCount"
        assert metric.value == 1
        assert metric.unit == MetricUnit.COUNT
        assert metric.dimensions["ErrorCategory"] == "validation_error"
        assert metric.dimensions["Endpoint"] == "/test"

    @pytest.mark.asyncio
    async def test_record_cache_operations(self, collector):
        """Test recording cache hits and misses"""
        await collector.record_cache_hit("redis")
        await collector.record_cache_miss("redis")

        metrics = await collector.get_buffered_metrics("cache")
        assert len(metrics) == 2

        hit_metric = metrics[0]
        assert hit_metric.name == "CacheHit"
        assert hit_metric.value == 1
        assert hit_metric.dimensions["CacheType"] == "redis"

        miss_metric = metrics[1]
        assert miss_metric.name == "CacheMiss"
        assert miss_metric.value == 1
        assert miss_metric.dimensions["CacheType"] == "redis"

    @pytest.mark.asyncio
    async def test_record_analysis_completion(self, collector):
        """Test recording analysis completion"""
        await collector.record_analysis_completion("AAPL", "comprehensive", 5.2, True)
        await collector.record_analysis_completion("MSFT", "comprehensive", 3.1, False)

        metrics = await collector.get_buffered_metrics("business")
        assert len(metrics) == 3  # 2 completion metrics + 1 duration metric

        # Check successful analysis
        success_metrics = [m for m in metrics if m.name == "AnalysisCompleted"]
        assert len(success_metrics) == 1
        assert success_metrics[0].dimensions["Ticker"] == "AAPL"

        # Check failed analysis
        failed_metrics = [m for m in metrics if m.name == "AnalysisFailed"]
        assert len(failed_metrics) == 1
        assert failed_metrics[0].dimensions["Ticker"] == "MSFT"

        # Check duration metric (only for successful analysis)
        duration_metrics = [m for m in metrics if m.name == "AnalysisDuration"]
        assert len(duration_metrics) == 1
        assert duration_metrics[0].value == 5.2

    @pytest.mark.asyncio
    async def test_cache_hit_ratio_calculation(self, collector):
        """Test cache hit ratio calculation"""
        # Record some cache operations
        await collector.record_cache_hit()
        await collector.record_cache_hit()
        await collector.record_cache_miss()

        hit_ratio = await collector.get_cache_hit_ratio()
        assert hit_ratio == 2 / 3  # 2 hits out of 3 total requests

    @pytest.mark.asyncio
    async def test_average_response_time_calculation(self, collector):
        """Test average response time calculation"""
        await collector.record_api_response_time("/test1", "GET", 100.0, 200)
        await collector.record_api_response_time("/test2", "GET", 200.0, 200)
        await collector.record_api_response_time("/test3", "GET", 300.0, 200)

        avg_time = await collector.get_average_response_time()
        assert avg_time == 200.0  # (100 + 200 + 300) / 3


class TestCloudWatchMetricsService:
    """Test the CloudWatch metrics service"""

    @pytest.fixture
    def mock_cloudwatch(self):
        with patch('app.core.metrics.boto3') as mock_boto3:
            mock_client = Mock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def metrics_service(self, mock_cloudwatch):
        with patch.dict('os.environ', {'CLOUDWATCH_METRICS_ENABLED': 'true'}):
            service = CloudWatchMetricsService()
            return service

    @pytest.mark.asyncio
    async def test_emit_single_metric(self, metrics_service, mock_cloudwatch):
        """Test emitting a single metric"""
        mock_cloudwatch.put_metric_data.return_value = {}

        metric = MetricData(
            name="TestMetric",
            value=42.0,
            unit=MetricUnit.COUNT,
            dimensions={"TestDimension": "TestValue"}
        )

        success = await metrics_service.emit_metric(metric)

        assert success
        mock_cloudwatch.put_metric_data.assert_called_once()

        call_args = mock_cloudwatch.put_metric_data.call_args
        assert call_args[1]['Namespace'] == "StockAnalysis/API"
        assert len(call_args[1]['MetricData']) == 1

        metric_data = call_args[1]['MetricData'][0]
        assert metric_data['MetricName'] == "TestMetric"
        assert metric_data['Value'] == 42.0
        assert metric_data['Unit'] == "Count"
        assert len(metric_data['Dimensions']) == 1
        assert metric_data['Dimensions'][0]['Name'] == "TestDimension"
        assert metric_data['Dimensions'][0]['Value'] == "TestValue"

    @pytest.mark.asyncio
    async def test_emit_metrics_batch(self, metrics_service, mock_cloudwatch):
        """Test emitting a batch of metrics"""
        mock_cloudwatch.put_metric_data.return_value = {}

        metrics = [
            MetricData(name="Metric1", value=1.0, unit=MetricUnit.COUNT),
            MetricData(name="Metric2", value=2.0, unit=MetricUnit.COUNT),
            MetricData(name="Metric3", value=3.0, unit=MetricUnit.COUNT)
        ]

        success_count = await metrics_service.emit_metrics_batch(metrics)

        assert success_count == 3
        mock_cloudwatch.put_metric_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_flush_buffered_metrics(self, metrics_service, mock_cloudwatch):
        """Test flushing buffered metrics"""
        mock_cloudwatch.put_metric_data.return_value = {}

        # Add some metrics to the buffer
        collector = metrics_service.get_collector()
        await collector.record_api_response_time("/test", "GET", 100.0, 200)
        await collector.record_error("test_error")

        success_count = await metrics_service.flush_buffered_metrics()

        assert success_count == 2
        mock_cloudwatch.put_metric_data.assert_called_once()

        # Buffer should be cleared after successful flush
        remaining_metrics = await collector.get_buffered_metrics()
        assert len(remaining_metrics) == 0

    def test_disabled_service(self):
        """Test that service works when disabled"""
        with patch.dict('os.environ', {'CLOUDWATCH_METRICS_ENABLED': 'false'}):
            service = CloudWatchMetricsService()
            assert not service.enabled
            assert service.cloudwatch is None


class TestConvenienceFunctions:
    """Test the convenience functions for metrics recording"""

    @pytest.mark.asyncio
    async def test_record_api_response_time_function(self):
        """Test the convenience function for recording API response time"""
        with patch('app.core.metrics.get_metrics_service') as mock_get_service:
            mock_service = Mock()
            mock_collector = Mock()
            mock_collector.record_api_response_time = AsyncMock()
            mock_service.collector = mock_collector
            mock_get_service.return_value = mock_service

            await record_api_response_time("/test", "GET", 150.0, 200)

            mock_collector.record_api_response_time.assert_called_once_with(
                "/test", "GET", 150.0, 200
            )

    @pytest.mark.asyncio
    async def test_record_error_function(self):
        """Test the convenience function for recording errors"""
        with patch('app.core.metrics.get_metrics_service') as mock_get_service:
            mock_service = Mock()
            mock_collector = Mock()
            mock_collector.record_error = AsyncMock()
            mock_service.collector = mock_collector
            mock_get_service.return_value = mock_service

            await record_error("test_error", "/test")

            mock_collector.record_error.assert_called_once_with("test_error", "/test")

    @pytest.mark.asyncio
    async def test_record_cache_operations_functions(self):
        """Test the convenience functions for recording cache operations"""
        with patch('app.core.metrics.get_metrics_service') as mock_get_service:
            mock_service = Mock()
            mock_collector = Mock()
            mock_collector.record_cache_hit = AsyncMock()
            mock_collector.record_cache_miss = AsyncMock()
            mock_service.collector = mock_collector
            mock_get_service.return_value = mock_service

            await record_cache_hit("redis")
            await record_cache_miss("redis")

            mock_collector.record_cache_hit.assert_called_once_with("redis")
            mock_collector.record_cache_miss.assert_called_once_with("redis")

    @pytest.mark.asyncio
    async def test_record_analysis_completion_function(self):
        """Test the convenience function for recording analysis completion"""
        with patch('app.core.metrics.get_metrics_service') as mock_get_service:
            mock_service = Mock()
            mock_collector = Mock()
            mock_collector.record_analysis_completion = AsyncMock()
            mock_service.collector = mock_collector
            mock_get_service.return_value = mock_service

            await record_analysis_completion("AAPL", "comprehensive", 5.2, True)

            mock_collector.record_analysis_completion.assert_called_once_with(
                "AAPL", "comprehensive", 5.2, True
            )
