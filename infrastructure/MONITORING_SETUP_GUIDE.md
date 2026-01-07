# Production Monitoring Setup Guide

## Overview

This guide provides step-by-step instructions for setting up comprehensive monitoring and alerting for the Stock Analysis production system.

## Prerequisites

- AWS CLI configured with appropriate permissions
- CDK CLI installed (`npm install -g aws-cdk`)
- Production infrastructure deployed
- Email address for alerts
- Slack workspace with webhook URL (optional)

## Monitoring Components

### 1. CloudWatch Alarms

The system includes the following production alarms:

#### API Gateway Alarms
- **API Error Rate**: Monitors 5XX errors from API Gateway
- **API Latency**: Monitors response time performance
- **API Throttling**: Monitors request throttling

#### Lambda Function Alarms
- **Lambda Error Rate**: Monitors function execution errors
- **Lambda Duration**: Monitors function execution time
- **Lambda Throttling**: Monitors function throttling
- **Lambda Concurrent Executions**: Monitors concurrent execution limits

#### DynamoDB Alarms
- **DynamoDB Throttling**: Monitors read/write throttling
- **DynamoDB System Errors**: Monitors system-level errors

#### Business Logic Alarms
- **Analysis Failure Rate**: Monitors stock analysis failures
- **Data Quality**: Monitors data quality issues

#### Composite Alarms
- **System Health**: Overall system health indicator

### 2. SNS Topics

Two SNS topics are created for different alert severities:

- **General Alerts** (`stock-analysis-alerts-production`): Non-critical alerts
- **Critical Alerts** (`stock-analysis-critical-alerts-production`): Immediate attention required

### 3. CloudWatch Dashboard

A comprehensive dashboard is created with widgets for:
- API Gateway metrics (requests, latency, errors)
- Lambda function metrics (invocations, duration, errors)
- DynamoDB metrics (capacity, throttling)

## Setup Instructions

### Step 1: Configure Alert Email

Set up email notifications for alerts:

```powershell
# Deploy with email alerts
.\deploy-production.ps1 -Environment production -AlertEmail "alerts@yourcompany.com"
```

### Step 2: Configure Slack Notifications (Optional)

1. **Create Slack Webhook**:
   - Go to your Slack workspace settings
   - Navigate to "Apps" → "Incoming Webhooks"
   - Create a new webhook for your alerts channel
   - Copy the webhook URL

2. **Deploy with Slack Integration**:
```powershell
# Deploy with both email and Slack alerts
.\deploy-production.ps1 -Environment production -AlertEmail "alerts@yourcompany.com" -SlackWebhookUrl "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Step 3: Verify Alert Setup

After deployment, verify that alerts are configured correctly:

1. **Check SNS Topics**:
```bash
# List SNS topics
aws sns list-topics --query 'Topics[?contains(TopicArn, `stock-analysis`)]'

# Check subscriptions
aws sns list-subscriptions-by-topic --topic-arn "arn:aws:sns:eu-west-1:ACCOUNT:stock-analysis-alerts-production"
```

2. **Check CloudWatch Alarms**:
```bash
# List all alarms
aws cloudwatch describe-alarms --alarm-names $(aws cloudwatch describe-alarms --query 'MetricAlarms[?contains(AlarmName, `stock-analysis`)].AlarmName' --output text)
```

3. **Test Email Notifications**:
```bash
# Manually trigger a test alarm
aws sns publish --topic-arn "arn:aws:sns:eu-west-1:ACCOUNT:stock-analysis-alerts-production" --message "Test alert message"
```

### Step 4: Access Monitoring Dashboard

1. **Get Dashboard URL** from CDK outputs:
```bash
# Check deployment outputs
cat outputs-production.json
```

2. **Access Dashboard**:
   - Open the CloudWatch console
   - Navigate to Dashboards
   - Open `stock-analysis-production` dashboard

## Alert Configuration Details

### Alarm Thresholds

| Alarm | Threshold | Evaluation Period | Description |
|-------|-----------|-------------------|-------------|
| API Error Rate | 10 errors | 2 periods of 5 min | High 5XX error rate |
| API Latency | 5000ms | 3 periods of 5 min | High response time |
| API Throttling | 50 requests | 2 periods of 5 min | Request throttling |
| Lambda Error Rate | 5 errors | 2 periods of 5 min | High function errors |
| Lambda Duration | 25000ms | 3 periods of 5 min | Long execution time |
| Lambda Throttling | 1 throttle | 1 period of 5 min | Function throttling |
| Lambda Concurrent | 800 executions | 2 periods of 5 min | High concurrency |
| DynamoDB Throttling | 1 throttle | 1 period of 5 min | Database throttling |
| DynamoDB Errors | 5 errors | 2 periods of 5 min | System errors |
| Analysis Failures | 10 failures | 2 periods of 10 min | Business logic failures |
| Data Quality | 20% low quality | 2 periods of 15 min | Data quality issues |

### Alert Routing

| Alert Type | SNS Topic | Notification Method |
|------------|-----------|-------------------|
| General | `stock-analysis-alerts-production` | Email + Slack |
| Critical | `stock-analysis-critical-alerts-production` | Email + Slack |

**Critical Alerts** (require immediate attention):
- API throttling
- Lambda throttling
- DynamoDB throttling
- System health composite alarm

**General Alerts** (require investigation):
- High error rates
- Performance degradation
- Data quality issues

## Custom Metrics

The application emits custom metrics to CloudWatch:

### Business Metrics
- **Namespace**: `StockAnalysis/Business`
- **Metrics**:
  - `AnalysisFailures`: Count of failed stock analyses
  - `AnalysisSuccesses`: Count of successful analyses
  - `AnalysisLatency`: Time taken for analysis

### Data Quality Metrics
- **Namespace**: `StockAnalysis/DataQuality`
- **Metrics**:
  - `LowQualityDataPercentage`: Percentage of low-quality data
  - `DataValidationFailures`: Count of validation failures
  - `MissingDataPoints`: Count of missing data points

### Usage Metrics
- **Namespace**: `StockAnalysis/Usage`
- **Metrics**:
  - `ActiveUsers`: Number of active users
  - `APICallsPerUser`: API calls per user
  - `CacheHitRate`: Cache hit percentage

## Monitoring Best Practices

### 1. Alert Fatigue Prevention
- Set appropriate thresholds to avoid false positives
- Use composite alarms for system-level health
- Implement alert suppression during maintenance

### 2. Escalation Procedures
- Configure different notification channels for different severities
- Set up on-call rotations using PagerDuty or similar
- Document escalation procedures in the runbook

### 3. Regular Review
- Review alarm thresholds monthly
- Analyze false positive rates
- Update thresholds based on system behavior

### 4. Dashboard Optimization
- Organize widgets by system component
- Use appropriate time ranges for different metrics
- Add annotations for deployments and incidents

## Troubleshooting

### Common Issues

#### 1. Email Notifications Not Received
```bash
# Check SNS topic subscriptions
aws sns list-subscriptions-by-topic --topic-arn "TOPIC_ARN"

# Check subscription confirmation
aws sns get-subscription-attributes --subscription-arn "SUBSCRIPTION_ARN"
```

**Solution**: Confirm email subscription in your inbox

#### 2. Slack Notifications Not Working
```bash
# Check Lambda function logs
aws logs filter-log-events --log-group-name "/aws/lambda/stock-analysis-slack-notifications-production" --start-time $(date -d '1 hour ago' +%s)000
```

**Solution**: Verify webhook URL and Lambda function permissions

#### 3. Alarms Not Triggering
```bash
# Check alarm state
aws cloudwatch describe-alarms --alarm-names "ALARM_NAME"

# Check metric data
aws cloudwatch get-metric-statistics --namespace "NAMESPACE" --metric-name "METRIC_NAME" --start-time $(date -d '1 hour ago' --iso-8601) --end-time $(date --iso-8601) --period 300 --statistics Sum
```

**Solution**: Verify metric data is being published and thresholds are appropriate

#### 4. Dashboard Not Loading
- Check CloudWatch service status
- Verify IAM permissions for dashboard access
- Clear browser cache and try again

## Maintenance

### Monthly Tasks
- [ ] Review alarm thresholds and adjust if needed
- [ ] Check for new AWS monitoring features
- [ ] Update contact information for alerts
- [ ] Review dashboard layout and metrics

### Quarterly Tasks
- [ ] Conduct incident response drill
- [ ] Review and update runbook procedures
- [ ] Analyze monitoring costs and optimize
- [ ] Update monitoring documentation

### Annual Tasks
- [ ] Complete monitoring system audit
- [ ] Review and update monitoring strategy
- [ ] Evaluate new monitoring tools and services
- [ ] Update disaster recovery procedures

## Cost Optimization

### CloudWatch Costs
- **Metrics**: $0.30 per metric per month
- **Alarms**: $0.10 per alarm per month
- **Dashboard**: $3.00 per dashboard per month
- **Logs**: $0.50 per GB ingested

### Optimization Tips
1. Use metric filters to reduce log ingestion
2. Set appropriate log retention periods
3. Use composite alarms to reduce alarm count
4. Archive old dashboard versions

## Support and Resources

### AWS Documentation
- [CloudWatch User Guide](https://docs.aws.amazon.com/cloudwatch/)
- [SNS Developer Guide](https://docs.aws.amazon.com/sns/)
- [CloudWatch Alarms](https://docs.aws.amazon.com/cloudwatch/latest/monitoring/AlarmThatSendsEmail.html)

### Internal Resources
- **Runbook**: `infrastructure/INCIDENT_RESPONSE_RUNBOOK.md`
- **Architecture**: `infrastructure/docs/architecture.md`
- **Deployment Guide**: `infrastructure/PRODUCTION_DEPLOYMENT.md`

### Contact Information
- **Engineering Team**: [Team Contact]
- **DevOps Team**: [DevOps Contact]
- **On-Call**: Check PagerDuty schedule

---

**Document Version**: 1.0  
**Last Updated**: [Current Date]  
**Next Review**: [Date + 3 months]  
**Owner**: DevOps Team