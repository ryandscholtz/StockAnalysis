# PDF Extraction Fields

This document lists all the financial data fields that the LLM agent extracts from uploaded PDF financial statements.

## Income Statement Fields

The following fields are extracted from the Income Statement for each available period:

1. **Total Revenue** - Total sales/revenue for the period
2. **Net Income** - Net profit after all expenses
3. **Operating Income** - Income from operations (before interest and taxes)
4. **EBIT** - Earnings Before Interest and Taxes
5. **Income Before Tax** - Income before tax expenses

## Balance Sheet Fields

The following fields are extracted from the Balance Sheet for each available period:

1. **Total Assets** - Sum of all company assets
2. **Total Liabilities** - Sum of all company liabilities
3. **Total Stockholder Equity** - Shareholders' equity
4. **Cash And Cash Equivalents** - Cash and short-term investments
5. **Total Debt** - Total debt obligations

## Cash Flow Statement Fields

The following fields are extracted from the Cash Flow Statement for each available period:

1. **Operating Cash Flow** - Cash generated from operations
2. **Capital Expenditures** - Cash spent on capital assets (CapEx)
3. **Free Cash Flow** - Operating Cash Flow minus Capital Expenditures
4. **Cash From Financing Activities** - Cash from financing (debt, equity, dividends)

## Key Metrics

The following key metrics are extracted (typically for the most recent period):

1. **Shares Outstanding** - Number of shares issued
2. **Market Cap** - Market capitalization (if available in the document)

## Data Format

- **Periods**: Data is extracted for multiple periods when available (e.g., 2024, 2023, 2022)
- **Date Format**: Periods use dates in "YYYY-MM-DD" or "YYYY-12-31" format
- **Values**: All monetary values should be in the same currency as the document
- **Structure**: Data is returned as JSON with nested structure by statement type and period

## Example Output Structure

```json
{
  "income_statement": {
    "2024-12-31": {
      "Total Revenue": 1000000,
      "Net Income": 100000,
      "Operating Income": 150000,
      "EBIT": 150000,
      "Income Before Tax": 120000
    },
    "2023-12-31": {
      "Total Revenue": 950000,
      "Net Income": 95000,
      ...
    }
  },
  "balance_sheet": {
    "2024-12-31": {
      "Total Assets": 5000000,
      "Total Liabilities": 2000000,
      "Total Stockholder Equity": 3000000,
      "Cash And Cash Equivalents": 500000,
      "Total Debt": 1500000
    }
  },
  "cashflow": {
    "2024-12-31": {
      "Operating Cash Flow": 200000,
      "Capital Expenditures": 50000,
      "Free Cash Flow": 150000,
      "Cash From Financing Activities": -30000
    }
  },
  "key_metrics": {
    "Shares Outstanding": 1000000,
    "Market Cap": 50000000
  }
}
```

## Notes

- The LLM will attempt to extract all available periods from the document
- If a field is not found in the PDF, it will be omitted from the output
- The extraction uses fuzzy matching to find similar field names (e.g., "Revenue" vs "Total Revenue")
- All values should be numeric (no currency symbols or commas in the JSON output)

