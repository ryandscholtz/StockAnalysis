# Deployment Guide

This document provides comprehensive guidance for deploying the Stock Analysis Application across different environments.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environments](#environments)
- [Deployment Strategies](#deployment-strategies)
- [CI/CD Pipeline](#cicd-pipeline)
- [Manual Deployment](#manual-deployment)
- [Rollback Procedures](#rollback-procedures)
- [Monitoring and Alerting](#monitoring-and-alerting)
- [Troubleshooting](#troubleshooting)

## Overview

The Stock Analysis Application uses a modern CI/CD pipeline with automated testing, security scanning, and deployment automation. The system supports multiple environments with different deployment strategies optimized for each use case.

### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Development   │    │     Staging     │    │   Production    │
│                 │    │                 │    │                 │
│ • Local testing │    │ • Integration   │    │ • Live system   │
│ • Feature dev   │    │ • UAT           │    │ • Blue/Green    │
│ • SQLite DB     │    │ • DynamoDB      │    │ • DynamoDB      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Prerequisites

### Required Tools

- **AWS CLI** (v2.0+)
- **AWS CDK** (v2.100+)
- **Node.js** (v18+)
- **Python** (v3.11+)
- **Docker** (for local testing)
- **Git** (for version control)

### AWS Permissions

Ensure your AWS credentials have the following permissions:
- CloudFormation full access
- Lambda full access
- API Gateway full access
- DynamoDB full access
- S3 full access
- CloudWatch full access
- IAM role creation

### Environment Variables

Set the following environment variables:

```bash
# AWS Configuration
export AWS_REGION=us-east-1
export AWS_PROFILE=your-profile

# Application Configuration
export ENVIRONMENT=staging|production
export STACK_NAME=StockAnalysisStack-{environment}
```

## Environments

### Staging Environment

- **Purpose**: Integration testing and UAT
- **URL**: https://staging-api.stockanalysis.com
- **Database**: DynamoDB (staging)
- **Deployment**: Automatic on `develop` branch
- **Monitoring**: Basic monitoring enabled

### Production Environment

- **Purpose**: Live production system
- **URL**: https://api.stockanalysis.com
- **Database**: DynamoDB (production)
- **Deployment**: Manual approval required
- **Monitoring**: Full monitoring and alerting

## Deployment Strategies

### Staging: Rolling Deployment

- Updates instances gradually
- Allows for quick rollback
- Minimal downtime
- Suitable for testing environments

### Production: Blue-Green Deployment

- Zero-downtime deployments
- Full environment switch
- Easy rollback capability
- Production-grade reliability

## CI/CD Pipeline

### Automated Workflows

1. **Pull Request Checks** (`.github/workflows/pr-checks.yml`)
   - Code quality validation
   - Quick tests
   - Security scanning
   - Bundle size analysis

2. **Main CI/CD Pipeline** (`.github/workflows/ci.yml`)
   - Comprehensive testing
   - Security scanning
   - Docker builds
   - Automated deployments

3. **Deployment Pipeline** (`.github/workflows/deploy.yml`)
   - Environment-specific deployments
   - Health checks
   - Rollback on failure
   - Notifications

4. **Hotfix Pipeline** (`.github/workflows/hotfix.yml`)
   - Emergency deployments
   - Minimal testing (if needed)
   - Immediate notifications

### Deployment Triggers

| Branch | Environment | Trigger | Approval |
|--------|-------------|---------|----------|
| `develop` | Staging | Automatic | None |
| `main` | Production | Automatic | Manual |
| `hotfix/*` | Production | Manual | Required |

## Manual Deployment

### Using Scripts

#### Staging Deployment

```bash
# Linux/macOS
./scripts/deploy-staging.sh

# Windows
.\scripts\deploy-staging.ps1
```

#### Production Deployment

```bash
# Linux/macOS
./scripts/deploy-production.sh

# Windows
.\scripts\deploy-production.ps1
```

### Using CDK Directly

```bash
# Navigate to infrastructure directory
cd infrastructure

# Install dependencies
npm ci

# Build CDK
npm run build

# Deploy to staging
npm run deploy:staging

# Deploy to production (requires approval)
npm run deploy:prod
```

### Manual Steps

1. **Pre-deployment Checks**
   ```bash
   # Run tests
   cd backend && python -m pytest
   cd ../frontend && npm test
   
   # Security scan
   cd ../backend && bandit -r app/
   ```

2. **Deploy Infrastructure**
   ```bash
   cd infrastructure
   cdk deploy --context environment=staging
   ```

3. **Deploy Application**
   ```bash
   # Backend deployment
   # (Handled by CDK Lambda deployment)
   
   # Frontend deployment
   cd frontend
   npm run build
   # Upload to S3/CloudFront
   ```

4. **Post-deployment Validation**
   ```bash
   # Health check
   curl https://staging-api.stockanalysis.com/health
   
   # API documentation
   curl https://staging-api.stockanalysis.com/docs
   ```

## Rollback Procedures

### Automatic Rollback

The system automatically rolls back if:
- Health checks fail
- Error rate exceeds threshold
- Performance degrades significantly

### Manual Rollback

```bash
# Using rollback script
./scripts/rollback.sh production

# Using CDK (manual process)
cd infrastructure
cdk deploy --context environment=production --context version=previous
```

### Rollback Steps

1. **Stop Traffic**
   - Update load balancer
   - Set maintenance mode

2. **Restore Infrastructure**
   - Deploy previous CDK version
   - Restore configuration

3. **Restore Database**
   - Use DynamoDB backup
   - Point-in-time recovery

4. **Validate Rollback**
   - Health checks
   - Smoke tests
   - Performance validation

5. **Resume Traffic**
   - Update load balancer
   - Monitor closely

## Monitoring and Alerting

### Key Metrics

- **Application Health**
  - Response time (P95 < 200ms)
  - Error rate (< 0.1%)
  - Availability (> 99.9%)

- **Infrastructure Health**
  - CPU utilization
  - Memory usage
  - Database connections

- **Business Metrics**
  - Analysis requests
  - User activity
  - Feature usage

### Dashboards

- **Operational Dashboard**: System health and performance
- **Business Dashboard**: Usage metrics and trends
- **Security Dashboard**: Security events and compliance

### Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| Application Down | 0% availability | Immediate escalation |
| High Error Rate | > 1% errors | Team notification |
| Slow Response | P95 > 500ms | Investigation required |
| Database Issues | Connection failures | Database team alert |

## Troubleshooting

### Common Issues

#### Deployment Failures

**CDK Bootstrap Issues**
```bash
# Re-bootstrap the environment
cdk bootstrap --context environment=staging
```

**Permission Errors**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM permissions
aws iam get-user
```

**Resource Conflicts**
```bash
# Check existing resources
aws cloudformation describe-stacks --stack-name StockAnalysisStack-staging

# Force update if needed
cdk deploy --force
```

#### Application Issues

**Health Check Failures**
1. Check application logs in CloudWatch
2. Verify database connectivity
3. Check environment variables
4. Validate API endpoints

**Performance Issues**
1. Monitor CloudWatch metrics
2. Check database query performance
3. Verify cache hit rates
4. Review application logs

**Security Issues**
1. Check WAF logs
2. Review access patterns
3. Validate SSL certificates
4. Monitor security events

### Debug Commands

```bash
# Check deployment status
aws cloudformation describe-stacks --stack-name StockAnalysisStack-staging

# View application logs
aws logs tail /aws/lambda/stock-analysis-api --follow

# Check database status
aws dynamodb describe-table --table-name stock-analyses-staging

# Monitor metrics
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Duration
```

### Support Contacts

- **DevOps Team**: devops@stockanalysis.com
- **Development Team**: dev@stockanalysis.com
- **On-call Engineer**: +1-555-0123 (emergencies only)

## Best Practices

### Development

1. **Feature Branches**: Use feature branches for development
2. **Pull Requests**: All changes must go through PR review
3. **Testing**: Write tests for all new features
4. **Documentation**: Update documentation with changes

### Deployment

1. **Staging First**: Always deploy to staging first
2. **Gradual Rollout**: Use feature flags for gradual rollouts
3. **Monitoring**: Monitor deployments closely
4. **Rollback Plan**: Always have a rollback plan ready

### Security

1. **Secrets Management**: Use AWS Secrets Manager
2. **Least Privilege**: Follow least privilege principle
3. **Regular Updates**: Keep dependencies updated
4. **Security Scanning**: Regular security scans

### Operations

1. **Monitoring**: Comprehensive monitoring setup
2. **Alerting**: Meaningful alerts with clear actions
3. **Documentation**: Keep runbooks updated
4. **Incident Response**: Clear incident response procedures

---

For additional support or questions, please contact the DevOps team or create an issue in the repository.