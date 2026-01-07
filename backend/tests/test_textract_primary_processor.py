"""
Unit tests for Textract as primary PDF processor
Tests that PDF processing uses Textract by default
Requirements: 6.1
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import boto3
from botocore.exceptions import ClientError
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from enhanced_textract_extractor import EnhancedTextractExtractor


class TestTextractPrimaryProcessor:
    """Test that Textract is used as the primary PDF processor"""
    
    def test_textract_is_primary_processor(self):
        """Test that PDF processing uses Textract by default"""
        # Create a mock PDF bytes
        mock_pdf_bytes = b"mock_pdf_content"
        
        # Mock the Textract response
        mock_textract_response = {
            'Blocks': [
                {
                    'BlockType': 'LINE',
                    'Text': 'Sample financial data line 1'
                },
                {
                    'BlockType': 'LINE', 
                    'Text': 'Sample financial data line 2'
                }
            ]
        }
        
        with patch('boto3.Session') as mock_session:
            # Setup mock session and client
            mock_client = Mock()
            mock_client.analyze_document.return_value = mock_textract_response
            mock_session.return_value.client.return_value = mock_client
            
            # Initialize extractor
            extractor = EnhancedTextractExtractor()
            
            # Extract text - should use Textract first
            result = extractor.extract_text_from_pdf(mock_pdf_bytes)
            
            # Verify Textract was called
            mock_client.analyze_document.assert_called_once_with(
                Document={'Bytes': mock_pdf_bytes},
                FeatureTypes=['TABLES', 'FORMS']
            )
            
            # Verify result contains expected text
            assert 'Sample financial data line 1' in result
            assert 'Sample financial data line 2' in result
    
    def test_textract_initialization_with_aws_credentials(self):
        """Test that Textract client is properly initialized with AWS credentials"""
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_session.return_value.client.return_value = mock_client
            
            # Test with environment variables
            with patch.dict(os.environ, {
                'AWS_REGION': 'us-west-2',
                'AWS_PROFILE': 'test-profile'
            }):
                extractor = EnhancedTextractExtractor()
                
                # Verify session was created with correct parameters
                mock_session.assert_called_once_with(
                    profile_name='test-profile',
                    region_name='us-west-2'
                )
                
                # Verify Textract client was created
                mock_session.return_value.client.assert_called_once_with('textract')
    
    def test_textract_analyze_document_called_with_correct_features(self):
        """Test that Textract analyze_document is called with TABLES and FORMS features"""
        mock_pdf_bytes = b"test_pdf_content"
        
        mock_response = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Test line'}
            ]
        }
        
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_client.analyze_document.return_value = mock_response
            mock_session.return_value.client.return_value = mock_client
            
            extractor = EnhancedTextractExtractor()
            extractor.extract_text_from_pdf(mock_pdf_bytes)
            
            # Verify analyze_document was called with correct features
            call_args = mock_client.analyze_document.call_args
            assert call_args[1]['FeatureTypes'] == ['TABLES', 'FORMS']
            assert call_args[1]['Document']['Bytes'] == mock_pdf_bytes
    
    def test_textract_financial_data_extraction_uses_textract_first(self):
        """Test that financial data extraction uses Textract as primary method"""
        mock_pdf_bytes = b"financial_pdf_content"
        ticker = "AAPL"
        
        mock_response = {
            'Blocks': [
                {'BlockType': 'LINE', 'Text': 'Revenue: $100M'},
                {'BlockType': 'LINE', 'Text': 'Net Income: $20M'}
            ]
        }
        
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_client.analyze_document.return_value = mock_response
            mock_session.return_value.client.return_value = mock_client
            
            extractor = EnhancedTextractExtractor()
            structured_data, text = extractor.extract_financial_data(mock_pdf_bytes, ticker)
            
            # Verify Textract was called for financial data extraction
            mock_client.analyze_document.assert_called_once()
            
            # Verify structured data format
            assert isinstance(structured_data, dict)
            assert 'income_statement' in structured_data
            assert 'balance_sheet' in structured_data
            assert 'cashflow' in structured_data
            assert 'key_metrics' in structured_data
            
            # Verify text extraction
            assert 'Revenue: $100M' in text
            assert 'Net Income: $20M' in text
    
    def test_textract_service_availability_check(self):
        """Test that the system checks Textract service availability"""
        with patch('boto3.Session') as mock_session:
            # Simulate service unavailable
            mock_session.side_effect = Exception("AWS credentials not configured")
            
            # Should raise exception during initialization
            with pytest.raises(Exception) as exc_info:
                EnhancedTextractExtractor()
            
            # The original exception is re-raised, so check for the original message
            assert "AWS credentials not configured" in str(exc_info.value)
    
    def test_textract_processes_blocks_correctly(self):
        """Test that Textract response blocks are processed correctly"""
        mock_pdf_bytes = b"test_content"
        
        # Mock response with different block types
        mock_response = {
            'Blocks': [
                {'BlockType': 'PAGE', 'Text': 'Page content'},  # Should be ignored
                {'BlockType': 'LINE', 'Text': 'Line 1'},        # Should be included
                {'BlockType': 'WORD', 'Text': 'Word'},          # Should be ignored
                {'BlockType': 'LINE', 'Text': 'Line 2'},        # Should be included
                {'BlockType': 'TABLE'},                         # No text, should be ignored
            ]
        }
        
        with patch('boto3.Session') as mock_session:
            mock_client = Mock()
            mock_client.analyze_document.return_value = mock_response
            mock_session.return_value.client.return_value = mock_client
            
            extractor = EnhancedTextractExtractor()
            result = extractor.extract_text_from_pdf(mock_pdf_bytes)
            
            # Should only include LINE blocks
            assert 'Line 1' in result
            assert 'Line 2' in result
            assert 'Page content' not in result
            assert 'Word' not in result
            
            # Lines should be separated by newlines
            lines = result.split('\n')
            assert 'Line 1' in lines
            assert 'Line 2' in lines