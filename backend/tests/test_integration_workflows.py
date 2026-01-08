"""
Integration tests for complete workflows
Tests end-to-end functionality across multiple components
"""
import pytest
from fastapi.testclient import TestClient
import io

# Import the FastAPI app
from app.core.app import app
from app.services.batch_processing_service import BatchProcessingService, BatchJobStatus


class TestStockAnalysisWorkflow:
    """Test end-to-end stock analysis workflow"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)

    @pytest.mark.integration
    def test_complete_stock_analysis_workflow_basic(self):
        """Test basic stock analysis workflow components"""
        # Step 1: Search for ticker
        search_response = self.client.get("/api/search?q=AAPL")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "results" in search_data

        # Step 2: Get analysis presets
        presets_response = self.client.get("/api/analysis-presets")
        assert presets_response.status_code == 200
        presets_data = presets_response.json()
        assert "presets" in presets_data
        assert "business_types" in presets_data

        # Step 3: Test version endpoint
        version_response = self.client.get("/api/version")
        assert version_response.status_code == 200
        version_data = version_response.json()
        assert "version" in version_data

    @pytest.mark.integration
    def test_end_to_end_stock_analysis_workflow(self):
        """Test complete end-to-end stock analysis workflow"""
        # Step 1: Search for a ticker
        search_response = self.client.get("/api/search?q=AAPL")
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert "results" in search_data
        assert len(search_data["results"]) > 0

        # Step 2: Get analysis presets to understand available business types
        presets_response = self.client.get("/api/analysis-presets")
        assert presets_response.status_code == 200
        presets_data = presets_response.json()
        assert "presets" in presets_data
        assert "business_types" in presets_data
        available_business_types = presets_data["business_types"]
        assert len(available_business_types) > 0

        # Step 3: Check if we have AI data for a test ticker (use manual data if needed)
        test_ticker = "TESTSTOCK"
        ai_data_response = self.client.get(f"/api/check-ai-data/{test_ticker}")
        assert ai_data_response.status_code == 200
        ai_data = ai_data_response.json()

        # If no AI data exists, add some manual data first
        if not ai_data.get("has_ai_data", False):
            # Add manual income statement data
            income_data = {
                "ticker": test_ticker,
                "data_type": "income_statement",
                "period": "2023",
                "data": {
                    "Total Revenue": 10000000,
                    "Net Income": 1000000,
                    "Operating Income": 1500000,
                    "Cost of Revenue": 6000000,
                    "Operating Expenses": 2500000
                }
            }

            income_response = self.client.post("/api/manual-data", json=income_data)
            assert income_response.status_code == 200

            # Add manual balance sheet data
            balance_data = {
                "ticker": test_ticker,
                "data_type": "balance_sheet",
                "period": "2023",
                "data": {
                    "Total Assets": 5000000,
                    "Total Stockholder Equity": 3000000,
                    "Total Debt": 1500000,
                    "Cash and Cash Equivalents": 1000000,
                    "Current Assets": 2500000,
                    "Current Liabilities": 500000
                }
            }

            balance_response = self.client.post("/api/manual-data", json=balance_data)
            assert balance_response.status_code == 200

            # Add key metrics
            metrics_data = {
                "ticker": test_ticker,
                "data_type": "key_metrics",
                "period": "latest",
                "data": {
                    "shares_outstanding": 1000000,
                    "market_cap": 50000000
                }
            }

            metrics_response = self.client.post("/api/manual-data", json=metrics_data)
            assert metrics_response.status_code == 200

        # Step 4: Perform stock analysis with custom business type
        business_type = available_business_types[0] if available_business_types else "technology"
        analyze_response = self.client.get(
            f"/api/analyze/{test_ticker}?business_type={business_type}")

        # Analysis might fail for test data, but we should get a proper response
        if analyze_response.status_code == 200:
            analysis_data = analyze_response.json()

            # Verify analysis structure
            assert "ticker" in analysis_data
            assert "companyName" in analysis_data
            assert "currentPrice" in analysis_data
            assert "fairValue" in analysis_data
            assert "recommendation" in analysis_data
            assert "businessType" in analysis_data
            assert "analysisWeights" in analysis_data

            # Verify analysis components
            assert "financialHealth" in analysis_data
            assert "businessQuality" in analysis_data
            assert "managementQuality" in analysis_data

            # Step 5: Get quote for the ticker
            quote_response = self.client.get(f"/api/quote/{test_ticker}")
            # Quote might not be available for test ticker, but endpoint should work
            assert quote_response.status_code in [200, 404]

        elif analyze_response.status_code == 404:
            # Expected for test ticker without real market data
            error_data = analyze_response.json()
            assert "detail" in error_data
            assert "not found" in error_data["detail"].lower()
        else:
            # Other errors should be investigated
            pytest.fail(
                f"Unexpected analysis response: {analyze_response.status_code} - {analyze_response.text}")


class TestPDFProcessingWorkflow:
    """Test PDF upload and processing workflow"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)

    @pytest.mark.integration
    def test_manual_data_entry_workflow(self):
        """Test manual data entry workflow"""
        # Step 1: Add manual income statement data
        income_data = {
            "ticker": "MANUAL",
            "data_type": "income_statement",
            "period": "2023",
            "data": {
                "Total Revenue": 5000000,
                "Net Income": 500000,
                "Operating Income": 750000
            }
        }

        income_response = self.client.post("/api/manual-data", json=income_data)
        assert income_response.status_code == 200
        income_result = income_response.json()
        assert income_result["success"] is True

        # Step 2: Add manual balance sheet data
        balance_data = {
            "ticker": "MANUAL",
            "data_type": "balance_sheet",
            "period": "2023",
            "data": {
                "Total Assets": 2500000,
                "Total Stockholder Equity": 1500000,
                "Total Debt": 800000
            }
        }

        balance_response = self.client.post("/api/manual-data", json=balance_data)
        assert balance_response.status_code == 200
        balance_result = balance_response.json()
        assert balance_result["success"] is True

        # Step 3: Add key metrics
        metrics_data = {
            "ticker": "MANUAL",
            "data_type": "key_metrics",
            "period": "latest",
            "data": {
                "shares_outstanding": 5000000,
                "market_cap": 50000000
            }
        }

        metrics_response = self.client.post("/api/manual-data", json=metrics_data)
        assert metrics_response.status_code == 200
        metrics_result = metrics_response.json()
        assert metrics_result["success"] is True

        # Step 4: Check that data was saved
        ai_data_response = self.client.get("/api/check-ai-data/MANUAL")
        assert ai_data_response.status_code == 200
        ai_data = ai_data_response.json()
        assert ai_data["has_ai_data"] is True
        assert "data_summary" in ai_data
        assert ai_data["data_summary"]["income_statement_periods"] > 0
        assert ai_data["data_summary"]["balance_sheet_periods"] > 0

    @pytest.mark.integration
    def test_pdf_upload_error_workflow(self):
        """Test PDF upload error handling"""
        # Test 1: Upload invalid file type
        invalid_content = b"This is not a PDF file"
        files = {"file": ("test.txt", io.BytesIO(invalid_content), "text/plain")}

        response = self.client.post("/api/upload-pdf?ticker=TEST", files=files)
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "pdf" in error_data["detail"].lower()

        # Test 2: Upload empty file
        empty_content = b""
        files = {"file": ("empty.pdf", io.BytesIO(empty_content), "application/pdf")}

        response = self.client.post("/api/upload-pdf?ticker=TEST", files=files)
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

        # Test 3: Missing ticker parameter
        valid_pdf = self._create_test_pdf_content()
        files = {"file": ("test.pdf", io.BytesIO(valid_pdf), "application/pdf")}

        response = self.client.post(
            "/api/upload-pdf",
            files=files)  # No ticker parameter
        assert response.status_code == 422  # Validation error

    def _create_test_pdf_content(self) -> bytes:
        """Create a simple test PDF content for testing"""
        # This creates a minimal PDF structure for testing
        pdf_header = b"%PDF-1.4\n"
        pdf_body = b"""1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Financial Statement) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000053 00000 n
0000000100 00000 n
0000000179 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
273
%%EOF
"""
        return pdf_header + pdf_body


class TestBatchAnalysisWorkflow:
    """Test batch analysis workflow"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = TestClient(app)

    @pytest.mark.integration
    def test_complete_batch_analysis_workflow(self):
        """Test complete batch analysis workflow"""
        # Step 1: Prepare test data - add manual data for multiple tickers
        test_tickers = ["BATCH1", "BATCH2", "BATCH3"]

        for i, ticker in enumerate(test_tickers):
            # Add income statement data
            income_data = {
                "ticker": ticker,
                "data_type": "income_statement",
                "period": "2023",
                "data": {
                    "Total Revenue": 1000000 * (i + 1),
                    "Net Income": 100000 * (i + 1),
                    "Operating Income": 150000 * (i + 1)
                }
            }

            income_response = self.client.post("/api/manual-data", json=income_data)
            assert income_response.status_code == 200

            # Add balance sheet data
            balance_data = {
                "ticker": ticker,
                "data_type": "balance_sheet",
                "period": "2023",
                "data": {
                    "Total Assets": 500000 * (i + 1),
                    "Total Stockholder Equity": 300000 * (i + 1),
                    "Total Debt": 150000 * (i + 1)
                }
            }

            balance_response = self.client.post("/api/manual-data", json=balance_data)
            assert balance_response.status_code == 200

        # Step 2: Submit batch analysis request
        batch_request = {
            "exchange": "TEST",
            "tickers": test_tickers,
            "business_type": "technology",
            "force_refresh": True
        }

        batch_response = self.client.post("/api/batch-analyze", json=batch_request)
        assert batch_response.status_code == 200
        batch_result = batch_response.json()

        # Verify batch response structure
        assert "message" in batch_result
        assert "total_tickers" in batch_result
        assert batch_result["total_tickers"] == len(test_tickers)

        # Step 3: Check batch results
        results_response = self.client.get(f"/api/batch-results?exchange=TEST")
        assert results_response.status_code == 200
        results_data = results_response.json()

        # Verify results structure
        assert "results" in results_data
        assert "summary" in results_data
        assert isinstance(results_data["results"], list)

        # Step 4: Verify individual analyses were created
        for ticker in test_tickers:
            ai_data_response = self.client.get(f"/api/check-ai-data/{ticker}")
            assert ai_data_response.status_code == 200
            ai_data = ai_data_response.json()
            assert ai_data["has_ai_data"] is True

    @pytest.mark.integration
    async def test_batch_processing_service_workflow(self):
        """Test batch processing service directly"""
        # Create batch processing service
        batch_service = BatchProcessingService(max_workers=2, batch_size=10)

        # Sample dataset for processing
        dataset = [
            {"ticker": "AAPL", "price": 150.00},
            {"ticker": "MSFT", "price": 350.00},
            {"ticker": "GOOGL", "price": 2800.00},
            {"ticker": "INVALID", "price": -1.00}  # Invalid data to test error handling
        ]

        # Mock processor function
        def mock_processor(data):
            if data["price"] < 0:
                raise ValueError("Invalid price")
            return {
                "ticker": data["ticker"],
                "processed_price": data["price"] * 1.1,
                "status": "processed"
            }

        # Process batch
        result = await batch_service.process_batch(
            dataset=dataset,
            processor_func=mock_processor,
            validate_input=False
        )

        # Verify results
        assert result.status == BatchJobStatus.COMPLETED
        assert result.total_records == 4
        assert result.successful_records == 3
        assert result.failed_records == 1
        assert result.success_rate == 75.0

        # Check individual records
        successful_records = [r for r in result.records if r.status == "success"]
        failed_records = [r for r in result.records if r.status == "failed"]

        assert len(successful_records) == 3
        assert len(failed_records) == 1
        assert failed_records[0].error_message == "Processing error: Invalid price"

        # Verify successful record results
        for record in successful_records:
            assert record.result is not None
            assert "processed_price" in record.result
            assert record.result["status"] == "processed"

    @pytest.mark.integration
    def test_batch_analysis_error_workflow(self):
        """Test batch analysis error handling"""
        # Test 1: Submit batch request with invalid data
        invalid_request = {
            "exchange": "",  # Empty exchange
            "tickers": [],   # Empty tickers list
        }

        response = self.client.post("/api/batch-analyze", json=invalid_request)
        assert response.status_code == 400  # Business logic error
        error_data = response.json()
        assert "error" in error_data
        assert "message" in error_data["error"]

        # Test 2: Submit batch request with missing required fields
        incomplete_request = {
            "exchange": "TEST"
            # Missing tickers field
        }

        response = self.client.post("/api/batch-analyze", json=incomplete_request)
        assert response.status_code == 422  # Validation error

        # Test 3: Submit batch request with invalid ticker format
        invalid_ticker_request = {
            "exchange": "TEST",
            "tickers": ["", "VALID", None]  # Mix of invalid and valid tickers
        }

        response = self.client.post("/api/batch-analyze", json=invalid_ticker_request)
        # Should handle invalid tickers gracefully
        assert response.status_code in [200, 400, 422]
