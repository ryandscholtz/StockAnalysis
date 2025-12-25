# DynamoDB vs SQLite/PostgreSQL Analysis

## DynamoDB Overview

DynamoDB is AWS's managed NoSQL database - serverless, auto-scaling, and pay-per-use.

## Comparison

| Feature | SQLite | PostgreSQL | DynamoDB |
|---------|--------|------------|----------|
| **Infrastructure** | File-based | Server required | Serverless ✅ |
| **Setup Complexity** | Very Easy ✅ | Medium | Easy |
| **Cost** | Free ✅ | $15-50/month | Pay-per-use (~$1-5/month for small scale) |
| **Scalability** | Single server | Vertical scale | Auto-scales ✅ |
| **Query Flexibility** | Good SQL | Excellent SQL | Limited (but sufficient) |
| **Time-Series** | Good | Excellent | Excellent ✅ |
| **AWS Integration** | None | Manual | Native ✅ |
| **Learning Curve** | Low ✅ | Medium | Medium |
| **Vendor Lock-in** | None ✅ | None ✅ | AWS only |

## DynamoDB Advantages for This Use Case

### ✅ **Perfect Fit:**
1. **Time-Series Data**: Stock analyses are naturally time-series (ticker + date)
2. **Serverless**: No database to manage, scales automatically
3. **Cost-Effective**: Free tier (25GB storage, 25 RCU/WCU), then pay-per-use
4. **Fast Queries**: Single-digit millisecond latency
5. **AWS Integration**: You already have AWS accounts set up
6. **Auto-Scaling**: Handles batch processing spikes automatically

### ✅ **Access Patterns:**
- Get analysis by ticker + date ✅ (Partition + Sort Key)
- Query by exchange ✅ (GSI)
- Filter by recommendation ✅ (GSI)
- Filter by margin of safety ✅ (GSI with range)
- Historical tracking ✅ (Sort key = date)

## DynamoDB Design

### Table Structure

**Table: `stock-analyses`**

**Primary Key:**
- **PK (Partition Key)**: `TICKER#{ticker}` (e.g., `TICKER#AAPL`)
- **SK (Sort Key)**: `DATE#{date}` (e.g., `DATE#2024-12-23`)

**Attributes:**
- `ticker`: String (e.g., "AAPL")
- `analysis_date`: String (e.g., "2024-12-23")
- `exchange`: String (e.g., "NYSE")
- `company_name`: String
- `current_price`: Number
- `fair_value`: Number
- `margin_of_safety_pct`: Number
- `recommendation`: String
- `analysis_data`: Map (full JSON stored as DynamoDB Map)
- `financial_health_score`: Number
- `business_quality_score`: Number
- `sector`: String
- `industry`: String
- `pe_ratio`: Number
- ... (all other extracted fields)
- `analyzed_at`: String (ISO timestamp)
- `status`: String

### Global Secondary Indexes (GSIs)

**GSI1: Exchange-Date Index**
- **PK**: `EXCHANGE#{exchange}` (e.g., `EXCHANGE#JSE`)
- **SK**: `DATE#{date}` (e.g., `DATE#2024-12-23`)
- **Use**: Get all stocks for an exchange on a date

**GSI2: Recommendation-Date Index**
- **PK**: `REC#{recommendation}` (e.g., `REC#BUY`)
- **SK**: `DATE#{date}` (e.g., `DATE#2024-12-23`)
- **Use**: Find all BUY recommendations for a date

**GSI3: Sector-Quality Index**
- **PK**: `SECTOR#{sector}` (e.g., `SECTOR#Technology`)
- **SK**: `QUALITY#{business_quality_score}` (e.g., `QUALITY#85`)
- **Use**: Find high-quality stocks in a sector

## Cost Estimate

### Free Tier (Always Free):
- 25 GB storage
- 25 Read Capacity Units (RCU)
- 25 Write Capacity Units (WCU)

### Beyond Free Tier (Example: 1000 stocks/day):
- **Storage**: ~50KB per analysis = 50MB/day = ~1.5GB/month = **$0.38/month**
- **Writes**: 1000 writes/day = **~$0.25/month** (on-demand pricing)
- **Reads**: 10,000 reads/month = **~$0.25/month**
- **Total**: **~$0.88/month** (very affordable!)

### With Reserved Capacity:
- Even cheaper if you commit to consistent usage

## Implementation Complexity

### SQLite/PostgreSQL:
```python
# Simple SQL query
results = db.query("SELECT * FROM stock_analyses WHERE exchange = ? AND date = ?")
```

### DynamoDB:
```python
# DynamoDB query (slightly more verbose)
response = table.query(
    IndexName='ExchangeDateIndex',
    KeyConditionExpression='exchange = :ex AND analysis_date = :date',
    ExpressionAttributeValues={':ex': 'JSE', ':date': '2024-12-23'}
)
```

**Complexity**: Slightly higher, but manageable with helper functions.

## Migration Path

### Option 1: Start with SQLite, Migrate Later
- ✅ Quick to implement
- ✅ No AWS dependency
- ✅ Easy local development
- ❌ Need to migrate later

### Option 2: Start with DynamoDB
- ✅ Production-ready from day 1
- ✅ No migration needed
- ✅ Scales automatically
- ❌ Requires AWS setup
- ❌ Slightly more complex queries

## Recommendation

### **For Development/Testing**: SQLite ✅
- Faster iteration
- No AWS costs
- Easier debugging
- Can test locally

### **For Production**: DynamoDB ✅
- Serverless, no ops
- Auto-scales
- Cost-effective
- AWS-native

### **Best Approach**: Hybrid
1. **Start with SQLite** (current implementation)
2. **Add DynamoDB adapter** (same interface)
3. **Switch via config** (environment variable)
4. **Migrate data** when ready

## DynamoDB Implementation

Would need:
1. **Boto3** (AWS SDK for Python)
2. **DynamoDB table** (created via CDK/CloudFormation or manually)
3. **DynamoDB service class** (similar interface to current `DatabaseService`)
4. **Access pattern helpers** (for common queries)

## Conclusion

**DynamoDB is IDEAL for this use case IF:**
- ✅ You're deploying to AWS
- ✅ You want serverless/scalable
- ✅ You're okay with AWS vendor lock-in
- ✅ You want production-ready from start

**SQLite is BETTER IF:**
- ✅ You want local development
- ✅ You want zero AWS dependency
- ✅ You want simpler queries
- ✅ You're okay managing database later

**My Recommendation**: 
Start with SQLite (current), add DynamoDB adapter, switch via config. Best of both worlds!

