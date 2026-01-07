"""
Unit tests for Bedrock AI integration
Tests that AI analysis features work with Bedrock
Requirements: 6.3
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ai.business_type_detector import BusinessTypeDetector
from app.config.analysis_weights import BusinessType


class TestBedrockAIIntegration:
    """Test that AI analysis features work with Bedrock"""
    
    def test_bedrock_enabled_by_environment_variable(self):
        """Test that Bedrock is enabled when USE_AWS_BEDROCK is set to true"""
        with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
            detector = BusinessTypeDetector()
            assert detector.use_aws_bedrock is True
    
    def test_bedrock_disabled_by_default(self):
        """Test that Bedrock is disabled by default"""
        with patch.dict(os.environ, {}, clear=True):
            detector = BusinessTypeDetector()
            assert detector.use_aws_bedrock is False
    
    def test_bedrock_model_id_configuration(self):
        """Test that Bedrock model ID can be configured"""
        custom_model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        
        with patch.dict(os.environ, {
            'USE_AWS_BEDROCK': 'true',
            'BEDROCK_MODEL_ID': custom_model_id
        }):
            detector = BusinessTypeDetector()
            assert detector.bedrock_model_id == custom_model_id
    
    def test_bedrock_aws_credentials_configuration(self):
        """Test that Bedrock uses AWS credentials configuration"""
        with patch.dict(os.environ, {
            'USE_AWS_BEDROCK': 'true',
            'AWS_REGION': 'us-west-2',
            'AWS_PROFILE': 'bedrock-profile'
        }):
            detector = BusinessTypeDetector()
            assert detector.aws_region == 'us-west-2'
            assert detector.aws_profile == 'bedrock-profile'
    
    def test_bedrock_claude_model_invocation(self):
        """Test that Bedrock correctly invokes Claude models"""
        company_info = {
            "company_name": "Test Tech Corp",
            "sector": "Technology",
            "industry": "Software",
            "description": "Cloud-based software solutions"
        }
        
        # Mock Bedrock response for Claude
        mock_response = {
            'body': Mock()
        }
        mock_response_body = {
            "content": [
                {"text": "technology"}
            ]
        }
        mock_response['body'].read.return_value = json.dumps(mock_response_body).encode()
        
        with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
            with patch('boto3.Session') as mock_session:
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.return_value = mock_response
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                detector = BusinessTypeDetector()
                result = detector.detect_business_type_ai(company_info)
                
                # Verify Bedrock was called
                mock_bedrock_client.invoke_model.assert_called_once()
                
                # Verify call parameters
                call_args = mock_bedrock_client.invoke_model.call_args
                assert call_args[1]['modelId'] == detector.bedrock_model_id
                
                # Verify request body format for Claude
                body = call_args[1]['body']
                assert 'anthropic_version' in body
                assert 'messages' in body
                assert body['max_tokens'] == 100
                
                # Verify result
                assert result == BusinessType.TECHNOLOGY
    
    def test_bedrock_generic_model_invocation(self):
        """Test that Bedrock works with non-Claude models"""
        company_info = {
            "company_name": "Bank Corp",
            "sector": "Financial Services",
            "industry": "Banking"
        }
        
        # Mock Bedrock response for generic model
        mock_response = {
            'body': Mock()
        }
        mock_response_body = {
            "generations": [
                {"text": "bank"}
            ]
        }
        mock_response['body'].read.return_value = json.dumps(mock_response_body).encode()
        
        with patch.dict(os.environ, {
            'USE_AWS_BEDROCK': 'true',
            'BEDROCK_MODEL_ID': 'amazon.titan-text-express-v1'
        }):
            with patch('boto3.Session') as mock_session:
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.return_value = mock_response
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                detector = BusinessTypeDetector()
                result = detector.detect_business_type_ai(company_info)
                
                # Verify Bedrock was called
                mock_bedrock_client.invoke_model.assert_called_once()
                
                # Verify request body format for generic model
                call_args = mock_bedrock_client.invoke_model.call_args
                body = call_args[1]['body']
                assert 'prompt' in body
                assert 'max_tokens' in body
                assert 'temperature' in body
                
                # Verify result
                assert result == BusinessType.BANK
    
    def test_bedrock_error_handling(self):
        """Test that Bedrock errors are handled gracefully"""
        company_info = {
            "company_name": "Test Corp",
            "sector": "Technology"
        }
        
        with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
            with patch('boto3.Session') as mock_session:
                # Simulate Bedrock error
                from botocore.exceptions import ClientError
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.side_effect = ClientError(
                    error_response={
                        'Error': {
                            'Code': 'ValidationException',
                            'Message': 'Invalid model ID'
                        }
                    },
                    operation_name='InvokeModel'
                )
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                detector = BusinessTypeDetector()
                result = detector.detect_business_type_ai(company_info)
                
                # Should return None on error
                assert result is None
    
    def test_bedrock_fallback_to_openai(self):
        """Test that system falls back to OpenAI when Bedrock fails"""
        company_info = {
            "company_name": "Healthcare Corp",
            "sector": "Healthcare"
        }
        
        with patch.dict(os.environ, {
            'USE_AWS_BEDROCK': 'true',
            'OPENAI_API_KEY': 'test-key'
        }):
            with patch('boto3.Session') as mock_session:
                # Bedrock fails
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock unavailable")
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                # OpenAI succeeds
                with patch('openai.OpenAI') as mock_openai:
                    mock_client = Mock()
                    mock_response = Mock()
                    mock_response.choices = [Mock()]
                    mock_response.choices[0].message.content = "healthcare"
                    mock_client.chat.completions.create.return_value = mock_response
                    mock_openai.return_value = mock_client
                    
                    detector = BusinessTypeDetector()
                    result = detector.detect_business_type_ai(company_info)
                    
                    # Should fall back to OpenAI and succeed
                    assert result == BusinessType.HEALTHCARE
                    mock_client.chat.completions.create.assert_called_once()
    
    def test_bedrock_prompt_creation_includes_company_info(self):
        """Test that Bedrock prompt includes all relevant company information"""
        company_info = {
            "company_name": "Advanced Manufacturing Inc",
            "sector": "Industrials",
            "industry": "Manufacturing",
            "description": "Advanced manufacturing solutions",
            "business_summary": "Industrial automation systems"
        }
        
        mock_response = {
            'body': Mock()
        }
        mock_response_body = {
            "content": [{"text": "manufacturing"}]
        }
        mock_response['body'].read.return_value = json.dumps(mock_response_body).encode()
        
        with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
            with patch('boto3.Session') as mock_session:
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.return_value = mock_response
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                detector = BusinessTypeDetector()
                detector.detect_business_type_ai(company_info)
                
                # Verify prompt includes company information
                call_args = mock_bedrock_client.invoke_model.call_args
                body = call_args[1]['body']
                prompt_content = body['messages'][0]['content']
                
                assert "Advanced Manufacturing Inc" in prompt_content
                assert "Industrials" in prompt_content
                assert "Manufacturing" in prompt_content
                assert "Advanced manufacturing solutions" in prompt_content
    
    def test_bedrock_business_type_parsing(self):
        """Test that Bedrock responses are correctly parsed to BusinessType enums"""
        test_cases = [
            ("technology", BusinessType.TECHNOLOGY),
            ("bank", BusinessType.BANK),
            ("reit", BusinessType.REIT),
            ("insurance", BusinessType.INSURANCE),
            ("high growth", BusinessType.HIGH_GROWTH),
            ("subscription", BusinessType.SUBSCRIPTION),
            ("manufacturing", BusinessType.MANUFACTURING),
            ("default", BusinessType.DEFAULT)
        ]
        
        for ai_response, expected_type in test_cases:
            company_info = {"company_name": "Test Corp"}
            
            mock_response = {
                'body': Mock()
            }
            mock_response_body = {
                "content": [{"text": ai_response}]
            }
            mock_response['body'].read.return_value = json.dumps(mock_response_body).encode()
            
            with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
                with patch('boto3.Session') as mock_session:
                    mock_bedrock_client = Mock()
                    mock_bedrock_client.invoke_model.return_value = mock_response
                    mock_session.return_value.client.return_value = mock_bedrock_client
                    
                    detector = BusinessTypeDetector()
                    result = detector.detect_business_type_ai(company_info)
                    
                    assert result == expected_type, f"Failed to parse '{ai_response}' to {expected_type}"
    
    def test_bedrock_integration_with_fallback_detection(self):
        """Test that Bedrock integrates properly with the fallback detection system"""
        company_info = {
            "company_name": "Utility Corp",
            "sector": "Utilities"
        }
        
        # Test when Bedrock succeeds
        mock_response = {
            'body': Mock()
        }
        mock_response_body = {
            "content": [{"text": "utility"}]
        }
        mock_response['body'].read.return_value = json.dumps(mock_response_body).encode()
        
        with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
            with patch('boto3.Session') as mock_session:
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.return_value = mock_response
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                detector = BusinessTypeDetector()
                result = detector.detect_with_fallback(
                    company_info=company_info,
                    sector="Utilities"
                )
                
                # Should use AI result
                assert result == BusinessType.UTILITY
        
        # Test when Bedrock fails - should use rule-based fallback
        with patch.dict(os.environ, {'USE_AWS_BEDROCK': 'true'}):
            with patch('boto3.Session') as mock_session:
                mock_bedrock_client = Mock()
                mock_bedrock_client.invoke_model.side_effect = Exception("Bedrock error")
                mock_session.return_value.client.return_value = mock_bedrock_client
                
                detector = BusinessTypeDetector()
                result = detector.detect_with_fallback(
                    company_info=company_info,
                    sector="Utilities"
                )
                
                # Should fall back to rule-based detection
                assert result is not None  # Rule-based should return something
                assert isinstance(result, BusinessType)