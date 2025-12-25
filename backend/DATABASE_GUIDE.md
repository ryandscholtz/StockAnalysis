# Database Guide for Stock Analysis

## Overview

The system now uses SQLite to store stock analysis results, preventing unnecessary re-processing of stocks that have already been analyzed today.

## Database Structure

### StockAnalysis Table
Stores individual stock analysis results:

- **ticker** (Primary Key): Stock ticker symbol
- **exchange**: Exchange name (e.g., "JSE", "NYSE")
- **analysis_date**: Date in YYYY-MM-DD format
- **analyzed_at**: Timestamp when analysis was performed
- **analysis_data**: Full analysis JSON (all metrics, valuations, etc.)
- **fair_value**: Quick access field for filtering
- **current_price**: Quick access field
- **margin_of_safety_pct**: Quick access field
- **recommendation**: BUY, HOLD, or AVOID
- **financial_health_score**: Score 0-100
- **business_quality_score**: Score 0-100
- **status**: success, error, or partial
- **error_message**: Error details if status is error

### BatchJob Table
Tracks batch analysis jobs:

- **id**: Job ID
- **exchange**: Exchange name
- **started_at**: When job started
- **completed_at**: When job finished
- **status**: running, completed, failed, cancelled
- **total_tickers**: Total number of tickers
- **processed_tickers**: Number processed so far
- **successful_tickers**: Number successful
- **failed_tickers**: Number failed
- **ticker_list**: List of tickers in this batch

## How It Works

### Automatic Caching

When you run batch analysis:

1. **Check Database First**: For each ticker, the system checks if it's already been analyzed today
2. **Skip if Found**: If analysis exists for today, it loads from database instead of re-analyzing
3. **Save New Analyses**: New analyses are automatically saved to the database
4. **Update on Re-run**: If you re-run the same ticker, it updates the existing record

### Example Flow

```python
# First run - analyzes all stocks
python batch_analyze_exchange.py JSE jse_tickers.txt
# Result: Analyzes 300 stocks, saves to database

# Second run same day - skips all stocks
python batch_analyze_exchange.py JSE jse_tickers.txt
# Result: Loads all 300 from database instantly, no API calls

# Next day - analyzes again (new date)
python batch_analyze_exchange.py JSE jse_tickers.txt
# Result: Analyzes all 300 stocks again (new analysis_date)
```

## Usage

### Basic Usage

The database is automatically used when running batch analysis:

```bash
python batch_analyze_exchange.py JSE jse_tickers.txt
```

### Query Results Programmatically

```python
from app.database.db_service import DatabaseService

# Initialize service
db = DatabaseService(db_path="stock_analysis.db")

# Check if stock analyzed today
if db.has_analysis_today("MRF.JO"):
    print("Already analyzed today!")

# Get analysis
analysis = db.get_analysis("MRF.JO")
if analysis:
    print(f"Fair Value: {analysis['fair_value']}")
    print(f"Recommendation: {analysis['recommendation']}")

# Get all JSE analyses for today
jse_analyses = db.get_exchange_analyses("JSE")
print(f"Found {len(jse_analyses)} JSE analyses")

# Filter undervalued stocks
undervalued = [
    a for a in jse_analyses 
    if a.get('margin_of_safety_pct', 0) > 20
]
print(f"Found {len(undervalued)} undervalued stocks")
```

### Query with SQL

You can also query directly using SQLite:

```bash
# Open database
sqlite3 stock_analysis.db

# Find all BUY recommendations today
SELECT ticker, fair_value, current_price, margin_of_safety_pct
FROM stock_analyses
WHERE recommendation = 'BUY'
  AND analysis_date = date('now')
ORDER BY margin_of_safety_pct DESC;

# Find stocks with high quality scores
SELECT ticker, business_quality_score, financial_health_score
FROM stock_analyses
WHERE business_quality_score > 70
  AND financial_health_score > 70
  AND analysis_date = date('now');

# Count analyses by exchange
SELECT exchange, COUNT(*) as count
FROM stock_analyses
WHERE analysis_date = date('now')
GROUP BY exchange;
```

## Benefits

### 1. **No Re-processing**
- Stocks analyzed today are automatically skipped
- Saves API calls and processing time
- Instant results for already-analyzed stocks

### 2. **Historical Tracking**
- Each day's analysis is stored separately
- Can compare analyses across days
- Track how valuations change over time

### 3. **Fast Queries**
- Indexed fields for quick filtering
- Query by exchange, recommendation, date
- No need to parse JSON files

### 4. **Resume Capability**
- If batch job is interrupted, resume from database
- Know exactly which stocks were processed
- Track progress in real-time

## Configuration

### Database Location

Default: `stock_analysis.db` in the backend directory

To change:
```python
analyzer = BatchAnalyzer(
    use_database=True,
    db_path="custom/path/stock_analysis.db"
)
```

### Disable Database

If you want to use JSON files only:
```python
analyzer = BatchAnalyzer(
    use_database=False  # Use JSON files only
)
```

## Database Maintenance

### Backup Database

```bash
# Copy database file
cp stock_analysis.db stock_analysis_backup.db

# Or use SQLite backup
sqlite3 stock_analysis.db ".backup backup.db"
```

### Clean Old Data

```sql
-- Delete analyses older than 30 days
DELETE FROM stock_analyses
WHERE analysis_date < date('now', '-30 days');

-- Delete old batch jobs
DELETE FROM batch_jobs
WHERE completed_at < datetime('now', '-7 days');
```

### Vacuum Database

```sql
-- Reclaim space after deletions
VACUUM;
```

## Migration from JSON

If you have existing JSON results and want to import them:

```python
import json
from app.database.db_service import DatabaseService

db = DatabaseService()

# Load JSON file
with open('batch_results/JSE_20241223.json', 'r') as f:
    results = json.load(f)

# Import each result
for ticker, data in results.items():
    if data.get('status') == 'success':
        db.save_analysis(
            ticker=ticker,
            analysis_data=data.get('analysis', {}),
            exchange='JSE',
            analysis_date='2024-12-23'
        )
```

## Performance

- **Query Speed**: < 1ms for single ticker lookup
- **Storage**: ~50-100KB per stock analysis
- **Concurrent Access**: SQLite handles concurrent reads well
- **Write Performance**: Batch writes are optimized

## Limitations

- **Single Writer**: SQLite allows one writer at a time (fine for batch processing)
- **File Size**: SQLite databases can grow large (consider archiving old data)
- **No Network Access**: SQLite is file-based (use PostgreSQL for distributed systems)

## Future Enhancements

Potential improvements:
- PostgreSQL support for production
- Automatic archiving of old analyses
- Web UI for querying database
- Export to CSV/Excel
- Comparison views (today vs yesterday)
- Alert system for significant changes

