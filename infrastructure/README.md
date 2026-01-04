# Stock Analysis Infrastructure

CDK infrastructure for deploying the Stock Analysis DynamoDB table.

## Prerequisites

1. **AWS CLI configured**
   ```bash
   aws configure
   # Or use profiles: aws configure --profile Cerebrum
   ```

2. **Node.js 18+ installed**
   ```bash
   node --version
   ```

3. **CDK CLI installed**
   ```bash
   npm install -g aws-cdk
   cdk --version
   ```

## Setup

1. **Install dependencies**
   ```bash
   cd infrastructure
   npm install
   ```

2. **Bootstrap CDK** (first time only, per account/region)
   ```bash
   cdk bootstrap
   # Or with profile:
   cdk bootstrap --profile Cerebrum
   ```

3. **Deploy the stack**
   ```bash
   # Deploy to default AWS account/region
   cdk deploy
   
   # Or deploy with specific profile
   cdk deploy --profile Cerebrum
   
   # Or deploy to specific region
   cdk deploy --context region=eu-west-1
   ```

4. **Verify deployment**
   ```bash
   aws dynamodb describe-table --table-name stock-analyses
   ```

## Stack Outputs

After deployment, the stack outputs:
- **TableName**: `stock-analyses`
- **TableArn**: Full ARN of the table
- **Region**: AWS region

## Configuration

### Environment Variables

Set these in your backend `.env` file or environment:

```bash
USE_DYNAMODB=true
DYNAMODB_TABLE_NAME=stock-analyses
DYNAMODB_REGION=eu-west-1
AWS_PROFILE=Cerebrum
```

### AWS Profile

The application uses the Cerebrum AWS profile by default. To use a specific AWS profile:

```bash
export AWS_PROFILE=Cerebrum
```

## Table Structure

### Primary Key
- **PK** (Partition Key): `TICKER#{ticker}` (e.g., `TICKER#AAPL`)
- **SK** (Sort Key): `DATE#{date}` (e.g., `DATE#2024-12-23`)

### Global Secondary Indexes

1. **GSI1-ExchangeDate**: Query by exchange and date
   - PK: `GSI1PK = EXCHANGE#{exchange}`
   - SK: `GSI1SK = DATE#{date}`

2. **GSI2-RecommendationDate**: Query by recommendation and date
   - PK: `GSI2PK = REC#{recommendation}`
   - SK: `GSI2SK = DATE#{date}`

3. **GSI3-SectorQuality**: Query by sector and quality score
   - PK: `GSI3PK = SECTOR#{sector}`
   - SK: `GSI3SK = QUALITY#{score}`

## Cost

- **Free Tier**: 25GB storage, 25 RCU/WCU (always free)
- **On-Demand Pricing**: Pay per request
  - Writes: $1.25 per million
  - Reads: $0.25 per million
  - Storage: $0.25 per GB/month

**Example**: 1000 stocks/day = ~$0.88/month

## Useful Commands

```bash
# View differences before deploying
cdk diff

# Synthesize CloudFormation template
cdk synth

# View stack details
cdk list

# Destroy stack (careful!)
cdk destroy

# Deploy with specific profile
cdk deploy --profile Cerebrum

# Deploy to specific region
cdk deploy --context region=eu-west-1
```

## Troubleshooting

### "Table already exists"
If the table exists from a previous deployment:
- The stack will use the existing table (removalPolicy: RETAIN)
- Or delete the table manually: `aws dynamodb delete-table --table-name stock-analyses`

### "Access Denied"
- Check AWS credentials: `aws sts get-caller-identity`
- Verify IAM permissions for DynamoDB
- Check AWS profile: `aws configure list`

### "Region not found"
- Specify region: `cdk deploy --context region=eu-west-1`
- Or set in `cdk.json` context

## Migration from SQLite

After deploying DynamoDB:

1. Set environment variable:
   ```bash
   export USE_DYNAMODB=true
   ```

2. Run batch analysis - it will use DynamoDB automatically

3. (Optional) Migrate existing SQLite data:
   ```bash
   python scripts/migrate_sqlite_to_dynamodb.py
   ```

