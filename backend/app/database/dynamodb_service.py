"""
DynamoDB service for stock analysis storage
Alternative to SQLite for AWS deployment
"""
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, date
from typing import Optional, Dict, List
from decimal import Decimal
import json
import os

from app.core.xray_middleware import create_database_subsegment, end_subsegment, trace_function


class DynamoDBService:
    """DynamoDB service for storing stock analyses"""
    
    def __init__(self, table_name: Optional[str] = None, region: Optional[str] = None):
        """
        Initialize DynamoDB service
        
        Args:
            table_name: DynamoDB table name (defaults to env var or "stock-analyses")
            region: AWS region (defaults to env var or "us-east-1")
        """
        self.table_name = table_name or os.getenv('DYNAMODB_TABLE_NAME', 'stock-analyses')
        self.region = region or os.getenv('DYNAMODB_REGION', 'eu-west-1')
        
        # Use AWS profile if set
        session = boto3.Session()
        if os.getenv('AWS_PROFILE'):
            session = boto3.Session(profile_name=os.getenv('AWS_PROFILE'))
        
        self.dynamodb = session.resource('dynamodb', region_name=self.region)
        self.table = self.dynamodb.Table(self.table_name)
    
    def _convert_to_dynamo(self, value):
        """Convert Python types to DynamoDB types"""
        if isinstance(value, float):
            # DynamoDB doesn't support float, use Decimal
            return Decimal(str(value))
        elif isinstance(value, dict):
            # Recursively convert dict values
            return {k: self._convert_to_dynamo(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._convert_to_dynamo(item) for item in value]
        elif value is None:
            return None
        return value
    
    def _convert_from_dynamo(self, value):
        """Convert DynamoDB types to Python types"""
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, dict):
            return {k: self._convert_from_dynamo(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._convert_from_dynamo(item) for item in value]
        return value
    
    @trace_function(name="dynamodb.has_analysis_today", annotations={"operation": "get_item", "table": "stock-analyses"})
    def has_analysis_today(self, ticker: str, analysis_date: Optional[str] = None) -> bool:
        """
        Check if stock has been analyzed today
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            True if analysis exists for today
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'TICKER#{ticker.upper()}',
                    'SK': f'DATE#{analysis_date}'
                },
                ProjectionExpression='PK'  # Only check existence
            )
            return 'Item' in response
        except ClientError as e:
            print(f"Error checking analysis: {e}")
            return False
    
    @trace_function(name="dynamodb.get_analysis", annotations={"operation": "get_item", "table": "stock-analyses"})
    def get_analysis(self, ticker: str, analysis_date: Optional[str] = None) -> Optional[Dict]:
        """
        Get analysis for a ticker
        
        Args:
            ticker: Stock ticker symbol
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            Analysis data dictionary or None
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'TICKER#{ticker.upper()}',
                    'SK': f'DATE#{analysis_date}'
                }
            )
            
            if 'Item' in response:
                item = response['Item']
                # Convert DynamoDB types back to Python
                result = self._convert_from_dynamo(item)
                # Remove PK/SK, add ticker/date
                result['ticker'] = ticker.upper()
                result['analysis_date'] = analysis_date
                return result
            return None
        except ClientError as e:
            print(f"Error getting analysis: {e}")
            return None
    
    @trace_function(name="dynamodb.save_analysis", annotations={"operation": "put_item", "table": "stock-analyses"})
    def save_analysis(self,
                     ticker: str,
                     analysis_data: Dict,
                     exchange: Optional[str] = None,
                     analysis_date: Optional[str] = None) -> bool:
        """
        Save analysis to DynamoDB
        
        Args:
            ticker: Stock ticker symbol
            analysis_data: Full analysis data dictionary
            exchange: Exchange name (optional)
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
        
        Returns:
            True if saved successfully
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        try:
            # Extract key fields (same as SQLite version)
            item = {
                'PK': f'TICKER#{ticker.upper()}',
                'SK': f'DATE#{analysis_date}',
                'ticker': ticker.upper(),
                'analysis_date': analysis_date,
                'analyzed_at': datetime.utcnow().isoformat(),
                'status': 'success'
            }
            
            # Add exchange if provided
            if exchange:
                item['exchange'] = exchange
                item['GSI1PK'] = f'EXCHANGE#{exchange}'  # For GSI1
                item['GSI1SK'] = f'DATE#{analysis_date}'
            
            # Extract and add quick-access fields
            item['current_price'] = self._convert_to_dynamo(analysis_data.get('currentPrice'))
            item['fair_value'] = self._convert_to_dynamo(analysis_data.get('fairValue'))
            item['company_name'] = analysis_data.get('companyName')
            
            margin_of_safety = analysis_data.get('marginOfSafety', {})
            item['margin_of_safety_pct'] = self._convert_to_dynamo(
                margin_of_safety.get('percentage') if isinstance(margin_of_safety, dict) 
                else margin_of_safety if isinstance(margin_of_safety, (int, float)) else None
            )
            item['upside_potential_pct'] = self._convert_to_dynamo(analysis_data.get('upsidePotential'))
            item['price_to_intrinsic_value'] = self._convert_to_dynamo(analysis_data.get('priceToIntrinsicValue'))
            item['recommendation'] = analysis_data.get('recommendation')
            
            # Valuation breakdown
            valuation = analysis_data.get('valuation', {})
            if isinstance(valuation, dict):
                item['dcf_value'] = self._convert_to_dynamo(valuation.get('dcfValue'))
                item['epv_value'] = self._convert_to_dynamo(valuation.get('epvValue'))
                item['asset_value'] = self._convert_to_dynamo(valuation.get('assetBasedValue'))
            
            # Scores
            financial_health = analysis_data.get('financialHealth', {})
            business_quality = analysis_data.get('businessQuality', {})
            management_quality = analysis_data.get('managementQuality', {})
            
            item['financial_health_score'] = self._convert_to_dynamo(
                financial_health.get('score') if isinstance(financial_health, dict) else None
            )
            item['business_quality_score'] = self._convert_to_dynamo(
                business_quality.get('score') if isinstance(business_quality, dict) else None
            )
            item['management_quality_score'] = self._convert_to_dynamo(
                management_quality.get('score') if isinstance(management_quality, dict) else None
            )
            
            # Company info
            item['sector'] = analysis_data.get('sector')
            item['industry'] = analysis_data.get('industry')
            item['currency'] = analysis_data.get('currency')
            
            # Analysis configuration (new fields)
            item['business_type'] = analysis_data.get('businessType')
            analysis_weights = analysis_data.get('analysisWeights')
            if analysis_weights:
                # Convert to JSON string for DynamoDB
                item['analysis_weights'] = json.dumps(analysis_weights) if isinstance(analysis_weights, dict) else analysis_weights
            
            # Price ratios
            price_ratios = analysis_data.get('priceRatios', {})
            if isinstance(price_ratios, dict):
                item['pe_ratio'] = self._convert_to_dynamo(price_ratios.get('peRatio'))
                item['pb_ratio'] = self._convert_to_dynamo(price_ratios.get('pbRatio'))
                item['ps_ratio'] = self._convert_to_dynamo(price_ratios.get('psRatio'))
            
            # Growth metrics
            growth_metrics = analysis_data.get('growthMetrics', {})
            if isinstance(growth_metrics, dict):
                item['revenue_growth_1y'] = self._convert_to_dynamo(growth_metrics.get('revenueGrowth1Y'))
                item['earnings_growth_1y'] = self._convert_to_dynamo(growth_metrics.get('earningsGrowth1Y'))
            
            # Store full analysis as DynamoDB Map
            item['analysis_data'] = self._convert_to_dynamo(analysis_data)
            
            # Add GSI keys for recommendation
            if item.get('recommendation'):
                item['GSI2PK'] = f'REC#{item["recommendation"]}'
                item['GSI2SK'] = f'DATE#{analysis_date}'
            
            # Add GSI keys for sector (if available)
            if item.get('sector') and item.get('business_quality_score'):
                item['GSI3PK'] = f'SECTOR#{item["sector"]}'
                item['GSI3SK'] = f'QUALITY#{item["business_quality_score"]}'
            
            # Remove None values (DynamoDB doesn't allow None)
            item = {k: v for k, v in item.items() if v is not None}
            
            # Put item
            self.table.put_item(Item=item)
            return True
            
        except ClientError as e:
            print(f"Error saving analysis for {ticker}: {e}")
            return False
    
    def save_error(self,
                  ticker: str,
                  error_message: str,
                  exchange: Optional[str] = None,
                  analysis_date: Optional[str] = None) -> bool:
        """Save error record"""
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        try:
            item = {
                'PK': f'TICKER#{ticker.upper()}',
                'SK': f'DATE#{analysis_date}',
                'ticker': ticker.upper(),
                'analysis_date': analysis_date,
                'analyzed_at': datetime.utcnow().isoformat(),
                'status': 'error',
                'error_message': error_message[:500]
            }
            
            if exchange:
                item['exchange'] = exchange
            
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error saving error for {ticker}: {e}")
            return False
    
    def get_exchange_analyses(self,
                             exchange: str,
                             analysis_date: Optional[str] = None,
                             limit: Optional[int] = None) -> List[Dict]:
        """
        Get all analyses for an exchange using GSI1
        
        Args:
            exchange: Exchange name
            analysis_date: Date in YYYY-MM-DD format (defaults to today)
            limit: Maximum number of results
        
        Returns:
            List of analysis dictionaries
        """
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        try:
            query_params = {
                'IndexName': 'GSI1-ExchangeDate',
                'KeyConditionExpression': 'GSI1PK = :ex AND GSI1SK = :date',
                'ExpressionAttributeValues': {
                    ':ex': f'EXCHANGE#{exchange}',
                    ':date': f'DATE#{analysis_date}'
                },
                'FilterExpression': '#status = :success',
                'ExpressionAttributeNames': {
                    '#status': 'status'
                }
            }
            
            if limit:
                query_params['Limit'] = limit
            
            response = self.table.query(**query_params)
            
            results = []
            for item in response.get('Items', []):
                result = self._convert_from_dynamo(item)
                result['ticker'] = result.get('PK', '').replace('TICKER#', '')
                result['analysis_date'] = result.get('SK', '').replace('DATE#', '')
                results.append(result)
            
            return results
            
        except ClientError as e:
            print(f"Error querying exchange analyses: {e}")
            return []

