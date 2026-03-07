# Deployment Guide

## Current System Architecture

### Backend: Enhanced AWS Lambda Function
- **File**: `simple-marketstack-lambda.py`
- **Function Name**: `stock-analysis-api-production`
- **Region**: `eu-west-1`
- **Profile**: `Cerebrum`
- **Runtime**: `python3.11`

### Frontend: Next.js Application
- **Framework**: Next.js 14+
- **Deployment**: Local development, production ready
- **API Base URL**: `https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production`

## Backend Deployment

### Prerequisites
- AWS CLI configured with `Cerebrum` profile
- PowerShell (Windows) or Bash (Linux/Mac)
- Access to AWS Lambda function `stock-analysis-api-production`

### Deployment Steps

1. **Prepare Lambda Package**
```powershell
# Compress the Lambda function
Compress-Archive -Path simple-marketstack-lambda.py -DestinationPath simple-marketstack-lambda.zip -Force
```

2. **Deploy to AWS Lambda**
```powershell
# Update function code
aws lambda update-function-code --function-name stock-analysis-api-production --zip-file fileb://simple-marketstack-lambda.zip --profile Cerebrum --region eu-west-1

# Update handler (if changed)
aws lambda update-function-configuration --function-name stock-analysis-api-production --handler simple-marketstack-lambda.lambda_handler --profile Cerebrum --region eu-west-1
```

3. **Verify Deployment**
```powershell
# Check health endpoint
Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -Method GET

# Check version
Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/version" -Method GET

# Check Explore endpoints (markets list and stocks for a market)
Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/explore/markets" -Method GET
Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/explore/stocks?market=SP500" -Method GET
```

**Note:** The **Explore** page (`/explore`) requires the backend to expose `/api/explore/markets` and `/api/explore/stocks`. These routes are included in `backend/lambda_build`. If the Explore page returns 404 for those URLs, rebuild the Lambda package from `lambda_build` and redeploy.

### Deploy via container image (Docker) — when package exceeds 250 MB

If the deployment package (or layer) exceeds Lambda’s 250 MB unzipped limit, use a **container image** (up to 10 GB).

**Prerequisites**

- **Docker** installed and running (Docker Desktop on Windows: https://docs.docker.com/desktop/install/windows-install/).

**One-shot script (recommended)**

From the repo root or `backend/`:

```powershell
cd backend
.\deploy-lambda-docker-full.ps1
```

This script will:

1. Check for Docker (exit with install instructions if missing).
2. Build the image from `Dockerfile.lambda` and push it to ECR (`stock-analysis-api`).
3. Create a new Lambda **stock-analysis-api-container** (PackageType Image) with the same role, timeout, memory, and env as `stock-analysis-api-production`, or update its code if it already exists.
4. Add permission for API Gateway to invoke the new function.
5. Update all API Gateway (dx0w31lbc1) integrations to use **stock-analysis-api-container**.
6. Deploy the `production` stage and run a health check.

So the live API will use the container-based Lambda. The existing Zip-based function (`stock-analysis-api-production` or `stock-analysis-gateway`) is no longer used by the API after a successful run.

If you see `docker is not recognized`: install Docker Desktop, start it, and run the script again.

### Version Format
Backend versions follow the pattern: `4.0.0-marketstack-YYMMDD-HHMM`
- `4.0.0-marketstack`: Base version with financial ratios
- `YYMMDD-HHMM`: Deployment timestamp in GMT+2

Example: `4.0.0-marketstack-260111-1347` (deployed Jan 11, 2026 at 13:47 GMT+2)

## Frontend Deployment

### Local Development
```bash
cd frontend
npm install
npm run dev
```
Access at: `http://localhost:3000`

### Production Build
```bash
cd frontend
npm run build
npm start
```

### Environment Configuration
Ensure `.env.local` contains:
```
NEXT_PUBLIC_API_URL=https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production
```

## Testing Deployment

### Backend Tests
```bash
# Test all endpoints
node test-enhanced-financial-ratios.js

# Test specific stock
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/GOOGL

# Test analysis
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/AAPL
```

### Frontend Tests
1. Navigate to `http://localhost:3000/watchlist`
2. Click on any stock (AAPL, GOOGL, MSFT, TSLA)
3. Verify financial summary card appears at top
4. Click "Run Analysis" to test full analysis

### Expected Results
- **Financial Summary Card**: Shows P/E, P/B, ROE, Debt-to-Equity, Market Cap, Current Ratio
- **Color Coding**: Green (good), Blue (moderate), Yellow (concerning)
- **Analysis Components**: PriceRatios, GrowthMetrics, FinancialHealth after "Run Analysis"

## Rollback Procedure

### Backend Rollback
If deployment fails, revert to previous working version:

```powershell
# Revert to simple watchlist version
aws lambda update-function-code --function-name stock-analysis-api-production --zip-file fileb://simple-watchlist-enhanced.zip --profile Cerebrum --region eu-west-1

# Update handler
aws lambda update-function-configuration --function-name stock-analysis-api-production --handler simple-lambda-watchlist.lambda_handler --profile Cerebrum --region eu-west-1
```

### Frontend Rollback
Frontend changes are in version control. Use git to revert:
```bash
git checkout HEAD~1 frontend/app/watchlist/[ticker]/page.tsx
```

## Monitoring

### Health Checks
- **Backend Health**: `GET /health`
- **Version Check**: `GET /api/version`
- **Functional Test**: `GET /api/manual-data/GOOGL`

### Key Metrics to Monitor
- Response times (should be < 2 seconds)
- Error rates (should be < 1%)
- Financial data accuracy
- Frontend rendering performance

## Troubleshooting

### Common Issues

**Lambda Function Timeout**
- Check CloudWatch logs
- Increase timeout if needed (currently 900 seconds)

**Financial Data Not Showing**
- Verify API response structure
- Check frontend console for errors
- Ensure `key_metrics.latest` exists in response

**Version Mismatch**
- Check backend version: `GET /api/version`
- Check frontend version in footer
- Ensure both are using GMT+2 timestamps

### Debug Commands
```bash
# Check Lambda logs
aws logs describe-log-groups --profile Cerebrum --region eu-west-1

# Test specific endpoint
curl -v https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/AAPL

# Check CORS headers
curl -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" -X OPTIONS https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/version
```

## Security Considerations

### API Security
- CORS properly configured for frontend domains
- No sensitive data in responses
- Rate limiting handled by AWS API Gateway

### Environment Variables
- No hardcoded API keys in Lambda function
- MarketStack API key placeholder for future integration
- AWS Secrets Manager integration ready

## Future Deployment Enhancements

### Planned Improvements
1. **CI/CD Pipeline**: Automated deployment on git push
2. **Environment Separation**: Dev/staging/prod environments
3. **Real MarketStack Integration**: Live market data
4. **Monitoring Dashboard**: CloudWatch metrics and alarms
5. **Blue/Green Deployment**: Zero-downtime deployments

### Infrastructure as Code
Consider moving to:
- AWS CDK or Terraform for infrastructure
- GitHub Actions for CI/CD
- CloudFormation for AWS resources

---

*Last Updated: January 11, 2026*
*Current Backend Version: 4.0.0-marketstack-260111-1347*