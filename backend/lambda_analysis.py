"""
Analysis Lambda - Handles stock analysis and valuation calculations
Uses Claude AI via Bedrock to fetch real financial data for each stock
"""
import json
import os
import boto3
from datetime import datetime
from decimal import Decimal, InvalidOperation

MANUAL_DATA_TABLE = os.environ.get('MANUAL_DATA_TABLE', 'stock-analysis-manual-data')

# Optional imports with fallbacks
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


# ---------------------------------------------------------------------------
# DynamoDB helpers
# ---------------------------------------------------------------------------

def _convert_for_dynamo(obj):
    """Recursively convert floats/ints to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        try:
            return Decimal(str(obj))
        except InvalidOperation:
            return None
    if isinstance(obj, dict):
        return {k: _convert_for_dynamo(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_convert_for_dynamo(v) for v in obj]
    return obj


def _save_ai_financial_data(ticker: str, inc: dict, bal: dict, cf: dict, km: dict, fiscal_year: str) -> None:
    """
    Persist AI-fetched financial data to DynamoDB so it appears in the
    'Stored Financial Data' panel on the ticker page.
    Non-fatal — a failure here does not block the analysis response.
    """
    try:
        period = fiscal_year or f"{datetime.now().year - 1}-12-31"
        now = datetime.now().isoformat()

        financial_data: dict = {}
        metadata: dict = {}

        for section_key, data in [
            ('income_statement', inc),
            ('balance_sheet', bal),
            ('cashflow', cf),
        ]:
            if data:
                financial_data[section_key] = {period: data}
                metadata[section_key] = {
                    'last_updated': now,
                    'source': 'ai_bedrock',
                    'period_count': 1,
                }

        if km:
            financial_data['key_metrics'] = {'latest': km}
            metadata['key_metrics'] = {
                'last_updated': now,
                'source': 'ai_bedrock',
                'period_count': 1,
            }

        if not financial_data:
            return

        item = _convert_for_dynamo({
            'ticker': ticker,
            'updatedAt': now,
            'financial_data': financial_data,
            'metadata': metadata,
            'has_data': True,
        })

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table(MANUAL_DATA_TABLE)
        table.put_item(Item=item)
    except Exception as exc:
        print(f"[WARN] Could not persist AI financial data for {ticker}: {exc}")


# ---------------------------------------------------------------------------
# SEC EDGAR helpers — real annual data for US-listed stocks
# ---------------------------------------------------------------------------

# Maps our field names → lists of US-GAAP concept names (first match wins)
_SEC_CONCEPT_MAP = {
    'income_statement': {
        'Total Revenue':    ['RevenueFromContractWithCustomerExcludingAssessedTax',
                             'Revenues', 'SalesRevenueNet',
                             'RevenueFromContractWithCustomerIncludingAssessedTax'],
        'Gross Profit':     ['GrossProfit'],
        'Operating Income': ['OperatingIncomeLoss'],
        'Net Income':       ['NetIncomeLoss'],
        'Basic EPS':        ['EarningsPerShareBasic'],
        'Diluted EPS':      ['EarningsPerShareDiluted'],
    },
    'balance_sheet': {
        'Total Assets':     ['Assets'],
        'Current Assets':   ['AssetsCurrent'],
        'Cash And Cash Equivalents': ['CashAndCashEquivalentsAtCarryingValue'],
        'Total Liabilities Net Minority Interest': ['Liabilities'],
        'Current Liabilities': ['LiabilitiesCurrent'],
        'Long Term Debt':   ['LongTermDebtNoncurrent', 'LongTermDebt'],
        'Total Stockholder Equity': [
            'StockholdersEquity',
            'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',
        ],
        'Retained Earnings': ['RetainedEarningsAccumulatedDeficit'],
    },
    'cashflow': {
        'Operating Cash Flow': ['NetCashProvidedByUsedInOperatingActivities'],
        'Capital Expenditure': ['PaymentsToAcquirePropertyPlantAndEquipment'],
        'Common Stock Dividends Paid': ['PaymentsOfDividendsCommonStock', 'PaymentsOfDividends'],
    },
    'key_metrics': {
        'shares_outstanding': ['CommonStockSharesOutstanding'],
    },
}


def _sec_json(url: str, timeout: int = 20) -> dict | None:
    """Download JSON from SEC EDGAR, handling gzip transparently."""
    from urllib.request import Request, urlopen
    import gzip as _gzip
    try:
        req = Request(url, headers={
            'User-Agent': 'StockAnalysisTool research@stockanalysis.app',
            'Accept-Encoding': 'gzip',
            'Accept': 'application/json',
        })
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            if resp.info().get('Content-Encoding') == 'gzip':
                raw = _gzip.decompress(raw)
            return json.loads(raw.decode('utf-8'))
    except Exception as e:
        print(f"[SEC] HTTP error ({url}): {e}")
        return None


def _sec_cik(ticker: str) -> str | None:
    """Return zero-padded 10-digit CIK for a US ticker, or None."""
    data = _sec_json('https://www.sec.gov/files/company_tickers.json', timeout=10)
    if not data:
        return None
    ticker_up = ticker.upper()
    for entry in data.values():
        if entry.get('ticker', '').upper() == ticker_up:
            return str(entry['cik_str']).zfill(10)
    return None


def _sec_latest_annual_value(gaap: dict, concept: str) -> float | None:
    """Return the most recent 10-K annual value for a US-GAAP concept, or None."""
    concept_data = gaap.get(concept, {})
    for unit in ('USD', 'shares', 'USD/shares', 'pure'):
        entries = concept_data.get('units', {}).get(unit, [])
        annual = [e for e in entries if e.get('form') == '10-K' and e.get('fp') == 'FY']
        if not annual:
            continue
        annual.sort(key=lambda e: e.get('end', ''), reverse=True)
        return annual[0].get('val')
    return None


def get_financial_data_from_sec(ticker: str) -> dict | None:
    """
    Fetch the latest annual financial data from SEC EDGAR XBRL.
    Returns data in the same format as get_financial_data_with_ai, or None on failure.
    Only works for US-listed tickers (no exchange suffix like .XJSE, .L, .JO).
    """
    if '.' in ticker:
        return None  # Non-US ticker — skip SEC

    print(f"[SEC] Looking up CIK for {ticker}...")
    cik = _sec_cik(ticker)
    if not cik:
        print(f"[SEC] No CIK found for {ticker}")
        return None

    print(f"[SEC] CIK={cik}, fetching company facts...")
    facts_data = _sec_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", timeout=25)
    if not facts_data:
        return None

    gaap = facts_data.get('facts', {}).get('us-gaap', {})
    if not gaap:
        print(f"[SEC] No US-GAAP data for {ticker}")
        return None

    # Extract each field, using the first matching concept
    result: dict[str, dict] = {s: {} for s in _SEC_CONCEPT_MAP}
    fiscal_year: str | None = None

    for section, fields in _SEC_CONCEPT_MAP.items():
        for field_name, concepts in fields.items():
            for concept in concepts:
                val = _sec_latest_annual_value(gaap, concept)
                if val is not None:
                    result[section][field_name] = val
                    # Capture fiscal year end date from the first successful concept
                    if fiscal_year is None:
                        entries = gaap.get(concept, {}).get('units', {})
                        for unit_entries in entries.values():
                            annual = [e for e in unit_entries
                                      if e.get('form') == '10-K' and e.get('fp') == 'FY']
                            if annual:
                                annual.sort(key=lambda e: e.get('end', ''), reverse=True)
                                fiscal_year = annual[0].get('end')
                    break

    # Derive Free Cash Flow = Operating CF - CapEx
    ocf   = result['cashflow'].get('Operating Cash Flow')
    capex = result['cashflow'].get('Capital Expenditure')
    if ocf is not None and capex is not None:
        result['cashflow']['Free Cash Flow'] = ocf - abs(capex)

    # Derive common key metrics
    km  = result['key_metrics']
    inc = result['income_statement']
    bal = result['balance_sheet']
    net_income = inc.get('Net Income')
    equity     = bal.get('Total Stockholder Equity')
    cur_assets = bal.get('Current Assets')
    cur_liab   = bal.get('Current Liabilities')
    debt       = bal.get('Long Term Debt')
    total_assets = bal.get('Total Assets')

    if net_income is not None and equity and equity != 0:
        km['roe'] = round(net_income / equity, 4)
    if net_income is not None and total_assets and total_assets != 0:
        km['roa'] = round(net_income / total_assets, 4)
    if debt is not None and equity and equity != 0:
        km['debt_to_equity'] = round(debt / equity, 4)
    if cur_assets is not None and cur_liab and cur_liab != 0:
        km['current_ratio'] = round(cur_assets / cur_liab, 4)

    if not any(result[s] for s in ('income_statement', 'balance_sheet', 'cashflow')):
        print(f"[SEC] No usable data extracted for {ticker}")
        return None

    print(f"[SEC] Successfully fetched data for {ticker} (fiscal year: {fiscal_year})")
    return {
        'income_statement': result['income_statement'],
        'balance_sheet':    result['balance_sheet'],
        'cashflow':         result['cashflow'],
        'key_metrics':      km,
        'fiscal_year':      fiscal_year or '',
        'currency':         'USD',
        'data_confidence':  'high',
    }


# ---------------------------------------------------------------------------
# Bedrock / Claude helpers
# ---------------------------------------------------------------------------

def _call_bedrock_claude(prompt: str, max_tokens: int = 2000) -> str:
    """Call Claude via AWS Bedrock and return the text response."""
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    response = bedrock.invoke_model(
        modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'temperature': 0,
            'messages': [{'role': 'user', 'content': prompt}]
        })
    )
    body = json.loads(response['body'].read())
    return body['content'][0]['text']


def _load_cached_financial_data(ticker: str, max_age_days: int = 90) -> dict | None:
    """
    Load AI-fetched financial data from DynamoDB if it's recent enough.
    Returns data in the same format as get_financial_data_with_ai, or None if
    no usable cache exists.
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table(MANUAL_DATA_TABLE)
        item = table.get_item(Key={'ticker': ticker}).get('Item')
        if not item or not item.get('has_data'):
            return None

        updated_at = item.get('updatedAt', '')
        if updated_at:
            age = datetime.now() - datetime.fromisoformat(updated_at)
            if age.days > max_age_days:
                return None

        fin = item.get('financial_data', {})

        def _latest(section: dict) -> dict:
            """Return the most recent period's data, converting Decimals to float."""
            if not section:
                return {}
            period = sorted(section.keys(), reverse=True)[0]
            return {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in section[period].items()
            }

        inc = _latest(fin.get('income_statement', {}))
        bal = _latest(fin.get('balance_sheet', {}))
        cf  = _latest(fin.get('cashflow', {}))
        km  = {
            k: float(v) if isinstance(v, Decimal) else v
            for k, v in fin.get('key_metrics', {}).get('latest', {}).items()
        }

        if not any([inc, bal, cf, km]):
            return None

        is_periods = list(fin.get('income_statement', {}).keys())
        fiscal_year = sorted(is_periods, reverse=True)[0] if is_periods else ''

        return {
            'income_statement': inc,
            'balance_sheet':    bal,
            'cashflow':         cf,
            'key_metrics':      km,
            'fiscal_year':      fiscal_year,
            'currency':         'USD',
            'data_confidence':  'high',
        }
    except Exception as e:
        print(f"[Cache] Could not load stored data for {ticker}: {e}")
        return None


def _extract_json(text: str) -> dict:
    """Extract and parse the first JSON object from an LLM response."""
    import re
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    # Try direct parse first (ideal path — model followed instructions)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back: extract between first { and last }
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    return {}


def get_financial_data_with_ai(ticker: str, company_name: str) -> dict:
    """
    Use Claude (via AWS Bedrock) to retrieve the most recent known annual
    financial data for a stock.  Returns a dict with keys:
        income_statement, balance_sheet, cashflow, key_metrics,
        fiscal_year, currency, data_confidence
    Returns {} (or {'error': ...}) on failure.
    """
    prompt = f"""You are a financial data provider with access to public company filings.
Return the most recent annual financial data you know about for {company_name} ({ticker}).

RULES:
- Use actual absolute numbers (not thousands/millions notation).
  Example: 394328000000 not 394,328 or 394.3B.
- Use null for any metric you are not confident about.
- Do NOT fabricate numbers. If you genuinely don't know a value, use null.
- For JSE/South African companies amounts should be in ZAR cents if the stock trades in cents,
  otherwise in ZAR rands. Indicate the currency in the "currency" field.

Return ONLY the following JSON object (no explanation, no markdown):
{{
  "income_statement": {{
    "Total Revenue": <number or null>,
    "Gross Profit": <number or null>,
    "Operating Income": <number or null>,
    "Net Income": <number or null>,
    "Basic EPS": <number or null>,
    "Diluted EPS": <number or null>
  }},
  "balance_sheet": {{
    "Total Assets": <number or null>,
    "Current Assets": <number or null>,
    "Cash And Cash Equivalents": <number or null>,
    "Total Liabilities Net Minority Interest": <number or null>,
    "Current Liabilities": <number or null>,
    "Long Term Debt": <number or null>,
    "Total Stockholder Equity": <number or null>,
    "Retained Earnings": <number or null>
  }},
  "cashflow": {{
    "Operating Cash Flow": <number or null>,
    "Free Cash Flow": <number or null>,
    "Capital Expenditure": <number or null>,
    "Common Stock Dividends Paid": <number or null>
  }},
  "key_metrics": {{
    "shares_outstanding": <number of shares (not millions) or null>,
    "pe_ratio": <number or null>,
    "pb_ratio": <number or null>,
    "debt_to_equity": <number or null>,
    "current_ratio": <number or null>,
    "roe": <decimal e.g. 0.15 for 15%, or null>,
    "roa": <decimal or null>
  }},
  "fiscal_year": "<YYYY-MM-DD of most recent fiscal year end>",
  "currency": "<ISO currency code e.g. USD, ZAR, GBP>",
  "data_confidence": "<high|medium|low>"
}}"""
    try:
        text = _call_bedrock_claude(prompt, max_tokens=2000)
        return _extract_json(text)
    except Exception as e:
        print(f"[Bedrock] ERROR {type(e).__name__}: {e}")
        return {'error': str(e)}


# ---------------------------------------------------------------------------
# Individual valuation model functions
# ---------------------------------------------------------------------------

def _safe(value, default=None):
    """Return value if it is a non-zero number, else default."""
    if value is None:
        return default
    try:
        v = float(value)
        return v if v != 0 else default
    except (TypeError, ValueError):
        return default


def run_dcf(fcf, shares, growth_rate=0.05, discount_rate=0.10,
            terminal_growth=0.03, years=5):
    """DCF fair value per share. Returns None if inputs insufficient."""
    fcf = _safe(fcf)
    shares = _safe(shares)
    if fcf is None or shares is None or shares <= 0:
        return None
    try:
        pv_sum = sum(
            fcf * ((1 + growth_rate) ** y) / ((1 + discount_rate) ** y)
            for y in range(1, years + 1)
        )
        terminal_cf = fcf * ((1 + growth_rate) ** years) * (1 + terminal_growth)
        terminal_pv = terminal_cf / (
            (discount_rate - terminal_growth) * ((1 + discount_rate) ** years)
        )
        return (pv_sum + terminal_pv) / shares
    except Exception:
        return None


def run_pe(eps, industry_pe=15.0):
    """P/E fair value per share."""
    eps = _safe(eps)
    if eps is None or eps <= 0:
        return None
    return eps * industry_pe


def run_book_value(equity, shares):
    """Book value per share."""
    equity = _safe(equity)
    shares = _safe(shares)
    if equity is None or shares is None or shares <= 0:
        return None
    return equity / shares


def run_earnings_power(net_income, shares, required_return=0.10):
    """Earnings power value per share (Graham-style)."""
    net_income = _safe(net_income)
    shares = _safe(shares)
    if net_income is None or shares is None or shares <= 0 or net_income <= 0:
        return None
    eps = net_income / shares
    return eps / required_return


def weighted_fair_value(model_results):
    """
    Weighted average of model results.
    model_results: list of (value, weight) tuples. None values are skipped.
    """
    valid = [(v, w) for v, w in model_results if v is not None and v > 0]
    if not valid:
        return None
    total_weight = sum(w for _, w in valid)
    if total_weight <= 0:
        return None
    return sum(v * w for v, w in valid) / total_weight


# ---------------------------------------------------------------------------
# POST endpoint handlers (unchanged)
# ---------------------------------------------------------------------------

def calculate_dcf_valuation(ticker: str, data: dict) -> dict:
    """Calculate DCF valuation for a stock (POST endpoint)"""
    try:
        free_cash_flow = data.get('freeCashFlow', 0)
        growth_rate = data.get('growthRate', 0.05)
        discount_rate = data.get('discountRate', 0.10)
        terminal_growth = data.get('terminalGrowth', 0.03)
        years = data.get('years', 5)
        shares_outstanding = data.get('sharesOutstanding', 1)

        cash_flows = []
        for year in range(1, years + 1):
            cf = free_cash_flow * ((1 + growth_rate) ** year)
            pv = cf / ((1 + discount_rate) ** year)
            cash_flows.append({
                'year': year,
                'cash_flow': round(cf, 2),
                'present_value': round(pv, 2)
            })

        terminal_cf = cash_flows[-1]['cash_flow'] * (1 + terminal_growth)
        terminal_value = terminal_cf / (discount_rate - terminal_growth)
        terminal_pv = terminal_value / ((1 + discount_rate) ** years)

        pv_sum = sum(cf['present_value'] for cf in cash_flows)
        enterprise_value = pv_sum + terminal_pv
        fair_value = enterprise_value / shares_outstanding if shares_outstanding > 0 else 0

        return {
            'statusCode': 200,
            'body': json.dumps({
                'ticker': ticker,
                'method': 'DCF',
                'fair_value': round(fair_value, 2),
                'enterprise_value': round(enterprise_value, 2),
                'cash_flows': cash_flows,
                'terminal_value': round(terminal_value, 2),
                'terminal_pv': round(terminal_pv, 2),
                'assumptions': {
                    'growth_rate': growth_rate,
                    'discount_rate': discount_rate,
                    'terminal_growth': terminal_growth,
                    'years': years
                }
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'DCF calculation failed: {str(e)}'})
        }


def calculate_pe_valuation(ticker: str, data: dict) -> dict:
    """Calculate P/E based valuation (POST endpoint)"""
    try:
        earnings_per_share = data.get('eps', 0)
        industry_pe = data.get('industryPE', 15)
        fair_value = earnings_per_share * industry_pe
        return {
            'statusCode': 200,
            'body': json.dumps({
                'ticker': ticker,
                'method': 'P/E',
                'fair_value': round(fair_value, 2),
                'eps': earnings_per_share,
                'industry_pe': industry_pe
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'P/E calculation failed: {str(e)}'})
        }


def analyze_stock(ticker: str, event: dict) -> dict:
    """Perform comprehensive stock analysis (POST endpoint)"""
    try:
        body = json.loads(event.get('body', '{}'))
        analysis_type = body.get('type', 'dcf')
        data = body.get('data', {})

        if analysis_type == 'dcf':
            return calculate_dcf_valuation(ticker, data)
        elif analysis_type == 'pe':
            return calculate_pe_valuation(ticker, data)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Unknown analysis type: {analysis_type}'})
            }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Analysis failed: {str(e)}'})
        }


def get_analysis_presets() -> dict:
    """Get available analysis presets/models"""
    presets = [
        {
            'id': 'conservative',
            'name': 'Conservative',
            'description': 'Conservative growth assumptions',
            'defaults': {'growthRate': 0.03, 'discountRate': 0.12, 'terminalGrowth': 0.02}
        },
        {
            'id': 'moderate',
            'name': 'Moderate',
            'description': 'Balanced growth assumptions',
            'defaults': {'growthRate': 0.05, 'discountRate': 0.10, 'terminalGrowth': 0.03}
        },
        {
            'id': 'aggressive',
            'name': 'Aggressive',
            'description': 'Optimistic growth assumptions',
            'defaults': {'growthRate': 0.08, 'discountRate': 0.08, 'terminalGrowth': 0.04}
        }
    ]
    return {
        'statusCode': 200,
        'body': json.dumps({'presets': presets})
    }


# ---------------------------------------------------------------------------
# GET /api/analyze/{ticker} — AI-powered streaming analysis
# ---------------------------------------------------------------------------

def analyze_stock_get(ticker: str, stream: bool, params: dict) -> dict:
    """Handle GET /api/analyze/{ticker} — AI-driven analysis with SSE streaming."""

    progress_events = []

    def progress(step, total, task):
        return 'data: ' + json.dumps(
            {'type': 'progress', 'step': step, 'total': total, 'task': task}
        )

    total_steps = 7

    # ------------------------------------------------------------------
    # Step 1: Fetch live stock price
    # ------------------------------------------------------------------
    progress_events.append(progress(1, total_steps, 'Fetching live stock price...'))

    current_price = 0
    company_name = f'{ticker} Corporation'
    currency = 'USD'
    try:
        lambda_client = boto3.client('lambda', region_name='eu-west-1')
        stock_data_lambda = os.getenv('STOCK_DATA_LAMBDA', 'stock-analysis-stock-data')
        payload = {
            'path': f'/api/ticker/{ticker}',
            'httpMethod': 'GET',
            'queryStringParameters': {},
            'headers': {}
        }
        resp = lambda_client.invoke(
            FunctionName=stock_data_lambda,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        stock_body = json.loads(
            json.loads(resp['Payload'].read()).get('body', '{}')
        )
        current_price = stock_body.get('currentPrice') or stock_body.get('price') or 0
        company_name = (
            stock_body.get('companyName') or stock_body.get('name') or company_name
        )
        currency = stock_body.get('currency', 'USD')
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Step 2: Retrieve financial data (cache → SEC EDGAR → Claude AI)
    # force_refresh=true bypasses the cache and always fetches the latest
    # ------------------------------------------------------------------
    force_refresh = str(params.get('force_refresh', 'false')).lower() == 'true'

    fin = None if force_refresh else _load_cached_financial_data(ticker)
    from_cache = fin is not None

    if from_cache:
        progress_events.append(progress(2, total_steps, 'Loading stored financial data...'))
    else:
        # Try SEC EDGAR first for US-listed stocks (official filings, always current)
        sec_fin = get_financial_data_from_sec(ticker)
        if sec_fin:
            progress_events.append(progress(2, total_steps, 'Fetching latest SEC EDGAR filings...'))
            fin = sec_fin
        else:
            # Fallback: Claude AI (handles non-US stocks and SEC failures)
            progress_events.append(progress(2, total_steps, 'Retrieving financial data with AI...'))
            fin = get_financial_data_with_ai(ticker, company_name)

    ai_error = fin.get('error')
    data_confidence = fin.get('data_confidence', 'low') if not ai_error else 'none'
    fiscal_year = fin.get('fiscal_year', '')

    inc = fin.get('income_statement', {}) or {}
    bal = fin.get('balance_sheet', {}) or {}
    cf  = fin.get('cashflow', {}) or {}
    km  = fin.get('key_metrics', {}) or {}

    # Persist AI-fetched data only when freshly retrieved (not from cache)
    if not from_cache and not ai_error and any([inc, bal, cf, km]):
        _save_ai_financial_data(ticker, inc, bal, cf, km, fiscal_year)

    shares = _safe(km.get('shares_outstanding'))

    # ------------------------------------------------------------------
    # Step 3: DCF valuation
    # ------------------------------------------------------------------
    progress_events.append(progress(3, total_steps, 'Running DCF valuation...'))

    dcf_value = run_dcf(
        fcf=cf.get('Free Cash Flow'),
        shares=shares,
        growth_rate=0.05,
        discount_rate=0.10,
        terminal_growth=0.03,
        years=5
    )
    # If no FCF, try Operating Cash Flow minus Capital Expenditure
    if dcf_value is None:
        ocf = _safe(cf.get('Operating Cash Flow'))
        capex = _safe(cf.get('Capital Expenditure'))
        if ocf is not None:
            implied_fcf = ocf - (abs(capex) if capex is not None else 0)
            dcf_value = run_dcf(
                fcf=implied_fcf, shares=shares,
                growth_rate=0.05, discount_rate=0.10,
                terminal_growth=0.03, years=5
            )

    # ------------------------------------------------------------------
    # Step 4: P/E valuation
    # ------------------------------------------------------------------
    progress_events.append(progress(4, total_steps, 'Running P/E valuation...'))

    eps = _safe(inc.get('Diluted EPS') or inc.get('Basic EPS'))
    # If EPS not given directly, derive from Net Income / shares
    if eps is None:
        net_income = _safe(inc.get('Net Income'))
        if net_income and shares:
            eps = net_income / shares
    industry_pe = _safe(km.get('pe_ratio'), default=15.0)
    pe_value = run_pe(eps, industry_pe)

    # ------------------------------------------------------------------
    # Step 5: Asset-based valuation (book value)
    # ------------------------------------------------------------------
    progress_events.append(progress(5, total_steps, 'Running asset-based valuation...'))

    book_value = run_book_value(
        equity=bal.get('Total Stockholder Equity'),
        shares=shares
    )
    earnings_power = run_earnings_power(
        net_income=inc.get('Net Income'),
        shares=shares
    )

    # ------------------------------------------------------------------
    # Step 6: Weighted fair value
    # ------------------------------------------------------------------
    progress_events.append(progress(6, total_steps, 'Calculating weighted fair value...'))

    # Weights: DCF=40%, P/E=30%, Earnings Power=20%, Book Value=10%
    fair_value = weighted_fair_value([
        (dcf_value, 0.40),
        (pe_value, 0.30),
        (earnings_power, 0.20),
        (book_value, 0.10),
    ])

    # Fallback: if AI data insufficient, use simple price-based estimate
    if fair_value is None and current_price:
        fair_value = round(current_price * 1.1, 2)  # 10% premium as placeholder

    # Round values
    if fair_value is not None:
        fair_value = round(fair_value, 2)
    dcf_rounded    = round(dcf_value, 2)    if dcf_value    is not None else None
    pe_rounded     = round(pe_value, 2)     if pe_value     is not None else None
    bv_rounded     = round(book_value, 2)   if book_value   is not None else None
    ep_rounded     = round(earnings_power, 2) if earnings_power is not None else None

    # ------------------------------------------------------------------
    # Step 7: Recommendation
    # ------------------------------------------------------------------
    progress_events.append(progress(7, total_steps, 'Generating recommendation...'))

    margin_of_safety = None
    upside = None
    if fair_value and current_price:
        margin_of_safety = round((fair_value - current_price) / fair_value * 100, 1)
        upside = round((fair_value - current_price) / current_price * 100, 1)

    if margin_of_safety is not None:
        if margin_of_safety > 25:
            recommendation = 'Strong Buy'
        elif margin_of_safety > 10:
            recommendation = 'Buy'
        elif margin_of_safety > -10:
            recommendation = 'Hold'
        elif margin_of_safety > -25:
            recommendation = 'Reduce'
        else:
            recommendation = 'Avoid'
    else:
        recommendation = 'Hold'

    # Build reasoning string
    models_used = []
    if dcf_rounded is not None:
        models_used.append(f'DCF ({currency} {dcf_rounded:,.2f})')
    if pe_rounded is not None:
        models_used.append(f'P/E ({currency} {pe_rounded:,.2f})')
    if ep_rounded is not None:
        models_used.append(f'Earnings Power ({currency} {ep_rounded:,.2f})')
    if bv_rounded is not None:
        models_used.append(f'Book Value ({currency} {bv_rounded:,.2f})')

    if models_used:
        reasoning = (
            f'Weighted fair value of {currency} {fair_value:,.2f} based on '
            f'{len(models_used)} model(s): {", ".join(models_used)}. '
            f'Financial data sourced via AI (confidence: {data_confidence}'
            + (f', fiscal year: {fiscal_year}' if fiscal_year else '') + ').'
        )
    else:
        reasoning = (
            f'Insufficient financial data retrieved by AI (confidence: {data_confidence}). '
            'Fair value estimated from live price only. Upload financial statements or '
            'use manual data entry for a full analysis.'
        )

    # Financial health indicators from AI data
    health_metrics = {}
    if _safe(km.get('current_ratio')):
        health_metrics['current_ratio'] = km['current_ratio']
    if _safe(km.get('debt_to_equity')):
        health_metrics['debt_to_equity'] = km['debt_to_equity']
    if _safe(km.get('roe')):
        health_metrics['roe'] = km['roe']
    if _safe(km.get('roa')):
        health_metrics['roa'] = km['roa']

    # Build full analysis response
    analysis = {
        'ticker': ticker,
        'companyName': company_name,
        'currentPrice': current_price,
        'currency': currency,
        'fairValue': fair_value,
        'marginOfSafety': margin_of_safety,
        'upsidePotential': upside,
        'priceToIntrinsicValue': (
            round(current_price / fair_value, 2) if fair_value and current_price else None
        ),
        'recommendation': recommendation,
        'recommendationReasoning': reasoning,
        'valuation': {
            'dcf': dcf_rounded,
            'peValue': pe_rounded,
            'bookValue': bv_rounded,
            'earningsPower': ep_rounded,
            'weightedAverage': fair_value
        },
        'financialHealth': {
            'score': None,
            'metrics': health_metrics
        },
        'businessQuality': {
            'score': None,
            'moatIndicators': [],
            'competitivePosition': ''
        },
        'aiFinancialData': {
            'fiscalYear': fiscal_year,
            'currency': fin.get('currency', currency),
            'confidence': data_confidence,
            'incomeStatement': inc if inc else None,
            'balanceSheet': bal if bal else None,
            'cashflow': cf if cf else None,
            'keyMetrics': km if km else None,
        },
        'timestamp': datetime.now().isoformat(),
        'dataSource': 'ai-bedrock-claude'
    }

    # Persist the analysis result so the ticker page can display it on load
    # without requiring the user to click Run Analysis again.
    # Store only summary fields (not aiFinancialData) to stay well under DynamoDB's
    # 400 KB item-size limit — the full financial statements are already in financial_data.
    try:
        pe_from_km = None
        if km:
            pe_from_km = km.get('pe_ratio') or km.get('pe') or km.get('price_to_earnings')
        analysis_summary = {
            'ticker': analysis['ticker'],
            'companyName': analysis['companyName'],
            'currentPrice': analysis['currentPrice'],
            'currency': analysis['currency'],
            'fairValue': analysis['fairValue'],
            'marginOfSafety': analysis['marginOfSafety'],
            'upsidePotential': analysis['upsidePotential'],
            'priceToIntrinsicValue': analysis['priceToIntrinsicValue'],
            'recommendation': analysis['recommendation'],
            'recommendationReasoning': analysis['recommendationReasoning'],
            'valuation': analysis['valuation'],
            'pe_ratio': float(pe_from_km) if pe_from_km is not None else None,
            'timestamp': analysis['timestamp'],
            'dataSource': analysis['dataSource'],
        }
        dynamodb_res = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb_res.Table(MANUAL_DATA_TABLE)
        table.update_item(
            Key={'ticker': ticker},
            UpdateExpression='SET latest_analysis = :a, updatedAt = :t',
            ExpressionAttributeValues={
                ':a': _convert_for_dynamo(analysis_summary),
                ':t': datetime.now().isoformat(),
            }
        )
    except Exception as exc:
        print(f"[WARN] Could not cache analysis for {ticker}: {exc}")

    if stream:
        sse_lines = progress_events + [
            'data: ' + json.dumps({'type': 'complete', 'data': analysis}),
        ]
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/event-stream'},
            'body': '\n'.join(sse_lines) + '\n'
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps(analysis)
        }


# ---------------------------------------------------------------------------
# Batch analyze (watchlist bulk analysis)
# ---------------------------------------------------------------------------

def handle_batch_analyze(event):
    """Handle POST /api/batch-analyze: run analysis for multiple tickers."""
    try:
        body = event.get('body') or '{}'
        if isinstance(body, str):
            body = json.loads(body)
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON body'})
        }
    tickers = body.get('tickers') or []
    if not tickers or not isinstance(tickers, list):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'tickers list required'})
        }
    # Limit per invocation to avoid timeout (60s)
    max_tickers = 10
    tickers = [str(t).strip().upper() for t in tickers[:max_tickers] if t]
    successful = 0
    failed = 0
    for ticker in tickers:
        try:
            result = analyze_stock_get(ticker, stream=False, params={})
            if result.get('statusCode') == 200:
                successful += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    summary = {'successful': successful, 'failed': failed}
    message = f"Batch analysis completed. Processed {successful} tickers successfully, {failed} failed."
    return {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'summary': summary,
            'message': message
        })
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """AWS Lambda handler for stock analysis"""

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Content-Type': 'application/json'
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}

    path = event.get('path', '')
    method = event.get('httpMethod', 'POST')

    try:
        if '/api/analysis/' in path and method == 'POST':
            ticker = path.split('/api/analysis/')[-1]
            result = analyze_stock(ticker, event)

        elif '/api/analyze/' in path and method == 'GET':
            ticker = path.split('/api/analyze/')[-1].split('?')[0]
            query_params = event.get('queryStringParameters') or {}
            stream = query_params.get('stream', 'false').lower() == 'true'
            result = analyze_stock_get(ticker, stream, query_params)

        elif '/api/analysis-presets' in path and method == 'GET':
            result = get_analysis_presets()

        elif '/api/batch-analyze' in path and method == 'POST':
            result = handle_batch_analyze(event)

        else:
            result = {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }

        result['headers'] = headers
        return result

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
