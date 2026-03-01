"""
CloudWatch Dashboard Management Service
Creates and manages CloudWatch dashboards for monitoring and observability
"""
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from app.core.logging import LoggerMixin


class DashboardType(str, Enum):
    """Types of dashboards"""
    OPERATIONAL = "operational"
    BUSINESS = "business"
    ALERTING = "alerting"


@dataclass
class DashboardWidget:
    """Represents a CloudWatch dashboard widget"""
    type: str  # "metric", "log", "text"
    x: int
    y: int
    width: int
    height: int
    properties: Dict[str, Any]


class CloudWatchDashboardService(LoggerMixin):
    """Service for creating and managing CloudWatch dashboards"""

    def __init__(self, namespace: str = "StockAnalysis/API"):
        self.namespace = namespace
        self.enabled = BOTO3_AVAILABLE and os.getenv("CLOUDWATCH_DASHBOARDS_ENABLED", "true").lower() == "true"
        self.region = os.getenv("AWS_REGION", "us-east-1")

        if self.enabled and BOTO3_AVAILABLE:
            try:
                self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
                self.log_info("CloudWatch dashboard service initialized")
            except (NoCredentialsError, Exception) as e:
                self.log_warning(f"Failed to initialize CloudWatch client: {e}")
                self.enabled = False
        else:
            self.cloudwatch = None
            if not BOTO3_AVAILABLE:
                self.log_warning("boto3 not available, CloudWatch dashboards disabled")
            else:
                self.log_info("CloudWatch dashboards disabled by configuration")

    def _create_metric_widget(
        self,
        title: str,
        metrics: List[List[str]],
        x: int,
        y: int,
        width: int = 12,
        height: int = 6,
        stat: str = "Average",
        period: int = 300,
        view: str = "timeSeries"
    ) -> DashboardWidget:
        """Create a metric widget"""
        return DashboardWidget(
            type="metric",
            x=x,
            y=y,
            width=width,
            height=height,
            properties={
                "metrics": metrics,
                "view": view,
                "stacked": False,
                "region": self.region,
                "title": title,
                "period": period,
                "stat": stat,
                "yAxis": {
                    "left": {
                        "min": 0
                    }
                }
            }
        )

    def _create_text_widget(
        self,
        markdown: str,
        x: int,
        y: int,
        width: int = 24,
        height: int = 2
    ) -> DashboardWidget:
        """Create a text widget with markdown content"""
        return DashboardWidget(
            type="text",
            x=x,
            y=y,
            width=width,
            height=height,
            properties={
                "markdown": markdown
            }
        )

    def _create_operational_dashboard_widgets(self) -> List[DashboardWidget]:
        """Create widgets for operational dashboard"""
        widgets = []

        # Header
        widgets.append(self._create_text_widget(
            markdown="# Stock Analysis API - Operational Dashboard\n\nSystem health and performance metrics",
            x=0, y=0, width=24, height=2
        ))

        # API Response Time
        widgets.append(self._create_metric_widget(
            title="API Response Time",
            metrics=[
                [self.namespace, "APIResponseTime", "Endpoint", "/analyze/{ticker}"],
                [self.namespace, "APIResponseTime", "Endpoint", "/quote/{ticker}"],
                [self.namespace, "APIResponseTime", "Endpoint", "/health"]
            ],
            x=0, y=2, width=12, height=6,
            stat="Average"
        ))

        # Error Rate
        widgets.append(self._create_metric_widget(
            title="Error Rate",
            metrics=[
                [self.namespace, "ErrorRate"]
            ],
            x=12, y=2, width=12, height=6,
            stat="Average"
        ))

        # Cache Performance
        widgets.append(self._create_metric_widget(
            title="Cache Hit Ratio",
            metrics=[
                [self.namespace, "CacheHitRatio"]
            ],
            x=0, y=8, width=12, height=6,
            stat="Average"
        ))

        # Cache Operations
        widgets.append(self._create_metric_widget(
            title="Cache Operations",
            metrics=[
                [self.namespace, "CacheHit", "CacheType", "memory"],
                [self.namespace, "CacheMiss", "CacheType", "memory"],
                [self.namespace, "CacheHit", "CacheType", "redis"],
                [self.namespace, "CacheMiss", "CacheType", "redis"]
            ],
            x=12, y=8, width=12, height=6,
            stat="Sum"
        ))

        # System Performance
        widgets.append(self._create_metric_widget(
            title="Average Response Time by Endpoint",
            metrics=[
                [self.namespace, "AverageResponseTime"]
            ],
            x=0, y=14, width=24, height=6,
            stat="Average"
        ))

        return widgets

    def _create_business_dashboard_widgets(self) -> List[DashboardWidget]:
        """Create widgets for business dashboard"""
        widgets = []

        # Header
        widgets.append(self._create_text_widget(
            markdown="# Stock Analysis API - Business Dashboard\n\nBusiness metrics and analysis performance",
            x=0, y=0, width=24, height=2
        ))

        # Analysis Completion Rate
        widgets.append(self._create_metric_widget(
            title="Analysis Completion Rate",
            metrics=[
                [self.namespace, "AnalysisCompletionRate"]
            ],
            x=0, y=2, width=12, height=6,
            stat="Average"
        ))

        # Analysis Volume
        widgets.append(self._create_metric_widget(
            title="Analysis Volume",
            metrics=[
                [self.namespace, "AnalysisCompleted"],
                [self.namespace, "AnalysisFailed"]
            ],
            x=12, y=2, width=12, height=6,
            stat="Sum"
        ))

        # Analysis Duration
        widgets.append(self._create_metric_widget(
            title="Analysis Duration",
            metrics=[
                [self.namespace, "AnalysisDuration", "AnalysisType", "comprehensive"],
                [self.namespace, "AnalysisDuration", "AnalysisType", "technology"],
                [self.namespace, "AnalysisDuration", "AnalysisType", "financial"]
            ],
            x=0, y=8, width=12, height=6,
            stat="Average"
        ))

        # Popular Tickers
        widgets.append(self._create_metric_widget(
            title="Analysis by Ticker (Top Analyzed)",
            metrics=[
                [self.namespace, "AnalysisCompleted", "Ticker", "AAPL"],
                [self.namespace, "AnalysisCompleted", "Ticker", "MSFT"],
                [self.namespace, "AnalysisCompleted", "Ticker", "GOOGL"],
                [self.namespace, "AnalysisCompleted", "Ticker", "AMZN"],
                [self.namespace, "AnalysisCompleted", "Ticker", "TSLA"]
            ],
            x=12, y=8, width=12, height=6,
            stat="Sum"
        ))

        return widgets

    def _create_alerting_dashboard_widgets(self) -> List[DashboardWidget]:
        """Create widgets for alerting dashboard"""
        widgets = []

        # Header
        widgets.append(self._create_text_widget(
            markdown="# Stock Analysis API - Alerting Dashboard\n\nCritical issues and alerts monitoring",
            x=0, y=0, width=24, height=2
        ))

        # Error Count by Category
        widgets.append(self._create_metric_widget(
            title="Error Count by Category",
            metrics=[
                [self.namespace, "ErrorCount", "ErrorCategory", "validation_error"],
                [self.namespace, "ErrorCount", "ErrorCategory", "authentication_error"],
                [self.namespace, "ErrorCount", "ErrorCategory", "external_api"],
                [self.namespace, "ErrorCount", "ErrorCategory", "database"],
                [self.namespace, "ErrorCount", "ErrorCategory", "internal_error"]
            ],
            x=0, y=2, width=12, height=6,
            stat="Sum"
        ))

        # High Response Time Alerts
        widgets.append(self._create_metric_widget(
            title="High Response Time (>1000ms)",
            metrics=[
                [self.namespace, "APIResponseTime", "Endpoint", "/analyze/{ticker}"],
                [self.namespace, "APIResponseTime", "Endpoint", "/quote/{ticker}"]
            ],
            x=12, y=2, width=12, height=6,
            stat="Maximum"
        ))

        # Failed Analyses
        widgets.append(self._create_metric_widget(
            title="Failed Analyses",
            metrics=[
                [self.namespace, "AnalysisFailed", "AnalysisType", "comprehensive"],
                [self.namespace, "AnalysisFailed", "AnalysisType", "technology"],
                [self.namespace, "AnalysisFailed", "AnalysisType", "financial"]
            ],
            x=0, y=8, width=12, height=6,
            stat="Sum"
        ))

        # Cache Miss Rate (Alert when high)
        widgets.append(self._create_metric_widget(
            title="Cache Miss Rate",
            metrics=[
                [self.namespace, "CacheMiss", "CacheType", "memory"],
                [self.namespace, "CacheMiss", "CacheType", "redis"]
            ],
            x=12, y=8, width=12, height=6,
            stat="Sum"
        ))

        return widgets

    def _widgets_to_dashboard_body(self, widgets: List[DashboardWidget]) -> str:
        """Convert widgets to dashboard body JSON"""
        dashboard_widgets = []

        for widget in widgets:
            dashboard_widget = {
                "type": widget.type,
                "x": widget.x,
                "y": widget.y,
                "width": widget.width,
                "height": widget.height,
                "properties": widget.properties
            }
            dashboard_widgets.append(dashboard_widget)

        dashboard_body = {
            "widgets": dashboard_widgets
        }

        return json.dumps(dashboard_body)

    async def create_dashboard(self, dashboard_type: DashboardType, dashboard_name: str = None) -> bool:
        """Create a CloudWatch dashboard"""
        if not self.enabled:
            self.log_warning("CloudWatch dashboards disabled, skipping dashboard creation")
            return False

        try:
            # Generate dashboard name if not provided
            if not dashboard_name:
                dashboard_name = f"StockAnalysis-{dashboard_type.value.title()}"

            # Get widgets based on dashboard type
            if dashboard_type == DashboardType.OPERATIONAL:
                widgets = self._create_operational_dashboard_widgets()
            elif dashboard_type == DashboardType.BUSINESS:
                widgets = self._create_business_dashboard_widgets()
            elif dashboard_type == DashboardType.ALERTING:
                widgets = self._create_alerting_dashboard_widgets()
            else:
                raise ValueError(f"Unknown dashboard type: {dashboard_type}")

            # Convert widgets to dashboard body
            dashboard_body = self._widgets_to_dashboard_body(widgets)

            # Create the dashboard
            response = self.cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=dashboard_body
            )

            self.log_info(
                f"Created CloudWatch dashboard: {dashboard_name}",
                dashboard_type=dashboard_type.value,
                widget_count=len(widgets)
            )

            return True

        except Exception as e:
            self.log_error(f"Failed to create dashboard {dashboard_name}: {e}")
            return False

    async def create_all_dashboards(self) -> Dict[str, bool]:
        """Create all standard dashboards"""
        results = {}

        for dashboard_type in DashboardType:
            dashboard_name = f"StockAnalysis-{dashboard_type.value.title()}"
            success = await self.create_dashboard(dashboard_type, dashboard_name)
            results[dashboard_name] = success

        return results

    async def delete_dashboard(self, dashboard_name: str) -> bool:
        """Delete a CloudWatch dashboard"""
        if not self.enabled:
            return False

        try:
            self.cloudwatch.delete_dashboards(
                DashboardNames=[dashboard_name]
            )

            self.log_info(f"Deleted CloudWatch dashboard: {dashboard_name}")
            return True

        except Exception as e:
            self.log_error(f"Failed to delete dashboard {dashboard_name}: {e}")
            return False

    async def list_dashboards(self) -> List[str]:
        """List all CloudWatch dashboards"""
        if not self.enabled:
            return []

        try:
            response = self.cloudwatch.list_dashboards()
            dashboard_names = [
                dashboard['DashboardName']
                for dashboard in response.get('DashboardEntries', [])
                if dashboard['DashboardName'].startswith('StockAnalysis-')
            ]

            return dashboard_names

        except Exception as e:
            self.log_error(f"Failed to list dashboards: {e}")
            return []

    async def create_alarms(self) -> Dict[str, bool]:
        """Create CloudWatch alarms for critical metrics"""
        if not self.enabled:
            return {}

        alarms = [
            {
                "name": "StockAnalysis-HighErrorRate",
                "description": "Alert when error rate exceeds 5%",
                "metric_name": "ErrorRate",
                "threshold": 5.0,
                "comparison": "GreaterThanThreshold"
            },
            {
                "name": "StockAnalysis-HighResponseTime",
                "description": "Alert when average response time exceeds 2000ms",
                "metric_name": "AverageResponseTime",
                "threshold": 2000.0,
                "comparison": "GreaterThanThreshold"
            },
            {
                "name": "StockAnalysis-LowCacheHitRatio",
                "description": "Alert when cache hit ratio falls below 70%",
                "metric_name": "CacheHitRatio",
                "threshold": 70.0,
                "comparison": "LessThanThreshold"
            },
            {
                "name": "StockAnalysis-HighAnalysisFailureRate",
                "description": "Alert when analysis completion rate falls below 90%",
                "metric_name": "AnalysisCompletionRate",
                "threshold": 90.0,
                "comparison": "LessThanThreshold"
            }
        ]

        results = {}

        for alarm_config in alarms:
            try:
                self.cloudwatch.put_metric_alarm(
                    AlarmName=alarm_config["name"],
                    ComparisonOperator=alarm_config["comparison"],
                    EvaluationPeriods=2,
                    MetricName=alarm_config["metric_name"],
                    Namespace=self.namespace,
                    Period=300,  # 5 minutes
                    Statistic='Average',
                    Threshold=alarm_config["threshold"],
                    ActionsEnabled=True,
                    AlarmDescription=alarm_config["description"],
                    Unit='None',
                    TreatMissingData='notBreaching'
                )

                results[alarm_config["name"]] = True
                self.log_info(f"Created alarm: {alarm_config['name']}")

            except Exception as e:
                results[alarm_config["name"]] = False
                self.log_error(f"Failed to create alarm {alarm_config['name']}: {e}")

        return results


# Global dashboard service instance
_dashboard_service: Optional[CloudWatchDashboardService] = None


def get_dashboard_service() -> CloudWatchDashboardService:
    """Get the global dashboard service instance"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = CloudWatchDashboardService()
    return _dashboard_service


async def initialize_dashboards():
    """Initialize dashboards and alarms"""
    service = get_dashboard_service()
    if service.enabled:
        # Create all dashboards
        dashboard_results = await service.create_all_dashboards()

        # Create alarms
        alarm_results = await service.create_alarms()

        service.log_info(
            "Dashboard initialization complete",
            dashboards_created=sum(dashboard_results.values()),
            alarms_created=sum(alarm_results.values())
        )

        return {
            "dashboards": dashboard_results,
            "alarms": alarm_results
        }

    return {"dashboards": {}, "alarms": {}}
