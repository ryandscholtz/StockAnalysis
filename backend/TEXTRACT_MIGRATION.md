# Migration from Ollama/EC2 to AWS Textract

This document describes the migration from Ollama running on EC2 to AWS Textract for PDF financial data extraction.

## Changes Made

### 1. New AWS Textract Integration
- Created `app/data/textract_extractor.py` - AWS Textract client for PDF extraction
- Textract extracts text and tables from PDFs
- Uses OpenAI (optional) to structure the extracted data into financial statements

### 2. Updated PDF Extractor
- Modified `app/data/pdf_extractor.py` to use Textract instead of Ollama
- Removed EC2 auto-start/stop functionality
- Removed Ollama API calls
- Falls back to local extraction (pdfplumber/PyPDF2) if Textract is unavailable

### 3. Updated API Routes
- Removed Ollama/EC2 references from error messages
- Updated diagnostic messages to reference Textract instead
- Changed extraction method tracking from "llm_per_page" to "textract" or "local_extraction"

### 4. EC2 Instance Stopped
- Created `stop_ec2_instance.py` script to stop the EC2 instance
- Instance has been stopped to avoid charges

## Configuration

### Required Environment Variables

1. **AWS Credentials** (for Textract):
   - `AWS_PROFILE` (default: "Cerebrum") - AWS profile name
   - `AWS_REGION` (default: "us-east-1") - AWS region
   - Or use default AWS credentials (via `~/.aws/credentials`)

2. **OpenAI API Key** (optional but recommended):
   - `OPENAI_API_KEY` - For structuring extracted text into financial data
   - If not set, basic pattern matching will be used (less accurate)

3. **Textract Enable/Disable**:
   - `USE_TEXTRACT` (default: "true") - Set to "false" to use local extraction only

### IAM Permissions Required

Your AWS IAM user/role needs the following permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:AnalyzeDocument",
        "textract:DetectDocumentText"
      ],
      "Resource": "*"
    }
  ]
}
```

## Benefits

1. **No EC2 Costs**: Textract is serverless - pay only for what you use
2. **Better Scalability**: Textract handles concurrent requests automatically
3. **No Infrastructure Management**: No need to manage EC2 instances, IPs, or Ollama
4. **Better Table Extraction**: Textract excels at extracting structured tables from PDFs
5. **Reliability**: AWS managed service with high availability

## Cost Comparison

- **EC2**: ~$0.10-0.50/hour (depending on instance type) even when idle
- **Textract**: ~$1.50 per 1,000 pages (first 1,000 pages/month free)
- **OpenAI**: ~$0.15-0.60 per 1M tokens (for structuring data)

For typical usage (10-50 PDFs/month), Textract is significantly cheaper than running an EC2 instance 24/7.

## Migration Steps Completed

✅ Created Textract integration module
✅ Updated PDF extractor to use Textract
✅ Removed EC2/Ollama dependencies
✅ Updated API routes and error messages
✅ Stopped EC2 instance
✅ Created migration documentation

## Testing

To test the new Textract integration:

1. Ensure AWS credentials are configured
2. Set `USE_TEXTRACT=true` in `.env` (default)
3. Optionally set `OPENAI_API_KEY` for better extraction
4. Upload a PDF financial statement via the API
5. Check logs to verify Textract is being used

## Rollback (if needed)

If you need to rollback to Ollama:

1. Set `USE_TEXTRACT=false` in `.env`
2. Set `LLAMA_API_URL` to your Ollama instance
3. Restart the backend server

Note: The EC2 instance has been stopped. You'll need to start it again if rolling back.

