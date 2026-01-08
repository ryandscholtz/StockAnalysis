# Production Deployment Guide

This guide covers the complete deployment of the Stock Analysis application to production AWS infrastructure.

## Prerequisites

### Required Tools
- AWS CLI v2 configured with appropriate credentials
- Node.js 18+ and npm
- Python 3.11+ with boto3
- AWS CDK CLI v2 (`npm install -g aws-cdk`)

### AWS Account Setup
- AWS Account: 295202642810 (Cerebrum)
- Region: eu-west-1 (Ireland)
- Required IAM permissions for CDK deployment

### Environment Variables
Set these environment variables before deployment:

```bash
export CDK_DEFAULT_ACCOUNT=295202642810
export CDK_DEFAULT_REGION=eu-west-1
export ENVIRONMENT=production

# Optional: Custom domain name
export DOMAIN_NAME=api.stockanalysis.cerebrum.com

# API Keys (will be stored in Secrets Manager)
export ALPHA_VANTAGE_API_KEY=your_key_here
export MARKETSTACK_API_KEY=your_key_here
export FRED_API_KEY=your_key_here
export FMP_API_KEY=your_key_here
```

## Deployment Steps

### Step 1: Prepare Infrastructure

1. **Navigate to infrastructure directory:**
   ```bash
   cd infrastructure
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Bootstrap CDK (first time only):**
   ```bash
   cdk bootstrap --context environment=production
   ```

### Step 2: Setup Production Secrets

1. **Run the secrets setup script:**
   ```bash
   python setup-production-secrets.py --environment production
   ```

2. **Validate secrets were created:**
   ```bash
   python setup-production-secrets.py --environment production --validate-only
   ```

### Step 3: Deploy Infrastructure

1. **Review deployment plan (dry run):**
   ```powershell
   .\deploy-production.ps1 -Environment production -DryRun
   ```

2. **Deploy to production:**
   ```powershell
   .\deploy-production.ps1 -Environment production
   ```

   Or using CDK directly:
   ```bash
   cdk deploy --context environment=production --require-approval never
   ```

### Step 4: Configure Backend Environment

1. **Update backend environment file:**
   Copy the deployment outputs to update `backend/.env.production`:
   
   ```bash
   # Update these values from CDK outputs
   DYNAMODB_TABLE_NAME=stock-analyses-production
   SECRETS_ARN=arn:aws:secretsmanager:eu-west-1:295202642810:secret:stock-analysis-secrets-production-XXXXXX
   ```

2. **Package Lambda function:**
   ```bash
   cd ../backend
   # Create deployment package (implementation needed)
   python package-lambda.py
   ```

### Step 5: Deploy Application Code

1. **Update Lambda function code:**
   ```bash
   aws lambda update-function-code \
     --function-name stock-analysis-api-production \
     --zip-file fileb://dist/lambda-package.zip \
     --region eu-west-1
   ```

2. **Update environment variables:**
   ```bash
   aws lambda update-function-configuration \
     --function-name stock-analysis-api-production \
     --environment file://lambda-env.json \
     --region eu-west-1
   ```

### Step 6: Verify Deployment

1. **Test health endpoint:**
   ```bash
   curl https://your-api-gateway-url/health
   ```

2. **Check CloudWatch logs:**
   ```bash
   aws logs tail /aws/lambda/stock-analysis-api-production --follow
   ```

3. **Verify monitoring dashboard:**
   Visit the CloudWatch dashboard URL from CDK outputs.

## Infrastructure Components

The production deployment creates:

### Core Infrastructure
- **DynamoDB Table**: `stock-analyses-production`
  - Point-in-time recovery enabled
  - Encryption at rest
  - Global secondary indexes for efficient querying

- **Lambda Function**: `stock-analysis-api-production`
  - Python 3.11 runtime
  - 1024MB memory allocation
  - 30-second timeout
  - X-Ray tracing enabled

- **API Gateway**: REST API with rate limiting
  - 1000 requests/second rate limit
  - 2000 burst limit
  - CORS configured for production domain

### Security
- **Secrets Manager**: Secure storage for sensitive configuration
- **IAM Roles**: Least privilege access for Lambda function
- **Encryption**: At rest and in transit

### Monitoring
- **CloudWatch Dashboard**: Real-time metrics and monitoring
- **CloudWatch Alarms**: Critical error and performance alerts
- **X-Ray Tracing**: Distributed tracing for performance analysis

### Networking
- **Rate Limiting**: API Gateway throttling
- **CORS**: Configured for production domain
- **HTTPS**: TLS 1.3 enforcement

## Post-Deployment Configuration

### 1. Domain Setup (Optional)
If using a custom domain:

```bash
# Create ACM certificate
aws acm request-certificate \
  --domain-name api.stockanalysis.cerebrum.com \
  --validation-method DNS \
  --region eu-west-1

# Configure API Gateway custom domain
# (Implementation depends on your domain setup)
```

### 2. Monitoring Setup

1. **Configure SNS notifications:**
   ```bash
   aws sns create-topic --name stock-analysis-alerts-production
   aws sns subscribe --topic-arn arn:aws:sns:eu-west-1:295202642810:stock-analysis-alerts-production \
     --protocol email --notification-endpoint your-email@example.com
   ```

2. **Update CloudWatch alarms to use SNS topic**

### 3. Backup Configuration

1. **Enable DynamoDB backups:**
   - Point-in-time recovery is already enabled
   - Consider setting up scheduled backups for compliance

2. **Lambda function versioning:**
   ```bash
   aws lambda publish-version --function-name stock-analysis-api-production
   ```

## Troubleshooting

### Common Issues

1. **CDK Bootstrap Issues:**
   ```bash
   # Re-bootstrap if needed
   cdk bootstrap --force --context environment=production
   ```

2. **Secrets Manager Access:**
   ```bash
   # Verify secret exists
   aws secretsmanager describe-secret --secret-id stock-analysis-secrets-production
   ```

3. **Lambda Function Issues:**
   ```bash
   # Check function logs
   aws logs describe-log-groups --log-group-name-prefix /aws/lambda/stock-analysis-api-production
   ```

### Rollback Procedure

1. **Rollback Lambda function:**
   ```bash
   aws lambda update-function-code \
     --function-name stock-analysis-api-production \
     --zip-file fileb://previous-version.zip
   ```

2. **Rollback infrastructure:**
   ```bash
   cdk deploy --context environment=production --rollback
   ```

## Security Considerations

### Access Control
- Lambda function uses least privilege IAM role
- Secrets Manager access restricted to specific secrets
- API Gateway rate limiting prevents abuse

### Data Protection
- DynamoDB encryption at rest using AWS managed keys
- Secrets Manager for sensitive configuration
- HTTPS enforcement for all communications

### Monitoring
- CloudWatch alarms for security events
- X-Ray tracing for request analysis
- Structured logging for audit trails

## Cost Optimization

### DynamoDB
- On-demand billing mode (pay per request)
- Consider provisioned capacity for predictable workloads

### Lambda
- Right-sized memory allocation (1024MB)
- Consider provisioned concurrency for consistent performance

### API Gateway
- REST API (cheaper than HTTP API for this use case)
- Caching can be enabled for frequently accessed endpoints

## Maintenance

### Regular Tasks
1. **Monitor CloudWatch dashboards weekly**
2. **Review CloudWatch alarms monthly**
3. **Update Lambda function code as needed**
4. **Rotate secrets quarterly**
5. **Review and update IAM permissions quarterly**

### Updates
1. **Infrastructure updates:** Use CDK deployment
2. **Application updates:** Update Lambda function code
3. **Configuration updates:** Update Secrets Manager values

## Support

For deployment issues:
1. Check CloudWatch logs first
2. Verify AWS credentials and permissions
3. Review CDK synthesis output for errors
4. Check AWS service limits and quotas