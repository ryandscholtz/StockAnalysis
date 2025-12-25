# Batch Stock Analysis Guide

## Overview

This guide explains how to analyze all stocks on a specific exchange using batch processing with rate limiting and error recovery.

## Feasibility

**Small exchanges (JSE ~300 stocks):**
- Time: ~10-25 minutes
- Very feasible ✅

**Medium exchanges (LSE ~2,000 stocks):**
- Time: ~1.5-3 hours
- Feasible with rate limiting ✅

**Large exchanges (NYSE/NASDAQ ~2,400-3,300 stocks):**
- Time: ~2-4 hours
- Challenging but possible ⚠️
- Requires careful rate limiting

## Getting Ticker Lists

### Option 1: Manual List
Create a text file with one ticker per line:

```
MRF.JO
NPN.JO
BTI.JO
AGL.JO
```

### Option 2: Use Helper Script (JSE Example)
```bash
cd backend
python scripts/get_jse_tickers.py
```

This generates `jse_tickers.txt` with common JSE tickers.

### Option 3: Use Stock List APIs
For comprehensive lists, consider:
- **Financial Modeling Prep API**: Provides exchange listings
- **Alpha Vantage API**: Market data including listings
- **Exchange websites**: Many exchanges provide CSV downloads

## Running Batch Analysis

### Basic Usage

```bash
cd backend
python batch_analyze_exchange.py <exchange_name> <ticker_list_file>
```

### Example: JSE Analysis

```bash
# Step 1: Get ticker list (or create manually)
python scripts/get_jse_tickers.py

# Step 2: Run batch analysis
python batch_analyze_exchange.py JSE jse_tickers.txt
```

### Example: Custom Exchange

```bash
# Create ticker list file: my_exchange_tickers.txt
echo "AAPL" > my_exchange_tickers.txt
echo "MSFT" >> my_exchange_tickers.txt
echo "GOOGL" >> my_exchange_tickers.txt

# Run analysis
python batch_analyze_exchange.py "MyExchange" my_exchange_tickers.txt
```

## Configuration

Edit `batch_analyze_exchange.py` to adjust:

- **`max_concurrent`**: Number of stocks analyzed simultaneously (default: 5)
- **`requests_per_minute`**: Rate limit (default: 30/min = 1800/hour)

```python
analyzer = BatchAnalyzer(
    max_concurrent=5,        # Increase for faster processing (but watch rate limits)
    requests_per_minute=30,  # Decrease if hitting rate limits
    results_dir="batch_results"
)
```

## Results

Results are saved to `batch_results/` directory:

- **`{exchange}_{date}.json`**: Full analysis results for each ticker
- **`{exchange}_progress_{date}.json`**: Progress summary

### Resume Capability

If the process is interrupted, simply run the same command again. It will:
- Skip already processed tickers
- Continue from where it left off
- Merge results with existing file

## Rate Limiting

Yahoo Finance has rate limits (~2,000 requests/hour per IP). The default settings:
- 30 requests/minute = 1,800 requests/hour
- Leaves buffer for rate limit errors

If you hit rate limits:
1. Reduce `requests_per_minute` to 20-25
2. Reduce `max_concurrent` to 2-3
3. Add delays between batches

## Error Handling

The batch processor:
- ✅ Continues processing even if individual stocks fail
- ✅ Saves progress after each batch
- ✅ Logs errors for each failed ticker
- ✅ Provides summary of successes/failures

## Example Output

```
=== Batch Analysis: JSE ===
Total tickers: 300
Already completed: 0
Remaining: 300
Results file: batch_results/JSE_20241223.json
==================================================

Processing batch 1/6 (50 tickers)...
  Progress: 10/300 (✓ 8 | ✗ 2)
  Progress: 20/300 (✓ 17 | ✗ 3)
  ...

=== Batch Analysis Complete ===
Successful: 285
Failed: 15
Results saved to: batch_results/JSE_20241223.json
```

## Analyzing Results

### Load Results in Python

```python
import json

with open('batch_results/JSE_20241223.json', 'r') as f:
    results = json.load(f)

# Filter successful analyses
successful = {k: v for k, v in results.items() if v.get('status') == 'success'}

# Find undervalued stocks (example)
undervalued = []
for ticker, data in successful.items():
    analysis = data.get('analysis', {})
    if analysis.get('marginOfSafety', {}).get('percentage', 0) > 20:
        undervalued.append(ticker)

print(f"Found {len(undervalued)} undervalued stocks")
```

## Tips

1. **Start Small**: Test with 10-20 tickers first
2. **Monitor Progress**: Check `*_progress_*.json` files
3. **Check Rate Limits**: If many failures, reduce rate limit
4. **Run Overnight**: For large exchanges, run during off-peak hours
5. **Use Multiple IPs**: For very large batches, consider distributed processing

## Limitations

- **Ticker List Required**: You need to provide the ticker list (no automatic discovery)
- **Rate Limits**: Yahoo Finance limits may slow down large batches
- **Data Availability**: Some stocks may have insufficient data
- **Time**: Large exchanges take several hours to process

## Future Enhancements

Potential improvements:
- Automatic ticker discovery from exchange APIs
- Database storage instead of JSON files
- Web UI for monitoring batch progress
- Distributed processing across multiple servers
- Integration with paid APIs for better rate limits

