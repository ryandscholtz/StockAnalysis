"""
AI-Powered Business Type Detection Service
Uses AWS Bedrock or OpenAI to analyze company information and determine the most appropriate valuation model
"""
import os
import logging
from typing import Optional, Dict, Any
from app.config.analysis_weights import BusinessType, AnalysisWeightPresets
from app.core.xray_middleware import trace_function, create_external_api_subsegment, end_subsegment

logger = logging.getLogger(__name__)


class BusinessTypeDetector:
    """AI-powered business type detector using AWS Bedrock or OpenAI"""

    def __init__(self):
        self.use_aws_bedrock = os.getenv("USE_AWS_BEDROCK", "false").lower() == "true"
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.aws_profile = os.getenv("AWS_PROFILE")  # Optional: use specific AWS profile
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

    def _get_available_business_types(self) -> str:
        """Get list of available business types for the prompt"""
        return ", ".join([bt.value.replace("_", " ").title() for bt in BusinessType])

    def _create_prompt(self, company_info: Dict[str, Any]) -> str:
        """Create prompt for AI analysis"""
        company_name = company_info.get("company_name", "Unknown")
        sector = company_info.get("sector", "Unknown")
        industry = company_info.get("industry", "Unknown")
        description = company_info.get("description", "")
        business_summary = company_info.get("business_summary", "")

        # Get financial context if available
        revenue_growth = company_info.get("revenue_growth", None)
        asset_intensity = company_info.get("asset_intensity", None)
        revenue = company_info.get("revenue", None)

        prompt = f"""Analyze the following company information and determine the most appropriate business type for valuation purposes.

Company: {company_name}
Sector: {sector}
Industry: {industry}
Description: {description or business_summary or "Not provided"}

Available business types: {self._get_available_business_types()}

Consider the following factors:
1. Industry characteristics (e.g., banks, REITs, insurance have specific models)
2. Business model (e.g., subscription/SaaS, e-commerce, franchise)
3. Growth stage (high growth, growth, mature, distressed)
4. Asset intensity (asset-heavy vs asset-light)
5. Revenue size and profitability

Based on this analysis, return ONLY the business type name (e.g., "technology", "bank", "high_growth", "subscription") that best matches this company.
If the company is a bank, REIT, or insurance company, prioritize those specific types.
If it's a technology company with subscription/recurring revenue, use "subscription".
If it's unclear, use "default".

Business type:"""

        return prompt

    @trace_function(name="ai.bedrock_business_type", annotations={"operation": "detect", "service": "bedrock"})
    def _call_aws_bedrock(self, prompt: str) -> Optional[str]:
        """Call AWS Bedrock for AI analysis"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            # Use AWS profile if specified, otherwise use default credentials
            session_kwargs = {'region_name': self.aws_region}
            if self.aws_profile:
                session_kwargs['profile_name'] = self.aws_profile

            session = boto3.Session(**session_kwargs)
            bedrock_runtime = session.client(service_name='bedrock-runtime')

            # Prepare the request
            if "claude" in self.bedrock_model_id.lower():
                # Claude format
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 100,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            else:
                # Generic format
                body = {
                    "prompt": prompt,
                    "max_tokens": 100,
                    "temperature": 0.3
                }

            response = bedrock_runtime.invoke_model(
                modelId=self.bedrock_model_id,
                body=body
            )

            # Parse response based on model
            response_body = response['body'].read()
            if "claude" in self.bedrock_model_id.lower():
                import json
                result = json.loads(response_body)
                content = result.get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "").strip().lower()
            else:
                import json
                result = json.loads(response_body)
                return result.get("generations", [{}])[0].get("text", "").strip().lower()

        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            return None
        except ClientError as e:
            logger.error(f"AWS Bedrock error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calling AWS Bedrock: {e}")
            return None

    @trace_function(name="ai.openai_business_type", annotations={"operation": "detect", "service": "openai"})
    def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API for AI analysis"""
        try:
            import openai

            if not self.openai_api_key:
                logger.warning("OpenAI API key not set")
                return None

            client = openai.OpenAI(api_key=self.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using mini for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a financial analyst expert at classifying companies for valuation purposes. Return only the business type name."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=50
            )

            result = response.choices[0].message.content.strip().lower()
            return result

        except ImportError:
            logger.warning("openai not installed. Install with: pip install openai")
            return None
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return None

    @trace_function(name="ai.detect_business_type", annotations={"operation": "detect", "service": "business_type_detector"})
    def detect_business_type_ai(self, company_info: Dict[str, Any]) -> Optional[BusinessType]:
        """
        Use AI to detect business type from company information

        Args:
            company_info: Dictionary with company information (company_name, sector, industry, description, etc.)

        Returns:
            BusinessType enum or None if detection fails
        """
        try:
            prompt = self._create_prompt(company_info)

            # Try AWS Bedrock first if enabled
            if self.use_aws_bedrock:
                result = self._call_aws_bedrock(prompt)
                if result:
                    return self._parse_business_type(result)

            # Fallback to OpenAI if available
            if self.openai_api_key:
                result = self._call_openai(prompt)
                if result:
                    return self._parse_business_type(result)

            logger.warning("No AI service available, falling back to rule-based detection")
            return None

        except Exception as e:
            logger.error(f"Error in AI business type detection: {e}")
            return None

    def _parse_business_type(self, ai_response: str) -> Optional[BusinessType]:
        """Parse AI response to BusinessType enum"""
        # Clean the response
        response_lower = ai_response.lower().strip()

        # Remove common prefixes/suffixes
        response_lower = response_lower.replace("business type:", "").strip()
        response_lower = response_lower.replace("the business type is", "").strip()
        response_lower = response_lower.replace("business type is", "").strip()
        response_lower = response_lower.split("\n")[0].strip()  # Take first line only
        response_lower = response_lower.split(".")[0].strip()  # Remove trailing period

        # Map to BusinessType enum
        type_mapping = {
            "high growth": BusinessType.HIGH_GROWTH,
            "high_growth": BusinessType.HIGH_GROWTH,
            "growth": BusinessType.GROWTH,
            "mature": BusinessType.MATURE,
            "cyclical": BusinessType.CYCLICAL,
            "asset heavy": BusinessType.ASSET_HEAVY,
            "asset_heavy": BusinessType.ASSET_HEAVY,
            "distressed": BusinessType.DISTRESSED,
            "bank": BusinessType.BANK,
            "reit": BusinessType.REIT,
            "insurance": BusinessType.INSURANCE,
            "utility": BusinessType.UTILITY,
            "utilities": BusinessType.UTILITY,
            "technology": BusinessType.TECHNOLOGY,
            "tech": BusinessType.TECHNOLOGY,
            "healthcare": BusinessType.HEALTHCARE,
            "retail": BusinessType.RETAIL,
            "energy": BusinessType.ENERGY,
            "professional services": BusinessType.PROFESSIONAL_SERVICES,
            "professional_services": BusinessType.PROFESSIONAL_SERVICES,
            "franchise": BusinessType.FRANCHISE,
            "e-commerce": BusinessType.ECOMMERCE,
            "ecommerce": BusinessType.ECOMMERCE,
            "subscription": BusinessType.SUBSCRIPTION,
            "manufacturing": BusinessType.MANUFACTURING,
            "default": BusinessType.DEFAULT,
        }

        # Try exact match first
        if response_lower in type_mapping:
            return type_mapping[response_lower]

        # Try partial match
        for key, value in type_mapping.items():
            if key in response_lower or response_lower in key:
                return value

        logger.warning(f"Could not parse business type from AI response: {ai_response}")
        return None

    def detect_with_fallback(self, company_info: Dict[str, Any],
                            sector: Optional[str] = None,
                            industry: Optional[str] = None,
                            revenue_growth: float = 0.0,
                            asset_intensity: float = 0.0) -> BusinessType:
        """
        Detect business type using AI first, then fallback to rule-based detection

        Args:
            company_info: Dictionary with company information
            sector: Company sector
            industry: Company industry
            revenue_growth: Revenue growth rate
            asset_intensity: Asset intensity ratio

        Returns:
            BusinessType enum
        """
        # Try AI detection first
        ai_result = self.detect_business_type_ai(company_info)
        if ai_result:
            logger.info(f"AI detected business type: {ai_result.value}")
            return ai_result

        # Fallback to rule-based detection
        logger.info("Using rule-based business type detection")
        return AnalysisWeightPresets.detect_business_type(
            sector=sector,
            industry=industry,
            revenue_growth=revenue_growth,
            asset_intensity=asset_intensity
        )
