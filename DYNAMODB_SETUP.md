# DynamoDB Setup Guide

Complete guide to migrate from SQLite to DynamoDB.

## Step 1: Deploy DynamoDB Table

### 1.1 Install CDK Dependencies

```bash
cd infrastructure
npm install
```

### 1.2 Bootstrap CDK (First Time Only)

```bash
# Using default AWS credentials
cdk bootstrap

# Or using a specific profile
cdk bootstrap --profile Cerebrum
# or
cdk bootstrap --profile Personal
```

### 1.3 Deploy the Stack

```bash
# Deploy to default account/region
cdk deploy

# Or with specific profile
cdk deploy --profile Cerebrum

# Or to specific region
cdk deploy --context region=eu-west-1
```

### 1.4 Verify Deployment

```bash
aws dynamodb describe-table --table-name stock-analyses
```

You should see the table with 3 Global Secondary Indexes (GSIs).

## Step 2: Configure Backend

### 2.1 Set Environment Variables

Create or update `.env` file in `backend/`:

```bash
# Use DynamoDB instead of SQLite
USE_DYNAMODB=true

# DynamoDB configuration
DYNAMODB_TABLE_NAME=stock-analyses
DYNAMODB_REGION=us-east-1

# AWS Profile (optional, if not using default)
AWS_PROFILE=Cerebrum
```

### 2.2 Install Python Dependencies

```bash
cd backend
pip install boto3
# Or if using requirements.txt
pip install -r requirements.txt
```

### 2.3 Verify AWS Credentials

```bash
aws sts get-caller-identity
# Should show your AWS account and user
```

## Step 3: Test DynamoDB Connection

### 3.1 Test Script

Create `backend/test_dynamodb.py`:

```python
from app.database.dynamodb_service import DynamoDBService

# Initialize DynamoDB service
db = DynamoDBService(table_name="stock-analyses")

# Test save
test_data = {
    'ticker': 'TEST',
    'currentPrice': 100.0,
    'fairValue': 120.0,
    'recommendation': 'BUY',
    'marginOfSafety': {'percentage': 20.0}
}

success = db.save_analysis(
    ticker='TEST',
    analysis_data=test_data,
    exchange='TEST',
    analysis_date='2024-12-23'
)

print(f"Save successful: {success}")

# Test read
analysis = db.get_analysis('TEST', '2024-12-23')
print(f"Retrieved: {analysis is not None}")
```

Run:
```bash
python test_dynamodb.py
```

## Step 4: Migrate Existing Data (Optional)

If you have existing SQLite data:

```bash
cd backend
python scripts/migrate_sqlite_to_dynamodb.py
```

Or migrate specific date range:
```bash
python scripts/migrate_sqlite_to_dynamodb.py --start-date 2024-12-01 --end-date 2024-12-23
```

## Step 5: Run Batch Analysis

Now batch analysis will automatically use DynamoDB:

```bash
python batch_analyze_exchange.py JSE jse_tickers.txt
```

You should see:
```
Using DynamoDB: stock-analyses in us-east-1
```

## Step 6: Verify Data in DynamoDB

### Using AWS CLI

```bash
# Get a specific analysis
aws dynamodb get-item \
  --table-name stock-analyses \
  --key '{"PK":{"S":"TICKER#AAPL"},"SK":{"S":"DATE#2024-12-23"}}'

# Query by exchange (using GSI1)
aws dynamodb query \
  --table-name stock-analyses \
  --index-name GSI1-ExchangeDate \
  --key-condition-expression "GSI1PK = :ex AND GSI1SK = :date" \
  --expression-attribute-values '{":ex":{"S":"EXCHANGE#JSE"},":date":{"S":"DATE#2024-12-23"}}'
```

### Using Python

```python
from app.database.dynamodb_service import DynamoDBService

db = DynamoDBService()

# Get analysis
analysis = db.get_analysis('AAPL', '2024-12-23')

# Get all JSE analyses for today
jse_analyses = db.get_exchange_analyses('JSE')
print(f"Found {len(jse_analyses)} JSE analyses")
```

## Troubleshooting

### "Table not found"
- Verify table exists: `aws dynamodb describe-table --table-name stock-analyses`
- Check table name matches: `DYNAMODB_TABLE_NAME=stock-analyses`

### "Access Denied"
- Check AWS credentials: `aws sts get-caller-identity`
- Verify IAM permissions for DynamoDB
- Check AWS profile: `export AWS_PROFILE=Cerebrum`

### "Region mismatch"
- Verify region: `aws configure get region`
- Set in `.env`: `DYNAMODB_REGION=us-east-1`

### "Still using SQLite"
- Check `.env` file has `USE_DYNAMODB=true`
- Restart Python process (env vars loaded at startup)
- Check console output for "Using DynamoDB" message

## Cost Monitoring

Monitor DynamoDB costs:

```bash
# View table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=stock-analyses \
  --start-time 2024-12-23T00:00:00Z \
  --end-time 2024-12-24T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

## Rollback to SQLite

If you need to switch back:

1. Remove or comment out in `.env`:
   ```bash
   # USE_DYNAMODB=true
   ```

2. Restart batch analysis

Data in DynamoDB will remain (table has RETAIN policy).

## Next Steps

- Set up CloudWatch alarms for costs
- Configure DynamoDB Streams for real-time updates
- Add Lambda functions for automated analysis
- Set up backup/restore procedures

