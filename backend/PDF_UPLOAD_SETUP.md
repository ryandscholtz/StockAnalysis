# PDF Upload and LLM Extraction Setup

This feature allows users to upload PDF financial statements (annual reports, 10-K filings, quarterly reports, etc.) and automatically extract financial data using AI.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `python-multipart` - For handling file uploads in FastAPI
- `PyPDF2` - PDF text extraction (fallback)
- `pdfplumber` - PDF text extraction (primary, better for tables)
- `openai` - OpenAI API client (optional)
- `anthropic` - Anthropic API client (optional)

### 2. Configure LLM Provider

Choose one of the following LLM providers:

#### Option A: OpenAI (Recommended)

1. Get an API key from https://platform.openai.com/api-keys
2. Add to your `.env` file:
```bash
OPENAI_API_KEY=your_api_key_here
LLM_PROVIDER=openai
```

#### Option B: Anthropic Claude

1. Get an API key from https://console.anthropic.com/
2. Add to your `.env` file:
```bash
ANTHROPIC_API_KEY=your_api_key_here
LLM_PROVIDER=anthropic
```

#### Option C: No LLM (Rule-based fallback)

If no API keys are provided, the system will use basic rule-based extraction (less accurate).

### 3. Usage

Once configured, users can:
1. Navigate to a stock analysis page
2. If fair value is 0 or data is missing, they'll see a PDF upload section
3. Upload a PDF financial statement
4. The AI will extract financial data automatically
5. The analysis will reload with the extracted data

## Supported PDF Types

- Annual Reports (10-K filings)
- Quarterly Reports (10-Q filings)
- Earnings Releases
- Financial Statements (Income Statement, Balance Sheet, Cash Flow)
- Investor Presentations with financial data

## How It Works

1. **PDF Text Extraction**: Uses `pdfplumber` (primary) or `PyPDF2` (fallback) to extract text and tables
2. **LLM Extraction**: Sends extracted text to LLM with a structured prompt to extract financial metrics
3. **Data Storage**: Extracted data is stored in the manual data store and used in subsequent analyses
4. **Automatic Integration**: The extracted data is automatically applied to the company data before valuation calculations

## API Endpoint

```
POST /api/upload-pdf?ticker=AAPL
Content-Type: multipart/form-data

Body:
  file: <PDF file>
```

Response:
```json
{
  "success": true,
  "message": "PDF processed successfully! Extracted 3 data period(s) for AAPL.",
  "updated_periods": 3
}
```

## Cost Considerations

- **OpenAI GPT-4o-mini**: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- **Anthropic Claude Haiku**: ~$0.25 per 1M input tokens, ~$1.25 per 1M output tokens
- Average PDF processing: ~$0.01-0.05 per document (depending on size)

## Troubleshooting

### "Could not extract text from PDF"
- PDF may be image-based (scanned). Consider using OCR first.
- PDF may be corrupted. Try re-saving the PDF.

### "LLM extraction failed"
- Check your API keys are set correctly
- Check your API quota/limits
- Check internet connectivity
- System will fall back to rule-based extraction

### "PDF file too large"
- Maximum file size is 50MB
- Consider splitting large documents or extracting relevant pages

