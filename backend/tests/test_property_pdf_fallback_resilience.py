"""
Property-based tests for PDF processing fallback resilience
Property 13: PDF Processing Fallback Resilience
Validates: Requirements 6.2
"""
from enhanced_textract_extractor import EnhancedTextractExtractor
import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import Mock, patch
from botocore.exceptions import ClientError
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestPDFProcessingFallbackResilience:
    """
    Property-based tests for PDF processing fallback resilience
    Feature: tech-stack-modernization, Property 13: PDF Processing Fallback Resilience
    For any PDF processing request, if Textract fails, the system should fall back to OCR and still produce extraction results
    """

    @given(
        pdf_size=st.integers(min_value=100, max_value=50000),
        textract_error_code=st.sampled_from([
            'UnsupportedDocumentException',
            'InvalidParameterException',
            'ThrottlingException',
            'InternalServerError',
            'AccessDeniedException'
        ]),
        ocr_available=st.booleans()
    )
    @settings(max_examples=50, deadline=5000)
    def test_pdf_processing_fallback_resilience_property(
            self, pdf_size, textract_error_code, ocr_available):
        """
        Property 13: PDF Processing Fallback Resilience
        For any PDF processing request, if Textract fails, the system should fall back to OCR and still produce extraction results
        """
        # Generate mock PDF bytes
        mock_pdf_bytes = b"x" * pdf_size

        # Mock Textract failure
        textract_error = ClientError(
            error_response={
                'Error': {
                    'Code': textract_error_code,
                    'Message': f'Textract error: {textract_error_code}'
                }
            },
            operation_name='AnalyzeDocument'
        )

        with patch('boto3.Session') as mock_session:
            # Setup Textract to fail
            mock_client = Mock()
            mock_client.analyze_document.side_effect = textract_error
            mock_session.return_value.client.return_value = mock_client

            # Mock OCR availability and response
            with patch('enhanced_textract_extractor.OCR_AVAILABLE', ocr_available):
                if ocr_available:
                    # Mock successful OCR fallback
                    mock_images = [Mock()]  # Mock PIL Image
                    mock_ocr_text = f"OCR extracted text from {pdf_size} byte PDF"

                    with patch('enhanced_textract_extractor.convert_from_bytes', return_value=mock_images), \
                            patch('enhanced_textract_extractor.pytesseract.image_to_string', return_value=mock_ocr_text):

                        extractor = EnhancedTextractExtractor()

                        # Should successfully extract text using OCR fallback
                        result = extractor.extract_text_from_pdf(mock_pdf_bytes)

                        # Verify fallback worked
                        assert result is not None
                        assert len(result) > 0
                        assert "OCR extracted text" in result

                        # Verify Textract was attempted first
                        mock_client.analyze_document.assert_called_once()
                else:
                    # OCR not available - should raise exception
                    extractor = EnhancedTextractExtractor()

                    with pytest.raises(Exception) as exc_info:
                        extractor.extract_text_from_pdf(mock_pdf_bytes)

                    # Should indicate OCR libraries not available
                    error_msg = str(exc_info.value).lower()
                    assert any(keyword in error_msg for keyword in [
                        'ocr', 'libraries', 'install', 'pytesseract', 'pdf2image'
                    ])

    @given(
        ticker=st.text(
            min_size=1, max_size=10, alphabet=st.characters(
                whitelist_categories=(
                    'Lu', 'Ll', 'Nd'))), pdf_content_size=st.integers(
            min_value=500, max_value=10000))
    @settings(max_examples=30, deadline=5000)
    def test_financial_data_extraction_fallback_resilience_property(
            self, ticker, pdf_content_size):
        """
        Property 13: Financial data extraction should fall back to OCR when Textract fails
        """
        assume(len(ticker.strip()) > 0)  # Ensure ticker is not empty

        mock_pdf_bytes = b"financial_data_" + b"x" * pdf_content_size

        # Mock Textract failure
        textract_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnsupportedDocumentException',
                    'Message': 'Document format not supported'
                }
            },
            operation_name='AnalyzeDocument'
        )

        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_client.analyze_document.side_effect = textract_error
            mock_session.return_value.client.return_value = mock_client

            # Mock OCR available and successful
            with patch('enhanced_textract_extractor.OCR_AVAILABLE', True):
                mock_images = [Mock()]
                mock_ocr_text = f"Financial data for {ticker}: Revenue $100M, Net Income $20M"

                with patch('enhanced_textract_extractor.convert_from_bytes', return_value=mock_images), \
                        patch('enhanced_textract_extractor.pytesseract.image_to_string', return_value=mock_ocr_text):

                    extractor = EnhancedTextractExtractor()

                    # Should successfully extract financial data using OCR fallback
                    structured_data, text = extractor.extract_financial_data(
                        mock_pdf_bytes, ticker)

                    # Verify fallback worked
                    assert structured_data is not None
                    assert isinstance(structured_data, dict)
                    assert 'income_statement' in structured_data
                    assert 'balance_sheet' in structured_data
                    assert 'cashflow' in structured_data
                    assert 'key_metrics' in structured_data

                    assert text is not None
                    assert len(text) > 0
                    assert ticker in text or "Financial data" in text

    @given(
        error_scenarios=st.lists(
            st.sampled_from([
                'UnsupportedDocumentException',
                'ThrottlingException',
                'InternalServerError',
                'AccessDeniedException',
                'InvalidParameterException'
            ]),
            min_size=1,
            max_size=3
        )
    )
    @settings(max_examples=20, deadline=5000)
    def test_multiple_textract_failures_still_fallback_property(self, error_scenarios):
        """
        Property 13: Multiple different Textract failures should all trigger OCR fallback
        """
        mock_pdf_bytes = b"test_pdf_content_for_multiple_failures"

        for error_code in error_scenarios:
            textract_error = ClientError(
                error_response={
                    'Error': {
                        'Code': error_code,
                        'Message': f'Textract error: {error_code}'
                    }
                },
                operation_name='AnalyzeDocument'
            )

            with patch('boto3.Session') as mock_session:
                mock_client = Mock()
                mock_client.analyze_document.side_effect = textract_error
                mock_session.return_value.client.return_value = mock_client

                # Mock OCR available and successful
                with patch('enhanced_textract_extractor.OCR_AVAILABLE', True):
                    mock_images = [Mock()]
                    mock_ocr_text = f"OCR fallback text for error {error_code}"

                    with patch('enhanced_textract_extractor.convert_from_bytes', return_value=mock_images), \
                            patch('enhanced_textract_extractor.pytesseract.image_to_string', return_value=mock_ocr_text):

                        extractor = EnhancedTextractExtractor()

                        # Should successfully fall back to OCR for any Textract error
                        result = extractor.extract_text_from_pdf(mock_pdf_bytes)

                        # Verify fallback worked regardless of error type
                        assert result is not None
                        assert len(result) > 0
                        assert f"OCR fallback text for error {error_code}" in result

                        # Verify Textract was attempted
                        mock_client.analyze_document.assert_called_once()

                        # Reset mock for next iteration
                        mock_client.reset_mock()

    @given(
        pdf_sizes=st.lists(
            st.integers(min_value=100, max_value=20000),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=15, deadline=5000)
    def test_fallback_resilience_across_pdf_sizes_property(self, pdf_sizes):
        """
        Property 13: Fallback resilience should work consistently across different PDF sizes
        """
        textract_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnsupportedDocumentException',
                    'Message': 'Document format not supported'
                }
            },
            operation_name='AnalyzeDocument'
        )

        for pdf_size in pdf_sizes:
            mock_pdf_bytes = b"pdf_content_" + b"x" * pdf_size

            with patch('boto3.Session') as mock_session:
                mock_client = Mock()
                mock_client.analyze_document.side_effect = textract_error
                mock_session.return_value.client.return_value = mock_client

                # Mock OCR available and successful
                with patch('enhanced_textract_extractor.OCR_AVAILABLE', True):
                    mock_images = [Mock()]
                    mock_ocr_text = f"OCR text for {pdf_size} byte PDF"

                    with patch('enhanced_textract_extractor.convert_from_bytes', return_value=mock_images), \
                            patch('enhanced_textract_extractor.pytesseract.image_to_string', return_value=mock_ocr_text):

                        extractor = EnhancedTextractExtractor()

                        # Should successfully fall back regardless of PDF size
                        result = extractor.extract_text_from_pdf(mock_pdf_bytes)

                        # Verify consistent fallback behavior
                        assert result is not None
                        assert len(result) > 0
                        assert f"OCR text for {pdf_size} byte PDF" in result

                        # Verify Textract was attempted
                        mock_client.analyze_document.assert_called_once()

                        # Reset for next iteration
                        mock_client.reset_mock()

    def test_fallback_preserves_extraction_interface(self):
        """
        Property 13: OCR fallback should preserve the same extraction interface as Textract
        """
        mock_pdf_bytes = b"interface_test_pdf"
        ticker = "TEST"

        textract_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'UnsupportedDocumentException',
                    'Message': 'Document format not supported'
                }
            },
            operation_name='AnalyzeDocument'
        )

        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_client.analyze_document.side_effect = textract_error
            mock_session.return_value.client.return_value = mock_client

            # Mock OCR available
            with patch('enhanced_textract_extractor.OCR_AVAILABLE', True):
                mock_images = [Mock()]
                mock_ocr_text = "OCR extracted financial data"

                with patch('enhanced_textract_extractor.convert_from_bytes', return_value=mock_images), \
                        patch('enhanced_textract_extractor.pytesseract.image_to_string', return_value=mock_ocr_text):

                    extractor = EnhancedTextractExtractor()

                    # Test text extraction interface
                    text_result = extractor.extract_text_from_pdf(mock_pdf_bytes)
                    assert isinstance(text_result, str)

                    # Test financial data extraction interface
                    structured_data, text = extractor.extract_financial_data(
                        mock_pdf_bytes, ticker)
                    assert isinstance(structured_data, dict)
                    assert isinstance(text, str)

                    # Verify expected structure is maintained
                    required_keys = [
                        'income_statement',
                        'balance_sheet',
                        'cashflow',
                        'key_metrics']
                    for key in required_keys:
                        assert key in structured_data
