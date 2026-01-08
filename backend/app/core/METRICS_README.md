# CloudWatch Custom Metrics Implementation

This document describes the comprehensive CloudWatch custom metrics implementation for the Stock Analysis API.

## Overview

The metrics system provides comprehensive monitoring and observability for the Stock Analysis API through:

1. **Custom Metrics Emission** - Automatic collection and emission of key performance indicators
2. **CloudWatch Dashboards** - Pre-built dashboards for operational, business, and alerting views
3. **Automated Alarms** - Critical threshold monitoring with alerting capabilities

## Architecture

### Components

- **MetricsCollector** - Collects and aggregates metrics in memory
- **CloudWatchMetricsService** - Emits metrics to AWS CloudWatch
- **MetricsMiddleware** - Automatically tracks API performance metrics
- **CloudWatchDashboardService** - Creates and manages dashWatch dashboards

### Metrics Flow

```
API Request → MetricsMiddleware → MetricsCollector → CloudWatchMetricsService → AWS CloudWatch
```

## Metrics Categories

### 1. API Performance Metrics

- **APIResponseTime** - Response time for each endpoint
- **AverageResponseTime** - Rolling average response time
- **ErrorRate** - Percentage of failed requests
- **ErrorCount** - Count of errors by category

**Dimensions:**
- Endpoint (e.g., `/analyze/{ticker}`, `/quote/{ticker}`)
- Method (GET, POST, PUT, DELETE)
- StatusCode (200, 400, 500, etc.)
- ErrorCategory (validation_error, authentication_error, etc.)

### 2. Cache Performance Metrics

- **CacheHit** - Cache hit events
- **CacheMiss** - Cache miss events  
- **CacheHitRatio** - Percentage of cache hits

**Dimensions:**
- CacheType (memory, redis)

### 3. Business Metrics

- **AnalysisCompleted** - Successful stock analyses
- **AnalysisFailed** - Failed stock analyses
- **AnalysisDuration** - Time taken for analysis
- **AnalysisCompletionRate** - Success rate percentage

**Dimensions:**
- Ticker (AAPL, MSFT, etc.)
- AnalysisType (comprehensive, technology, financial)

### 4. System Metrics

- **ErrorRate** - Overall system error rate
- **AverageResponseTime** - System-wide response time

## Configuration

### Environment Variables

```bash
# Enable/disable CloudWatch metrics
CLOUDWATCH_METRICS_ENABLED=true

# Enable/disable CloudWatch dashboards
CLOUDWATCH_DASHBOARDS_ENABLED=true

# Initialize dashboards on startup (production only)
INIT_DASHBOARDS_ON_STARTUP=false

# Metrics configuration
METRICS_BATCH_SIZE=20
METRICS_FLUSH_INTERVAL=60

# AWS Configuration
AWS_REGION=us-east-1
```

### AWS Permissions

The application requires the following IAM permissions:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData",
                "cloudwatch:PutDashboard",
                "cloudwatch:DeleteDashboards",
                "cloudwatch:ListDashboards",
                "cloudwatch:PutMetricAlarm"
            ],
            "Resource": "*"
        }
    ]
}
```

## Usage

### Automatic Metrics Collection

Metrics are automatically collected through middleware:

```python
# API response times are automatically tracked
# Cache hits/misses are automatically tracked
# Errors are automatically tracked
```

### Manual Metrics Recording

```python
from app.core.metrics import (
    record_api_response_time,
    record_error,
    record_cache_hit,
    record_cache_miss,
    record_analysis_completion
)

# Record custom metrics
await record_api_response_time("/custom", "GET", 150.0, 200)
await record_error("custom_error", "/custom")
await record_cache_hit("redis")
await record_analysis_completion("AAPL", "comprehensive", 5.2, True)
```

### Dashboard Management

Use the dashboard management script:

```bash
# Show dashboard information
python scripts/manage_dashboards.py info

# Create all dashboards and alarms
python scripts/manage_dashboards.py create-all

# Create specific dashboard
python scripts/manage_dashboards.py create operational

# List existing dashboards
python scripts/manage_dashboards.py list

# Delete dashboard
python scripts/manage_dashboards.py delete StockAnalysis-Operational
```

## Dashboards

### 1. Operational Dashboard (`StockAnalysis-Operational`)

**Purpose:** System health and performance monitoring

**Widgets:**
- API Response Time by endpoint
- Error Rate trends
- Cache Hit Ratio
- Cache Operations (hits/misses)
- Average Response Time

### 2. Business Dashboard (`StockAnalysis-Business`)

**Purpose:** Business metrics and analysis performance

**Widgets:**
- Analysis Completion Rate
- Analysis Volume (completed vs failed)
- Analysis Duration by type
- Popular Tickers (most analyzed)

### 3. Alerting Dashboard (`StockAnalysis-Alerting`)

**Purpose:** Critical issues and alerts monitoring

**Widgets:**
- Error Count by Category
- High Response Time Alerts (>1000ms)
- Failed Analyses by type
- Cache Miss Rate

## Alarms

### Critical Thresholds

1. **High Error Rate** - Triggers when error rate > 5%
2. **High Response Time** - Triggers when average response time > 2000ms
3. **Low Cache Hit Ratio** - Triggers when cache hit ratio < 70%
4. **High Analysis Failure Rate** - Triggers when completion rate < 90%

### Alarm Configuration

- **Evaluation Periods:** 2 (10 minutes)
- **Period:** 5 minutes
- **Statistic:** Average
- **Missing Data:** Not breaching

## Monitoring Best Practices

### 1. Key Metrics to Watch

- **Response Time:** Should be < 200ms for cached data, < 2000ms for analysis
- **Error Rate:** Should be < 1% under normal conditions
- **Cache Hit Ratio:** Should be > 80% for optimal performance
- **Analysis Success Rate:** Should be > 95%

### 2. Alert Thresholds

- **Critical:** Immediate attention required (error rate > 5%)
- **Warning:** Monitor closely (response time > 1000ms)
- **Info:** Trending issues (cache hit ratio declining)

### 3. Dashboard Usage

- **Operational:** Daily monitoring by DevOps team
- **Business:** Weekly review by product team
- **Alerting:** Real-time monitoring for incidents

## Troubleshooting

### Common Issues

1. **Metrics Not Appearing**
   - Check AWS credentials and permissions
   - Verify `CLOUDWATCH_METRICS_ENABLED=true`
   - Check application logs for CloudWatch errors

2. **Dashboard Creation Fails**
   - Verify IAM permissions for CloudWatch dashboards
   - Check AWS region configuration
   - Ensure boto3 is installed

3. **High Metric Costs**
   - Reduce `METRICS_FLUSH_INTERVAL` to batch more metrics
   - Filter out high-frequency, low-value metrics
   - Use metric filters to reduce data points

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger("app.core.metrics").setLevel(logging.DEBUG)
```

Check metrics buffer:

```python
from app.core.metrics import get_metrics_service

service = get_metrics_service()
collector = service.get_collector()
metrics = await collector.get_buffered_metrics()
print(f"Buffered metrics: {len(metrics)}")
```

## Performance Considerations

### Metric Batching

- Metrics are batched and sent every 60 seconds by default
- CloudWatch has a limit of 20 metrics per API call
- Large batches are automatically split

### Memory Usage

- Metrics are stored in memory before emission
- Old metrics are automatically cleaned up
- Buffer size is limited to prevent memory leaks

### Cost Optimization

- Custom metrics cost $0.30 per metric per month
- Use dimensions wisely to avoid metric explosion
- Consider sampling for high-frequency metrics

## Integration Examples

### Custom Analysis Tracking

```python
import time
from app.core.metrics import record_analysis_completion

async def analyze_stock(ticker: str):
    start_time = time.time()
    success = False
    
    try:
        # Perform analysis
        result = await perform_analysis(ticker)
        success = True
        return result
    finally:
        duration = time.time() - start_time
        await record_analysis_completion(
            ticker, "comprehensive", duration, success
        )
```

### Custom Cache Integration

```python
from app.core.metrics import record_cache_hit, record_cache_miss

class CustomCache:
    async def get(self, key: str):
        value = await self._get_from_cache(key)
        if value:
            await record_cache_hit("custom")
            return value
        else:
            await record_cache_miss("custom")
            return None
```

## Future Enhancements

1. **Real-time Streaming Metrics** - WebSocket-based metric streaming
2. **Custom Metric Aggregations** - Business-specific KPIs
3. **Anomaly Detection** - ML-based anomaly detection on metrics
4. **Cost Optimization** - Intelligent metric sampling and filtering
5. **Multi-Region Support** - Cross-region metric aggregation