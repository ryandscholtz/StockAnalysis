"""
Auth & Watchlist Lambda - Handles authentication and watchlist CRUD operations
Dependencies: boto3 (DynamoDB), minimal libraries
"""
import json
import os
import boto3
from datetime import datetime
from decimal import Decimal
from urllib.parse import unquote

# DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
WATCHLIST_TABLE = os.getenv('WATCHLIST_TABLE', 'stock-analysis-watchlist')
MANUAL_DATA_TABLE = os.getenv('MANUAL_DATA_TABLE', 'stock-analysis-manual-data')
BUY_LIST_TABLE = os.getenv('BUY_LIST_TABLE', 'stock-analysis-buy-list')
DISCARDED_LIST_TABLE = os.getenv('DISCARDED_LIST_TABLE', 'stock-analysis-discarded-list')
DISCARDED_TTL_DAYS = 7


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
            # Recommendation — worst-of model vs AI analyst
            def _rec_severity(r):
                return {'Strong Buy': 1, 'Buy': 2, 'Hold': 3, 'Reduce': 4, 'Avoid': 5}.get(r or '', 0)
            model_rec = la.get('modelRecommendation') or (la.get('recommendation') if la.get('recommendation') != 'AI Conflict' else None)
            ai_rec = la.get('aiRecommendation')
            if model_rec and ai_rec:
                rec = model_rec if _rec_severity(model_rec) >= _rec_severity(ai_rec) else ai_rec
            else:
                rec = model_rec or ai_rec or la.get('recommendation')
            if rec is not None:
                it['recommendation'] = rec
            if model_rec is not None:
                it['modelRecommendation'] = model_rec
            if ai_rec is not None:
                it['aiRecommendation'] = ai_rec
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
        
        price_val = data.get('currentPrice') or data.get('pricePerShare') or 0
        item = {
            'userId': user_id,
            'ticker': ticker,
            'addedAt': datetime.now().isoformat(),
            'companyName': data.get('companyName', ticker),
            'exchange': data.get('exchange', ''),
            'currentPrice': Decimal(str(price_val)),
            'notes': data.get('notes', '')
        }
        # Optional fields — store only when provided
        for field in ('companyType', 'sector', 'currency'):
            if data.get(field):
                item[field] = data[field]

        # Analysis data — store when provided so watchlist shows results immediately
        # without depending solely on the enrichment lookup from manual-data table
        for field in ('recommendation', 'modelRecommendation', 'aiRecommendation', 'last_analyzed_at'):
            if data.get(field):
                item[field] = data[field]
        for field in ('fair_value', 'margin_of_safety_pct', 'upside_potential',
                      'pe_ratio', 'pb_ratio', 'ps_ratio', 'ev_to_ebitda', 'current_price'):
            if data.get(field) is not None:
                try:
                    item[field] = Decimal(str(data[field]))
                except Exception:
                    pass

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


# ---------------------------------------------------------------------------
# Discarded list
# ---------------------------------------------------------------------------

def get_discarded_list(user_id: str) -> dict:
    """Get user's discarded list (auto-expired items excluded by DynamoDB TTL)."""
    try:
        import time
        table = dynamodb.Table(DISCARDED_LIST_TABLE)
        now = int(time.time())
        response = table.query(
            KeyConditionExpression='userId = :uid',
            FilterExpression='attribute_not_exists(expires_at) OR expires_at > :now',
            ExpressionAttributeValues={':uid': user_id, ':now': now}
        )
        items = response.get('Items', [])
        return {
            'statusCode': 200,
            'body': json.dumps({'items': items}, cls=DecimalEncoder)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get discarded list: {str(e)}'})
        }


def add_to_discarded_list(user_id: str, ticker: str, data: dict) -> dict:
    """Add a stock to the discarded list with a 7-day TTL."""
    try:
        import time
        table = dynamodb.Table(DISCARDED_LIST_TABLE)
        expires_at = int(time.time()) + DISCARDED_TTL_DAYS * 86400
        item = {
            'userId': user_id,
            'ticker': ticker,
            'added_at': data.get('added_at', datetime.now().isoformat()),
            'expires_at': expires_at,
        }
        for field in ('company_name', 'exchange', 'currency', 'recommendation',
                      'reason'):
            if data.get(field):
                item[field] = data[field]
        table.put_item(Item=item)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Added to discarded list', 'item': item}, cls=DecimalEncoder)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to add to discarded list: {str(e)}'})
        }


def add_many_to_discarded_list(user_id: str, stocks: list) -> dict:
    """Batch-add multiple stocks to the discarded list."""
    try:
        import time
        table = dynamodb.Table(DISCARDED_LIST_TABLE)
        expires_at = int(time.time()) + DISCARDED_TTL_DAYS * 86400
        with table.batch_writer() as batch:
            for stock in stocks:
                ticker = stock.get('ticker', '')
                if not ticker:
                    continue
                item = {
                    'userId': user_id,
                    'ticker': ticker,
                    'added_at': datetime.now().isoformat(),
                    'expires_at': expires_at,
                }
                for field in ('company_name', 'exchange', 'currency', 'recommendation', 'reason'):
                    if stock.get(field):
                        item[field] = stock[field]
                batch.put_item(Item=item)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Added {len(stocks)} items to discarded list'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to batch-add to discarded list: {str(e)}'})
        }


def remove_from_discarded_list(user_id: str, ticker: str) -> dict:
    """Remove a stock from the discarded list."""
    try:
        table = dynamodb.Table(DISCARDED_LIST_TABLE)
        table.delete_item(Key={'userId': user_id, 'ticker': ticker})
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'message': 'Removed from discarded list'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to remove from discarded list: {str(e)}'})
        }


def get_buy_list(user_id: str) -> dict:
    """Get user's buy list."""
    try:
        table = dynamodb.Table(BUY_LIST_TABLE)
        response = table.query(
            KeyConditionExpression='userId = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )
        items = response.get('Items', [])
        return {
            'statusCode': 200,
            'body': json.dumps({'items': items}, cls=DecimalEncoder)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to get buy list: {str(e)}'})
        }


def add_to_buy_list(user_id: str, ticker: str, data: dict) -> dict:
    """Add or update a stock in the buy list. Preserves existing quantity if not provided."""
    try:
        table = dynamodb.Table(BUY_LIST_TABLE)

        # Fetch existing item to preserve quantity if not specified
        existing_qty = 1
        try:
            existing = table.get_item(Key={'userId': user_id, 'ticker': ticker}).get('Item')
            if existing:
                existing_qty = int(existing.get('quantity', 1))
        except Exception:
            pass

        qty = data.get('quantity', existing_qty)
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = existing_qty

        item = {
            'userId': user_id,
            'ticker': ticker,
            'added_at': data.get('added_at', datetime.now().isoformat()),
            'quantity': qty,
        }
        for field in ('company_name', 'exchange', 'currency', 'recommendation',
                      'modelRecommendation', 'aiRecommendation'):
            if data.get(field):
                item[field] = data[field]
        for field in ('current_price', 'fair_value', 'margin_of_safety_pct'):
            if data.get(field) is not None:
                try:
                    item[field] = Decimal(str(data[field]))
                except Exception:
                    pass

        table.put_item(Item=item)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Added to buy list', 'item': item}, cls=DecimalEncoder)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to add to buy list: {str(e)}'})
        }


def update_buy_list_quantity(user_id: str, ticker: str, quantity: int) -> dict:
    """Update the quantity for a buy list item."""
    try:
        table = dynamodb.Table(BUY_LIST_TABLE)
        table.update_item(
            Key={'userId': user_id, 'ticker': ticker},
            UpdateExpression='SET quantity = :q',
            ExpressionAttributeValues={':q': quantity}
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'quantity': quantity})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to update quantity: {str(e)}'})
        }


def remove_from_buy_list(user_id: str, ticker: str) -> dict:
    """Remove a stock from the buy list."""
    try:
        table = dynamodb.Table(BUY_LIST_TABLE)
        table.delete_item(Key={'userId': user_id, 'ticker': ticker})
        return {
            'statusCode': 200,
            'body': json.dumps({'success': True, 'message': 'Removed from buy list'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to remove from buy list: {str(e)}'})
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
    
    # Extract user ID from headers — API Gateway lowercases headers, so check both cases
    _headers = event.get('headers', {}) or {}
    user_id = _headers.get('X-User-Id') or _headers.get('x-user-id')

    # Fallback: extract sub from the Cognito JWT in Authorization header
    if not user_id:
        auth_header = _headers.get('Authorization') or _headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            try:
                import base64
                token = auth_header[7:]
                payload_b64 = token.split('.')[1]
                # Fix padding for base64
                payload_b64 += '=' * (-len(payload_b64) % 4)
                payload = json.loads(base64.b64decode(payload_b64).decode('utf-8'))
                user_id = payload.get('sub')
            except Exception:
                pass

    if not user_id and ('/api/watchlist' in path or '/api/manual-data' in path
                        or '/api/buy-list' in path or '/api/discarded-list' in path):
        return {
            'statusCode': 401,
            'headers': headers,
            'body': json.dumps({'error': 'Unauthorized: missing user identity'})
        }

    try:
        # Watchlist routes
        if '/api/watchlist' in path:
            if method == 'GET' and path == '/api/watchlist':
                result = get_watchlist(user_id)
            elif method == 'GET' and '/api/watchlist/' in path:
                ticker = unquote(path.split('/api/watchlist/')[-1])
                result = get_watchlist_item(user_id, ticker)
            elif method == 'POST':
                body = json.loads(event.get('body', '{}') or '{}')
                # Extract ticker from path (/api/watchlist/{ticker}) or body
                if '/api/watchlist/' in path:
                    ticker = unquote(path.split('/api/watchlist/')[-1].split('?')[0])
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
                ticker = unquote(path.split('/api/watchlist/')[-1])
                result = remove_from_watchlist(user_id, ticker)
            else:
                result = {
                    'statusCode': 405,
                    'body': json.dumps({'error': 'Method not allowed'})
                }
        
        # Buy list routes
        elif '/api/buy-list' in path:
            if method == 'GET' and path == '/api/buy-list':
                result = get_buy_list(user_id)
            elif method == 'POST' and '/api/buy-list/' in path:
                ticker = unquote(path.split('/api/buy-list/')[-1].split('?')[0])
                body = json.loads(event.get('body', '{}') or '{}')
                result = add_to_buy_list(user_id, ticker, body)
            elif method == 'PUT' and '/api/buy-list/' in path:
                ticker = unquote(path.split('/api/buy-list/')[-1].split('?')[0])
                body = json.loads(event.get('body', '{}') or '{}')
                quantity = body.get('quantity')
                if quantity is not None:
                    result = update_buy_list_quantity(user_id, ticker, int(quantity))
                else:
                    result = add_to_buy_list(user_id, ticker, body)
            elif method == 'DELETE' and '/api/buy-list/' in path:
                ticker = unquote(path.split('/api/buy-list/')[-1].split('?')[0])
                result = remove_from_buy_list(user_id, ticker)
            else:
                result = {
                    'statusCode': 405,
                    'body': json.dumps({'error': 'Method not allowed'})
                }

        # Discarded list routes
        elif '/api/discarded-list' in path:
            if method == 'GET':
                result = get_discarded_list(user_id)
            elif method == 'POST' and path == '/api/discarded-list':
                # Batch add: body = {"stocks": [{"ticker": ..., ...}, ...]}
                body = json.loads(event.get('body', '{}') or '{}')
                stocks = body.get('stocks', [])
                if stocks:
                    result = add_many_to_discarded_list(user_id, stocks)
                else:
                    result = {'statusCode': 400, 'body': json.dumps({'error': 'stocks list required'})}
            elif method == 'POST' and '/api/discarded-list/' in path:
                ticker = unquote(path.split('/api/discarded-list/')[-1].split('?')[0])
                body = json.loads(event.get('body', '{}') or '{}')
                result = add_to_discarded_list(user_id, ticker, body)
            elif method == 'DELETE' and '/api/discarded-list/' in path:
                ticker = unquote(path.split('/api/discarded-list/')[-1].split('?')[0])
                result = remove_from_discarded_list(user_id, ticker)
            else:
                result = {'statusCode': 405, 'body': json.dumps({'error': 'Method not allowed'})}

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
