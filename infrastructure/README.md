# Stock Analysis Infrastructure

Modern AWS CDK infrastructure for the Stock Analysis application with comprehensive monitoring, security, and scalability features.

## Architecture Overview

This infrastructure implements a serverless architecture with the following components:

- **API Gateway**: RESTful API with rate limiting and CORS
- **AWS Lambda**: Serverless compute for the FastAPI application
- **DynamoDB**: NoSQL database with GSIs for efficient querying
- **Secrets Manager**: Secure storage for sensitive configuration
- **CloudWatch**: Monitoring, logging, and alerting
- **X-Ray**: Distributed tracing for performance monitoring

## Features

### 🔒 Security
- AWS Secrets Manager integration for sensitive data
- IAM roles with least privilege access
- API Gateway rate limiting and throttling
- HTTPS/TLS enforcement
- Security headers middleware

### 📊 Monitoring & Observability
- CloudWatch dashboards with key metrics
- Custom alarms for error rates and performance
- X-Ray tracing for request flow analysis
- Structured logging with correlation IDs
- Performance SLA monitoring

### 🚀 Scalability & Performance
- Serverless auto-scaling with Lambda
- DynamoDB on-demand billing
- API Gateway caching (configurable)
- Optimized Lambda packaging
- Environment-specific resource sizing

### 🏗️ Infrastructure as Code
- AWS CDK with TypeScript
- Environment-specific deployments
- Automated resource tagging
- Stack outputs for integration
- Rollback capabilities

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Node.js** (v18 or later)
3. **AWS CDK** installed globally: `npm install -g aws-cdk`
4. **Python 3.11** for Lambda runtime compatibility

## Quick Start

### 1. Install Dependencies

```bash
cd infrastructure
npm install
```

### 2. Bootstrap CDK (First Time Only)

```bash
cdk bootstrap
```

### 3. Deploy to Development

```bash
# Using PowerShell script (recommended)
.\deploy-infrastructure.ps1 -Environment development

# Or using CDK directly
npm run deploy:dev
```

### 4. Deploy to Production

```bash
# With domain name
.\deploy-infrastructure.ps1 -Environment production -DomainName "api.yourdomain.com"

# Or using CDK
cdk deploy --context environment=production --context domainName="api.yourdomain.com"
```

## Environment Configuration

### Development
- Minimal resources for cost optimization
- Debug logging enabled
- Relaxed CORS policies
- Lower rate limits

### Staging
- Production-like configuration
- Moderate resource allocation
- Testing-friendly settings

### Production
- High availability and performance
- Comprehensive monitoring and alerting
- Strict security policies
- Auto-scaling enabled

## Deployment Commands

### PowerShell Script (Recommended)

```powershell
# Deploy to development
.\deploy-infrastructure.ps1 -Environment development

# Deploy to staging
.\deploy-infrastructure.ps1 -Environment staging

# Deploy to production with domain
.\deploy-infrastructure.ps1 -Environment production -DomainName "api.example.com"

# Dry run (show changes without deploying)
.\deploy-infrastructure.ps1 -Environment production -DryRun

# Destroy infrastructure
.\deploy-infrastructure.ps1 -Environment development -Destroy
```

### CDK Commands

```bash
# Show differences
npm run diff

# Deploy specific environment
npm run deploy:dev
npm run deploy:staging
npm run deploy:prod

# Synthesize CloudFormation template
npm run synth

# Destroy stack
npm run destroy
```

## Backend Packaging

Before deploying, package the backend application:

```powershell
cd ../backend
.\package-lambda.ps1 -Clean
```

This creates a `dist/` directory with the Lambda-ready package.

## Monitoring & Observability

### CloudWatch Dashboard

Access the monitoring dashboard via the output URL after deployment:
- API Gateway metrics (requests, latency, errors)
- Lambda function metrics (invocations, duration, errors)
- DynamoDB metrics (read/write capacity, throttling)

### Alarms (Production Only)

- **API Error Rate**: Triggers when server errors exceed threshold
- **Lambda Error Rate**: Monitors function execution failures
- **Lambda Duration**: Alerts on performance degradation

### X-Ray Tracing

All requests are traced through X-Ray for:
- Request flow visualization
- Performance bottleneck identification
- Error root cause analysis

## Security Features

### Secrets Management

Sensitive configuration is stored in AWS Secrets Manager:
- JWT secrets
- Encryption keys
- External API keys
- Database credentials

### IAM Permissions

Lambda functions have minimal required permissions:
- DynamoDB read/write access to specific table
- Secrets Manager read access to specific secrets
- CloudWatch metrics and logs write access
- X-Ray trace write access

### Rate Limiting

API Gateway enforces rate limits:
- **Development**: 100 requests/second, 200 burst
- **Production**: 1000 requests/second, 2000 burst
- Daily quotas: 10K (dev) / 100K (prod)

## Cost Optimization

### Development Environment
- Smaller Lambda memory allocation (512 MB)
- Shorter log retention (1 week)
- No point-in-time recovery for DynamoDB
- Destroy policy for non-critical resources

### Production Environment
- Optimized Lambda memory (1024 MB)
- Extended log retention (1 month)
- Point-in-time recovery enabled
- Retain policy for data resources

## Troubleshooting

### Common Issues

1. **Bootstrap Required**
   ```bash
   cdk bootstrap
   ```

2. **Insufficient Permissions**
   - Ensure AWS credentials have CDK deployment permissions
   - Check IAM policies for CloudFormation, Lambda, DynamoDB access

3. **Package Too Large**
   - Use Lambda Layers for large dependencies
   - Optimize package contents in `package-lambda.ps1`

4. **Region Mismatch**
   - Set `AWS_DEFAULT_REGION` environment variable
   - Update CDK context in `cdk.json`

### Logs and Debugging

```bash
# View CloudFormation events
aws cloudformation describe-stack-events --stack-name StockAnalysisInfrastructureStack-development

# View Lambda logs
aws logs tail /aws/lambda/stock-analysis-api-development --follow

# Check API Gateway logs
aws logs tail API-Gateway-Execution-Logs_<api-id>/development --follow
```

## Stack Outputs

After deployment, the following outputs are available:

- **ApiUrl**: Base URL for the API Gateway
- **TableName**: DynamoDB table name for application configuration
- **SecretsArn**: ARN of the Secrets Manager secret
- **DashboardUrl**: Direct link to CloudWatch dashboard

## Contributing

1. Make infrastructure changes in TypeScript
2. Test with development environment first
3. Use `cdk diff` to review changes
4. Deploy to staging for validation
5. Deploy to production with approval

## Support

For infrastructure issues:
1. Check CloudWatch logs and metrics
2. Review CloudFormation stack events
3. Validate AWS permissions and quotas
4. Consult AWS CDK documentation