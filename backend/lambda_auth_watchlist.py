"""
Auth & Watchlist Lambda - Handles authentication and watchlist CRUD operations
Dependencies: boto3 (DynamoDB), minimal libraries
"""
import json
import os
import boto3
from datetime import datetime
from decimal import Decimal

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
WATCHLIST_TABLE = os.getenv('WATCHLIST_TABLE', 'stock-analysis-watchlist')
MANUAL_DATA_TABLE = os.getenv('MANUAL_DATA_TABLE', 'stock-analysis-manual-data')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types from DynamoDB"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def _enrich_with_latest_analysis(items: list) -> list:
    """Enrich watchlist items with latest_analysis from MANUAL_DATA_TABLE (price, valuation, PE)."""
    if not items:
        return items
    tickers = [it.get('ticker') for it in items if it.get('ticker')]
    if not tickers:
        return items
    try:
        manual_table = dynamodb.Table(MANUAL_DATA_TABLE)
        analysis_by_ticker = {}
        # BatchGetItem allows up to 100 keys per request
        for i in range(0, len(tickers), 100):
            batch = tickers[i:i + 100]
            response = dynamodb.meta.client.batch_get_item(
                RequestItems={
                    MANUAL_DATA_TABLE: {
                        'Keys': [{'ticker': t} for t in batch]
                    }
                }
            )
            for row in response.get('Responses', {}).get(MANUAL_DATA_TABLE, []):
                ticker = row.get('ticker')
                la = row.get('latest_analysis') or {}
                if isinstance(la, dict):
                    analysis_by_ticker[ticker] = la
        # Merge into each watchlist item (support both camelCase and snake_case for frontend)
        for it in items:
            t = it.get('ticker')
            la = analysis_by_ticker.get(t) or {}
            if not la:
                continue
            # Price — use explicit None checks so that 0 is preserved
            cp = la.get('currentPrice') if la.get('currentPrice') is not None else la.get('current_price')
            if cp is not None:
                it['current_price'] = float(cp) if hasattr(cp, '__float__') else cp
                it['currentPrice'] = it['current_price']
            # Currency
            currency = la.get('currency')
            if currency:
                it['currency'] = currency
            # Fair value & margin (valuation) — explicit None checks
            fv = la.get('fairValue') if la.get('fairValue') is not None else la.get('fair_value')
            if fv is not None:
                it['fair_value'] = float(fv) if hasattr(fv, '__float__') else fv
                it['fairValue'] = it['fair_value']
            mos = la.get('marginOfSafety') if la.get('marginOfSafety') is not None else la.get('margin_of_safety_pct')
            if mos is not None:
                it['margin_of_safety_pct'] = float(mos) if hasattr(mos, '__float__') else mos
                it['marginOfSafety'] = it['margin_of_safety_pct']
            # Recommendation
            rec = la.get('recommendation')
            if rec is not None:
                it['recommendation'] = rec
            # PE ratio from keyMetrics or top-level
            km = la.get('aiFinancialData') or la.get('ai_financial_data') or {}
            km = km.get('keyMetrics') or km.get('key_metrics') or {}
            pe = km.get('pe_ratio') or km.get('pe') or km.get('price_to_earnings')
            if pe is None:
                pe = la.get('pe_ratio') or la.get('priceToEarnings')
            if pe is not None:
                it['pe_ratio'] = float(pe) if hasattr(pe, '__float__') else pe
            # Timestamp for "last analyzed"
            ts = la.get('timestamp')
            if ts:
                it['last_analyzed_at'] = ts
                it['last_updated'] = ts
    except Exception as e:
        # Non-fatal: return items without enrichment
        print(f"[WARN] Watchlist enrichment failed: {e}")
    return items


def get_watchlist(user_id: str) -> dict:
    """Get user's watchlist enriched with latest analysis (price, valuation, PE)."""
    try:
        table = dynamodb.Table(WATCHLIST_TABLE)
        response = table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        
        items = response.get('Items', [])
        items = _enrich_with_latest_analysis(items)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'items': items}, cls=DecimalEncoder)
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get watchlist: {str(e)}'})
        }


def add_to_watchlist(user_id: str, ticker: str, data: dict) -> dict:
    """Add stock to watchlist"""
    try:
        table = dynamodb.Table(WATCHLIST_TABLE)
        
        item = {
            'userId': user_id,
            'ticker': ticker,
            'addedAt': datetime.now().isoformat(),
            'companyName': data.get('companyName', ticker),
            'currentPrice': Decimal(str(data.get('currentPrice', 0))),
            'notes': data.get('notes', '')
        }
        
        table.put_item(Item=item)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Added to watchlist', 'item': item}, cls=DecimalEncoder)
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to add to watchlist: {str(e)}'})
        }


def remove_from_watchlist(user_id: str, ticker: str) -> dict:
    """Remove stock from watchlist"""
    try:
        table = dynamodb.Table(WATCHLIST_TABLE)
        
        table.delete_item(
            Key={
                'userId': user_id,
                'ticker': ticker
            }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'message': 'Removed from watchlist'})
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to remove from watchlist: {str(e)}'})
        }


def get_watchlist_item(user_id: str, ticker: str) -> dict:
    """Get specific watchlist item"""
    try:
        table = dynamodb.Table(WATCHLIST_TABLE)
        
        response = table.get_item(
            Key={
                'userId': user_id,
                'ticker': ticker
            }
        )
        
        item = response.get('Item')
        
        if item:
            return {
                'statusCode': 200,
                'body': json.dumps({'item': item}, cls=DecimalEncoder)
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Item not found'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get watchlist item: {str(e)}'})
        }


def get_manual_data(ticker: str) -> dict:
    """Get manual financial data for a ticker"""
    try:
        table = dynamodb.Table(MANUAL_DATA_TABLE)
        
        response = table.get_item(
            Key={'ticker': ticker}
        )
        
        item = response.get('Item')
        
        if item:
            return {
                'statusCode': 200,
                'body': json.dumps(item, cls=DecimalEncoder)
            }
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No manual data found'})
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get manual data: {str(e)}'})
        }


def save_manual_data(ticker: str, data: dict) -> dict:
    """Save manual financial data for a ticker"""
    try:
        table = dynamodb.Table(MANUAL_DATA_TABLE)
        
        item = {
            'ticker': ticker,
            'updatedAt': datetime.now().isoformat(),
            **data
        }
        
        # Convert floats to Decimal for DynamoDB
        for key, value in item.items():
            if isinstance(value, float):
                item[key] = Decimal(str(value))
        
        table.put_item(Item=item)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Manual data saved', 'ticker': ticker})
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to save manual data: {str(e)}'})
        }


def lambda_handler(event, context):
    """AWS Lambda handler for auth and watchlist operations"""
    
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    # Extract user ID from headers or use default for testing
    user_id = event.get('headers', {}).get('X-User-Id', 'test-user')
    
    try:
        # Watchlist routes
        if '/api/watchlist' in path:
            if method == 'GET' and path == '/api/watchlist':
                result = get_watchlist(user_id)
            elif method == 'GET' and '/api/watchlist/' in path:
                ticker = path.split('/api/watchlist/')[-1]
                result = get_watchlist_item(user_id, ticker)
            elif method == 'POST':
                body = json.loads(event.get('body', '{}') or '{}')
                # Extract ticker from path (/api/watchlist/{ticker}) or body
                if '/api/watchlist/' in path:
                    ticker = path.split('/api/watchlist/')[-1].split('?')[0]
                else:
                    ticker = body.get('ticker', '')
                # Merge query string params into body for company_name/exchange/notes
                query_params = event.get('queryStringParameters') or {}
                if query_params.get('company_name'):
                    body['companyName'] = query_params['company_name']
                if query_params.get('exchange'):
                    body['exchange'] = query_params['exchange']
                if query_params.get('notes'):
                    body['notes'] = query_params['notes']
                result = add_to_watchlist(user_id, ticker, body)
            elif method == 'DELETE':
                ticker = path.split('/api/watchlist/')[-1]
                result = remove_from_watchlist(user_id, ticker)
            else:
                result = {
                    'statusCode': 405,
                    'body': json.dumps({'error': 'Method not allowed'})
                }
        
        # Manual data routes
        elif '/api/manual-data/' in path:
            ticker = path.split('/api/manual-data/')[-1]
            
            if method == 'GET':
                result = get_manual_data(ticker)
            elif method == 'POST' or method == 'PUT':
                body = json.loads(event.get('body', '{}'))
                result = save_manual_data(ticker, body)
            else:
                result = {
                    'statusCode': 405,
                    'body': json.dumps({'error': 'Method not allowed'})
                }
        
        # Health check
        elif path == '/health' or path == '/':
            result = {
                'statusCode': 200,
                'body': json.dumps({
                    'status': 'healthy',
                    'service': 'auth-watchlist',
                    'timestamp': datetime.now().isoformat()
                })
            }
        
        else:
            result = {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
        
        # Add CORS headers to result
        result['headers'] = headers
        return result
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
