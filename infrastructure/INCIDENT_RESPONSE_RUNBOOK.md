# Stock Analysis System - Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to incidents in the Stock Analysis production system. It covers common scenarios, escalation procedures, and recovery steps.

## Alert Categories

### 🟡 General Alerts (Non-Critical)
- Performance degradation
- Elevated error rates (within acceptable limits)
- Resource utilization warnings
- Data quality issues

### 🔴 Critical Alerts (Immediate Action Required)
- System outages
- Service throttling
- Security incidents
- Data corruption
- Complete service failures

## Incident Response Team

### Primary On-Call Engineer
- **Responsibility**: First responder for all alerts
- **Response Time**: 15 minutes for critical, 1 hour for general
- **Actions**: Initial assessment, immediate mitigation, escalation if needed

### Secondary On-Call Engineer
- **Responsibility**: Backup support and complex issue resolution
- **Response Time**: 30 minutes after escalation
- **Actions**: Deep technical investigation, coordination with AWS support

### Engineering Manager
- **Responsibility**: Incident coordination and communication
- **Response Time**: 1 hour for critical incidents
- **Actions**: Stakeholder communication, resource allocation, post-incident review

## Alert Response Procedures

### API Gateway Alerts

#### High Error Rate (5XX Errors)
**Alert**: `stock-analysis-api-error-rate-production`

**Immediate Actions**:
1. Check CloudWatch Dashboard for error patterns
2. Review Lambda function logs in CloudWatch Logs
3. Verify DynamoDB table health
4. Check external API dependencies

**Investigation Steps**:
```bash
# Check recent deployments
aws lambda get-function --function-name stock-analysis-api-production

# Review error logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/stock-analysis-api-production \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Check API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name 5XXError \
  --dimensions Name=ApiName,Value="Stock Analysis API - production" \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum
```

**Mitigation**:
- If Lambda errors: Rollback to previous version
- If DynamoDB issues: Check throttling and capacity
- If external API issues: Enable circuit breaker or fallback

#### High Latency
**Alert**: `stock-analysis-api-latency-production`

**Immediate Actions**:
1. Check Lambda duration metrics
2. Review DynamoDB performance metrics
3. Verify cache hit rates
4. Check external API response times

**Investigation Steps**:
```bash
# Check Lambda performance
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=stock-analysis-api-production \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average,Maximum

# Check DynamoDB latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions Name=TableName,Value=stock-analyses-production \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Average
```

**Mitigation**:
- Scale Lambda memory if CPU-bound
- Check DynamoDB hot partitions
- Verify cache configuration
- Enable API Gateway caching if not already active

#### Request Throttling
**Alert**: `stock-analysis-api-throttle-production`

**Immediate Actions**:
1. Check current request rates
2. Review usage plan limits
3. Identify source of high traffic
4. Assess if traffic is legitimate

**Investigation Steps**:
```bash
# Check request patterns
aws logs filter-log-events \
  --log-group-name API-Gateway-Execution-Logs_$(aws apigateway get-rest-apis --query 'items[?name==`Stock Analysis API - production`].id' --output text)/production \
  --start-time $(date -d '30 minutes ago' +%s)000 \
  --filter-pattern "[timestamp, requestId, ip, user, timestamp, method, resource, protocol, status, error, responseLength, requestTime]"
```

**Mitigation**:
- Temporarily increase throttling limits if legitimate traffic
- Block suspicious IP addresses
- Implement additional rate limiting at application level
- Contact AWS support for DDoS protection if needed

### Lambda Function Alerts

#### High Error Rate
**Alert**: `stock-analysis-lambda-error-rate-production`

**Immediate Actions**:
1. Check error logs for patterns
2. Verify environment variables and secrets
3. Check external service dependencies
4. Review recent code changes

**Investigation Steps**:
```bash
# Get detailed error information
aws logs filter-log-events \
  --log-group-name /aws/lambda/stock-analysis-api-production \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "{ $.level = \"ERROR\" }"

# Check function configuration
aws lambda get-function-configuration \
  --function-name stock-analysis-api-production
```

**Mitigation**:
- Rollback to previous working version
- Fix configuration issues
- Implement circuit breakers for external services
- Scale function resources if needed

#### Function Throttling
**Alert**: `stock-analysis-lambda-throttle-production`

**Immediate Actions**:
1. Check concurrent execution metrics
2. Review account-level Lambda limits
3. Assess if throttling is expected
4. Check for infinite loops or long-running processes

**Investigation Steps**:
```bash
# Check concurrent executions
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=stock-analysis-api-production \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Maximum

# Check account limits
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-B99A9384
```

**Mitigation**:
- Request limit increase from AWS
- Optimize function performance
- Implement queuing for batch operations
- Split large functions into smaller ones

### DynamoDB Alerts

#### Request Throttling
**Alert**: `stock-analysis-dynamo-throttle-production`

**Immediate Actions**:
1. Check consumed vs provisioned capacity
2. Review access patterns for hot partitions
3. Verify GSI usage
4. Check for large item operations

**Investigation Steps**:
```bash
# Check table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=stock-analyses-production \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum

# Check for hot partitions
aws dynamodb describe-table \
  --table-name stock-analyses-production \
  --query 'Table.TableStatus'
```

**Mitigation**:
- Switch to on-demand billing temporarily
- Implement exponential backoff in application
- Optimize partition key distribution
- Use batch operations where possible

#### System Errors
**Alert**: `stock-analysis-dynamo-errors-production`

**Immediate Actions**:
1. Check AWS service health dashboard
2. Review DynamoDB service limits
3. Verify table configuration
4. Check for corrupted requests

**Investigation Steps**:
```bash
# Check service health
curl -s https://status.aws.amazon.com/ | grep -i dynamodb

# Review recent table operations
aws dynamodb describe-table \
  --table-name stock-analyses-production
```

**Mitigation**:
- Contact AWS support immediately
- Implement fallback to backup data source
- Enable point-in-time recovery if not already active

### Business Logic Alerts

#### High Analysis Failure Rate
**Alert**: `stock-analysis-failure-rate-production`

**Immediate Actions**:
1. Check external data source availability
2. Review input data quality
3. Verify AI/ML service health
4. Check for configuration changes

**Investigation Steps**:
```bash
# Check custom metrics
aws cloudwatch get-metric-statistics \
  --namespace StockAnalysis/Business \
  --metric-name AnalysisFailures \
  --start-time $(date -d '2 hours ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 600 \
  --statistics Sum

# Review application logs for business logic errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/stock-analysis-api-production \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "{ $.event_type = \"analysis_failure\" }"
```

**Mitigation**:
- Disable problematic analysis features temporarily
- Switch to backup data sources
- Implement graceful degradation
- Alert data team for investigation

#### Data Quality Issues
**Alert**: `stock-analysis-data-quality-production`

**Immediate Actions**:
1. Check data source health
2. Review data validation rules
3. Verify data transformation logic
4. Check for upstream system changes

**Investigation Steps**:
```bash
# Check data quality metrics
aws cloudwatch get-metric-statistics \
  --namespace StockAnalysis/DataQuality \
  --metric-name LowQualityDataPercentage \
  --start-time $(date -d '4 hours ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 900 \
  --statistics Average
```

**Mitigation**:
- Implement stricter data validation
- Use cached/historical data as fallback
- Contact data providers about quality issues
- Enable manual data review process

## System Health Monitoring

### Overall System Health
**Alert**: `stock-analysis-system-health-production`

This composite alarm indicates multiple system components are experiencing issues.

**Immediate Actions**:
1. Check all individual component alarms
2. Assess overall system availability
3. Determine if this is a cascading failure
4. Implement emergency procedures if needed

**Emergency Procedures**:
1. **Maintenance Mode**: Enable maintenance page
2. **Service Degradation**: Disable non-critical features
3. **Complete Outage**: Activate disaster recovery procedures

## Communication Procedures

### Internal Communication

#### Slack Notifications
- **Channel**: `#stock-analysis-alerts`
- **Critical Alerts**: Automatic notifications via webhook
- **Status Updates**: Manual updates every 30 minutes during incidents

#### Email Notifications
- **Recipients**: On-call engineers, engineering manager
- **Frequency**: Immediate for critical, digest for general alerts

### External Communication

#### Status Page Updates
- **URL**: `https://status.stockanalysis.com`
- **Update Frequency**: Every 15 minutes during outages
- **Responsibility**: Engineering manager or designated communications lead

#### Customer Notifications
- **Threshold**: Service degradation > 15 minutes
- **Method**: Email, in-app notifications
- **Approval**: Engineering manager required

## Escalation Procedures

### Level 1: On-Call Engineer
- **Trigger**: Any alert
- **Response Time**: 15 minutes (critical), 1 hour (general)
- **Actions**: Initial assessment, basic mitigation

### Level 2: Senior Engineer + Manager
- **Trigger**: Incident not resolved in 30 minutes (critical) or 2 hours (general)
- **Response Time**: 30 minutes
- **Actions**: Deep investigation, coordination with AWS support

### Level 3: Engineering Leadership
- **Trigger**: Major outage > 1 hour or security incident
- **Response Time**: 1 hour
- **Actions**: Executive communication, resource allocation, vendor escalation

### Level 4: Executive Team
- **Trigger**: Business-critical outage > 2 hours
- **Response Time**: 2 hours
- **Actions**: Customer communication, business continuity decisions

## Recovery Procedures

### Service Restoration Checklist

1. **Identify Root Cause**
   - [ ] Review all monitoring data
   - [ ] Analyze logs and traces
   - [ ] Document findings

2. **Implement Fix**
   - [ ] Apply immediate mitigation
   - [ ] Test fix in staging environment
   - [ ] Deploy to production with monitoring

3. **Verify Resolution**
   - [ ] Confirm all alarms are cleared
   - [ ] Test critical user journeys
   - [ ] Monitor for 30 minutes post-resolution

4. **Communication**
   - [ ] Update status page
   - [ ] Notify stakeholders
   - [ ] Send all-clear notification

### Rollback Procedures

#### Lambda Function Rollback
```bash
# List function versions
aws lambda list-versions-by-function \
  --function-name stock-analysis-api-production

# Rollback to previous version
aws lambda update-alias \
  --function-name stock-analysis-api-production \
  --name LIVE \
  --function-version $PREVIOUS_VERSION
```

#### Infrastructure Rollback
```bash
# Rollback CDK stack
cd infrastructure
cdk deploy --rollback
```

## Post-Incident Procedures

### Immediate Actions (Within 24 hours)
1. **Incident Summary**
   - Timeline of events
   - Impact assessment
   - Root cause analysis
   - Resolution steps taken

2. **Communication**
   - Internal incident report
   - Customer communication (if applicable)
   - Stakeholder briefing

### Follow-up Actions (Within 1 week)
1. **Post-Incident Review**
   - Schedule blameless post-mortem
   - Identify improvement opportunities
   - Create action items with owners

2. **Process Improvements**
   - Update monitoring and alerting
   - Improve documentation
   - Enhance automation

3. **Training**
   - Share learnings with team
   - Update runbooks
   - Conduct incident response drills

## Contact Information

### On-Call Rotation
- **Primary**: Check PagerDuty schedule
- **Secondary**: Check PagerDuty schedule
- **Manager**: [Engineering Manager Contact]

### Vendor Support
- **AWS Support**: Case priority based on severity
- **Third-party APIs**: Check vendor status pages first

### Emergency Contacts
- **Security Team**: [Security Contact]
- **Legal Team**: [Legal Contact] (for data breaches)
- **Executive Team**: [Executive Contacts]

## Tools and Resources

### Monitoring Tools
- **CloudWatch Dashboard**: [Dashboard URL from CDK output]
- **X-Ray Tracing**: AWS X-Ray console
- **Log Analysis**: CloudWatch Logs Insights

### Communication Tools
- **Slack**: `#stock-analysis-alerts` channel
- **PagerDuty**: Incident management
- **Status Page**: Customer communication

### Documentation
- **Architecture Diagrams**: `infrastructure/docs/`
- **API Documentation**: Swagger/OpenAPI docs
- **Deployment Guides**: `infrastructure/PRODUCTION_DEPLOYMENT.md`

## Appendix

### Common AWS CLI Commands

#### CloudWatch Metrics
```bash
# Get metric statistics
aws cloudwatch get-metric-statistics \
  --namespace [NAMESPACE] \
  --metric-name [METRIC_NAME] \
  --dimensions Name=[DIMENSION_NAME],Value=[DIMENSION_VALUE] \
  --start-time [START_TIME] \
  --end-time [END_TIME] \
  --period [PERIOD] \
  --statistics [STATISTICS]
```

#### Lambda Management
```bash
# Get function information
aws lambda get-function --function-name [FUNCTION_NAME]

# Update function code
aws lambda update-function-code \
  --function-name [FUNCTION_NAME] \
  --zip-file fileb://[ZIP_FILE]
```

#### DynamoDB Operations
```bash
# Describe table
aws dynamodb describe-table --table-name [TABLE_NAME]

# Get item
aws dynamodb get-item \
  --table-name [TABLE_NAME] \
  --key '[KEY_JSON]'
```

### Useful Log Queries

#### Error Analysis
```
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100
```

#### Performance Analysis
```
fields @timestamp, @duration
| filter @type = "REPORT"
| stats avg(@duration), max(@duration), min(@duration) by bin(5m)
```

#### Request Tracing
```
fields @timestamp, @requestId, @message
| filter @requestId = "[REQUEST_ID]"
| sort @timestamp asc
```

---

**Document Version**: 1.0  
**Last Updated**: [Current Date]  
**Next Review**: [Date + 3 months]  
**Owner**: Engineering Team