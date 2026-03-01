# Lambda Microservices Architecture

## Overview

The Stock Analysis API has been split into 5 specialized Lambda functions to overcome AWS Lambda's 250 MB package size limit. This microservices architecture provides better scalability, maintainability, and cost optimization.

## Architecture Diagram

```
                                    ┌─────────────────────┐
                                    │   API Gateway       │
                                    │  (HTTP API)         │
                                    └──────────┬──────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │  Gateway Lambda     │
                                    │  (Router - 5 MB)    │
                                    └──────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
         ┌──────────▼──────────┐    ┌─────────▼─────────┐    ┌──────────▼──────────┐
         │  Stock Data Lambda  │    │  Analysis Lambda  │    │  PDF Processor      │
         │  (yfinance - 80 MB) │    │  (numpy - 60 MB)  │    │  (pdfplumber-40 MB) │
         └─────────────────────┘    └───────────────────┘    └─────────────────────┘
                                               │
                                    ┌──────────▼──────────┐
                                    │  Auth/Watchlist     │
                                    │  (DynamoDB - 20 MB) │
                                    └─────────────────────┘
```

## Lambda Functions

### 1. API Gateway Lambda (Router)
- **Function Name**: `stock-analysis-gateway`
- **Size**: ~5 MB
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Dependencies**: boto3 (AWS SDK only)
- **Purpose**: Routes incoming requests to specialized Lambdas
- **Endpoints**: All `/api/*` routes

**Routes:**
- `/api/ticker/*` → Stock Data Lambda
- `/api/search` → Stock Data Lambda
- `/api/pdf/*` → PDF Processing Lambda
- `/api/analysis/*` → Analysis Lambda
- `/api/watchlist/*` → Auth/Watchlist Lambda
- `/api/manual-data/*` → Auth/Watchlist Lambda
- `/health`, `/` → Health check (handled locally)

### 2. Stock Data Lambda
- **Function Name**: `stock-analysis-stock-data`
- **Size**: ~80 MB
- **Memory**: 512 MB
- **Timeout**: 30 seconds
- **Dependencies**: yfinance, pandas, numpy, requests
- **Purpose**: Fetch stock prices and market data

**Endpoints:**
- `GET /api/ticker/{ticker}` - Get stock information
- `GET /api/search?q={query}` - Search for stocks

**Data Sources:**
- Yahoo Finance (via yfinance)
- MarketStack API (for company names)

### 3. PDF Processing Lambda
- **Function Name**: `stock-analysis-pdf-processor`
- **Size**: ~40 MB
- **Memory**: 1024 MB
- **Timeout**: 60 seconds
- **Dependencies**: PyPDF2, pdfplumber, Pillow, boto3
- **Purpose**: Upload and extract text from PDF financial statements

**Endpoints:**
- `POST /api/pdf/upload` - Upload PDF and extract text
- `POST /api/pdf/extract` - Extract text from PDF

**Storage:**
- Uploads PDFs to S3 bucket: `stock-analysis-pdfs`
- Returns extracted text for analysis

### 4. Analysis Lambda
- **Function Name**: `stock-analysis-analyzer`
- **Size**: ~60 MB
- **Memory**: 512 MB
- **Timeout**: 60 seconds
- **Dependencies**: numpy, pandas, boto3
- **Purpose**: Perform stock valuation and analysis calculations

**Endpoints:**
- `POST /api/analysis/{ticker}` - Analyze stock with DCF/P/E models
- `GET /api/analysis-presets` - Get available analysis presets

**Analysis Methods:**
- DCF (Discounted Cash Flow)
- P/E (Price-to-Earnings) valuation
- Financial ratios

### 5. Auth & Watchlist Lambda
- **Function Name**: `stock-analysis-auth`
- **Size**: ~20 MB
- **Memory**: 256 MB
- **Timeout**: 15 seconds
- **Dependencies**: boto3 (minimal)
- **Purpose**: Handle authentication and watchlist CRUD operations

**Endpoints:**
- `GET /api/watchlist` - Get user's watchlist
- `GET /api/watchlist/{ticker}` - Get specific watchlist item
- `POST /api/watchlist` - Add to watchlist
- `DELETE /api/watchlist/{ticker}` - Remove from watchlist
- `GET /api/manual-data/{ticker}` - Get manual financial data
- `POST /api/manual-data/{ticker}` - Save manual financial data

**Storage:**
- DynamoDB table: `stock-analysis-watchlist`
- DynamoDB table: `stock-analysis-manual-data`

## Deployment

### Prerequisites
- AWS CLI configured with profile "Cerebrum"
- Python 3.11 installed
- PowerShell (Windows) or Bash (Linux/Mac)

### Deploy All Microservices

```powershell
cd backend
./deploy-microservices.ps1
```

This script will:
1. Create deployment packages for each Lambda
2. Upload packages to S3
3. Deploy/update all 5 Lambda functions
4. Configure environment variables
5. Update API Gateway integration
6. Test the health endpoint

### Manual Deployment

Deploy individual Lambdas:

```powershell
# Deploy Gateway Lambda
pip install -r requirements-gateway.txt -t lambda_build_gateway
Copy-Item api_gateway_lambda.py lambda_build_gateway/lambda_function.py
Compress-Archive -Path lambda_build_gateway/* -DestinationPath lambda-gateway.zip
aws lambda update-function-code --function-name stock-analysis-gateway --zip-file fileb://lambda-gateway.zip --profile Cerebrum --region eu-west-1

# Deploy Stock Data Lambda
pip install -r requirements-stock-data.txt -t lambda_build_stock
Copy-Item lambda_stock_data.py lambda_build_stock/lambda_function.py
Compress-Archive -Path lambda_build_stock/* -DestinationPath lambda-stock-data.zip
aws lambda update-function-code --function-name stock-analysis-stock-data --zip-file fileb://lambda-stock-data.zip --profile Cerebrum --region eu-west-1

# Repeat for other Lambdas...
```

## Environment Variables

### Gateway Lambda
- `STOCK_DATA_LAMBDA`: stock-analysis-stock-data
- `PDF_LAMBDA`: stock-analysis-pdf-processor
- `ANALYSIS_LAMBDA`: stock-analysis-analyzer
- `AUTH_LAMBDA`: stock-analysis-auth
- `MARKETSTACK_API_KEY`: b435b1cd06228185916b7b7afd790dc6
- `CORS_ALLOW_ALL`: true

### Stock Data Lambda
- `MARKETSTACK_API_KEY`: b435b1cd06228185916b7b7afd790dc6

### PDF Processing Lambda
- `PDF_BUCKET`: stock-analysis-pdfs

### Auth/Watchlist Lambda
- `WATCHLIST_TABLE`: stock-analysis-watchlist
- `MANUAL_DATA_TABLE`: stock-analysis-manual-data

## IAM Permissions

Each Lambda needs:
- **Basic Execution**: `AWSLambdaBasicExecutionRole`
- **Lambda Invocation**: `lambda:InvokeFunction` (Gateway Lambda only)
- **DynamoDB**: `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Query`, `dynamodb:DeleteItem` (Auth Lambda)
- **S3**: `s3:PutObject`, `s3:GetObject` (PDF Lambda)

## Benefits

### Size Optimization
- **Before**: 250+ MB (exceeded limit)
- **After**: 
  - Gateway: 5 MB
  - Auth: 20 MB
  - PDF: 40 MB
  - Analysis: 60 MB
  - Stock Data: 80 MB
- **Total**: 205 MB (distributed across 5 functions)

### Performance
- Faster cold starts (smaller packages)
- Parallel execution (multiple Lambdas can run simultaneously)
- Optimized memory allocation per function

### Cost Optimization
- Pay only for what you use
- Different memory/timeout settings per function
- Auth Lambda (256 MB) costs less than PDF Lambda (1024 MB)

### Scalability
- Each Lambda scales independently
- High traffic on stock data doesn't affect PDF processing
- Better resource utilization

### Maintainability
- Clear separation of concerns
- Easier to update individual services
- Simpler testing and debugging

## Monitoring

### CloudWatch Logs
Each Lambda has its own log group:
- `/aws/lambda/stock-analysis-gateway`
- `/aws/lambda/stock-analysis-stock-data`
- `/aws/lambda/stock-analysis-pdf-processor`
- `/aws/lambda/stock-analysis-analyzer`
- `/aws/lambda/stock-analysis-auth`

### Metrics
Monitor:
- Invocation count per Lambda
- Error rates
- Duration
- Concurrent executions
- Throttles

### Testing

```bash
# Test health endpoint
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health

# Test stock data
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/ticker/AAPL

# Test analysis presets
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analysis-presets

# Test watchlist
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist
```

## Troubleshooting

### Lambda Invocation Errors
- Check IAM permissions for Lambda-to-Lambda invocation
- Verify function names in environment variables
- Check CloudWatch logs for detailed errors

### CORS Issues
- All Lambdas return CORS headers
- Gateway Lambda handles OPTIONS preflight
- Verify `Access-Control-Allow-Origin: *` in responses

### Timeout Issues
- Increase timeout for specific Lambda
- Check if downstream services (yfinance, MarketStack) are slow
- Consider caching frequently accessed data

### Package Size Issues
- Keep dependencies minimal per Lambda
- Use `--only-binary=:all:` for pip installs
- Exclude unnecessary files from packages

## Future Enhancements

1. **Caching Layer**: Add Redis/ElastiCache for frequently accessed data
2. **API Gateway Caching**: Enable caching at API Gateway level
3. **Lambda Layers**: Share common dependencies across Lambdas
4. **Step Functions**: Orchestrate complex multi-Lambda workflows
5. **EventBridge**: Async processing for long-running tasks
6. **Container Images**: Use Docker for even larger dependencies

## API Endpoint

**Production**: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review this documentation
3. Test individual Lambdas directly
4. Verify IAM permissions and environment variables
