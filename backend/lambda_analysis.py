"""
Analysis Lambda - Handles stock analysis and valuation calculations
Uses Claude AI via Bedrock to fetch real financial data for each stock
"""
import json
import os
import base64
import uuid
import boto3
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _has_real_values(d: dict) -> bool:
    """Return True only if the dict contains at least one non-None value."""
    return any(v is not None for v in d.values())


def _cleanup_empty_financial_periods(ticker: str) -> None:
    """
    Remove period stubs whose data is empty (all-null fields stripped by DynamoDB).
    Called on every fresh analysis so leftover empty stubs are scrubbed from the UI.
    Non-fatal.
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table(MANUAL_DATA_TABLE)
        item = table.get_item(Key={'ticker': ticker}).get('Item')
        if not item:
            return

        fin = item.get('financial_data', {})
        meta = item.get('metadata', {})
        changed = False

        for section_key in list(fin.keys()):
            section = fin[section_key]
            if not isinstance(section, dict):
                continue
            empty_periods = [
                period for period, data in section.items()
                if not isinstance(data, dict) or not data
            ]
            for period in empty_periods:
                del fin[section_key][period]
                changed = True
            if not fin[section_key]:
                del fin[section_key]
                meta.pop(section_key, None)
                changed = True

        if not changed:
            return

        table.update_item(
            Key={'ticker': ticker},
            UpdateExpression='SET financial_data = :fd, metadata = :md, has_data = :hd',
            ExpressionAttributeValues={
                ':fd': fin,
                ':md': meta,
                ':hd': bool(fin),
            }
        )
        print(f"[Cleanup] Removed empty financial periods for {ticker}")
    except Exception as exc:
        print(f"[WARN] Could not cleanup empty periods for {ticker}: {exc}")


def _merge_financial_sections(existing: dict, new: dict) -> dict:
    """
    Section-level merge: if new data provides a section (non-empty), replace the entire
    existing section with it. If new data does not provide a section, keep the existing
    (e.g. PDF-sourced) section intact. No field-level mixing within a section.
    """
    merged = dict(existing)
    for sk, sv in new.items():
        # Only replace if the new section has actual data
        if isinstance(sv, dict) and sv:
            merged[sk] = sv
        elif not isinstance(sv, dict):
            merged[sk] = sv
    return merged


def _save_ai_financial_data(ticker: str, inc: dict, bal: dict, cf: dict, km: dict,
                             fiscal_year: str, fin_currency: str = 'USD',
                             source: str = 'ai_bedrock',
                             section_sources: dict | None = None) -> None:
    """
    Persist fetched financial data to DynamoDB so it appears in the
    'Stored Financial Data' panel on the ticker page.
    Merges with any existing data field-by-field so that PDF-sourced values
    are never erased by a subsequent analysis that couldn't find those fields.
    section_sources: optional per-section source override, e.g.
      {'income_statement': 'yahoo_finance', 'balance_sheet': 'ai_bedrock'}
    Only saves sections that contain at least one non-None value.
    Non-fatal — a failure here does not block the analysis response.
    """
    try:
        period = fiscal_year or f"{datetime.now().year - 1}-12-31"
        now = datetime.now().isoformat()
        section_sources = section_sources or {}

        new_financial_data: dict = {}
        new_metadata: dict = {}

        for section_key, data in [
            ('income_statement', inc),
            ('balance_sheet', bal),
            ('cashflow', cf),
        ]:
            if data and _has_real_values(data):
                new_financial_data[section_key] = {period: data}
                new_metadata[section_key] = {
                    'last_updated': now,
                    'source': section_sources.get(section_key, source),
                    'period_count': 1,
                }

        if km and _has_real_values(km):
            new_financial_data['key_metrics'] = {'latest': km}
            new_metadata['key_metrics'] = {
                'last_updated': now,
                'source': section_sources.get('key_metrics', source),
                'period_count': 1,
            }

        if not new_financial_data:
            print(f"[AI Data] No usable financial data to persist for {ticker} — all fields null")
            return

        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        table = dynamodb.Table(MANUAL_DATA_TABLE)

        # Load existing item so we can merge rather than overwrite
        existing_item = table.get_item(Key={'ticker': ticker}).get('Item') or {}
        existing_fin = existing_item.get('financial_data') or {}
        existing_meta = existing_item.get('metadata') or {}

        # Merge financial data field-by-field
        merged_fin = _merge_financial_sections(existing_fin, new_financial_data)

        # Merge metadata: update entries for sections we wrote new data into
        merged_meta = dict(existing_meta)
        for sk, mv in new_metadata.items():
            merged_meta[sk] = mv

        # Build new item preserving any extra fields (pdf_status, pdf_s3_key, etc.)
        preserved = {k: v for k, v in existing_item.items()
                     if k not in ('ticker', 'updatedAt', 'financial_data', 'metadata',
                                  'financial_currency', 'has_data')}
        item = _convert_for_dynamo({
            **preserved,
            'ticker': ticker,
            'updatedAt': now,
            'financial_data': merged_fin,
            'metadata': merged_meta,
            'financial_currency': fin_currency,
            'has_data': True,
        })

        table.put_item(Item=item)
        print(f"[AI Data] Saved/merged financial data for {ticker} (source={source})")
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
# Yahoo Finance quoteSummary — financial statements for non-US stocks
# ---------------------------------------------------------------------------

def _yahoo_symbol(ticker: str) -> str:
    """Convert our ticker format to Yahoo Finance symbol format."""
    if ticker.upper().endswith('.XJSE'):
        return ticker[:-5] + '.JO'
    return ticker


def _yahoo_get_session():
    """
    Establish a Yahoo Finance session and return (opener, crumb).
    The Yahoo Finance v10 quoteSummary API requires a valid session cookie
    and crumb since 2023; without them it returns 401 Unauthorized.
    Returns (None, None) on failure.
    """
    from urllib.request import Request, HTTPCookieProcessor, build_opener
    from http.cookiejar import CookieJar

    cj = CookieJar()
    opener = build_opener(HTTPCookieProcessor(cj))
    ua = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    # Establish a session — fc.yahoo.com is lightweight compared to the main page
    for seed_url in ('https://fc.yahoo.com', 'https://finance.yahoo.com/'):
        try:
            opener.open(Request(seed_url, headers={'User-Agent': ua}), timeout=8)
            break
        except Exception:
            continue

    # Fetch the crumb that authenticates subsequent API calls
    try:
        with opener.open(
            Request('https://query2.finance.yahoo.com/v1/test/getcrumb',
                    headers={'User-Agent': ua}),
            timeout=8
        ) as resp:
            crumb = resp.read().decode('utf-8').strip()
            if crumb and len(crumb) >= 3:
                return opener, crumb
    except Exception as e:
        print(f"[Yahoo Financials] Crumb fetch failed: {e}")

    return None, None


def get_financial_data_from_yahoo(ticker: str) -> dict | None:
    """
    Fetch the most recent annual financial statements from Yahoo Finance's
    quoteSummary API using stdlib urllib only (no yfinance library required).
    Returns data in the same format as get_financial_data_from_sec, or None on failure.
    Used for non-US stocks where SEC EDGAR has no data (e.g. JSE .XJSE, LSE .L).
    """
    import gzip as _gzip
    from urllib.request import Request

    symbol = _yahoo_symbol(ticker)

    opener, crumb = _yahoo_get_session()
    if opener is None:
        print(f"[Yahoo Financials] Could not establish session for {symbol}")
        return None

    modules = (
        'incomeStatementHistory,balanceSheetHistory,'
        'cashflowStatementHistory,defaultKeyStatistics,financialData'
    )
    url = (
        f'https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}'
        f'?modules={modules}&crumb={crumb}'
    )

    try:
        req = Request(url, headers={
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
        })
        with opener.open(req, timeout=15) as resp:
            raw = resp.read()
            if resp.info().get('Content-Encoding') == 'gzip':
                raw = _gzip.decompress(raw)
            data = json.loads(raw.decode('utf-8'))
    except Exception as e:
        print(f"[Yahoo Financials] HTTP error for {symbol}: {e}")
        return None

    result_list = (data.get('quoteSummary') or {}).get('result') or []
    if not result_list:
        err = (data.get('quoteSummary') or {}).get('error')
        print(f"[Yahoo Financials] No result for {symbol}: {err}")
        return None

    r = result_list[0]

    def _raw(obj) -> float | None:
        """Extract numeric value from Yahoo's {raw: ..., fmt: ...} wrapper."""
        if obj is None:
            return None
        if isinstance(obj, dict):
            v = obj.get('raw')
            return float(v) if v is not None else None
        try:
            return float(obj)
        except (TypeError, ValueError):
            return None

    # Income statement — most recent annual period
    inc_list = (r.get('incomeStatementHistory') or {}).get('incomeStatementHistory') or []
    i = inc_list[0] if inc_list else {}
    fiscal_year = (i.get('endDate') or {}).get('fmt', '')
    inc = {
        'Total Revenue':    _raw(i.get('totalRevenue')),
        'Gross Profit':     _raw(i.get('grossProfit')),
        'Operating Income': _raw(i.get('operatingIncome') or i.get('ebit')),
        'Net Income':       _raw(i.get('netIncome')),
        'Basic EPS':        _raw(i.get('basicEPS')),
        'Diluted EPS':      _raw(i.get('dilutedEPS')),
    }

    # Balance sheet — most recent annual period
    bal_list = (r.get('balanceSheetHistory') or {}).get('balanceSheetStatements') or []
    b = bal_list[0] if bal_list else {}
    bal = {
        'Total Assets':     _raw(b.get('totalAssets')),
        'Current Assets':   _raw(b.get('totalCurrentAssets')),
        'Cash And Cash Equivalents': _raw(b.get('cash') or b.get('cashAndCashEquivalents')),
        'Total Liabilities Net Minority Interest': _raw(b.get('totalLiab')),
        'Current Liabilities': _raw(b.get('totalCurrentLiabilities')),
        'Long Term Debt':   _raw(b.get('longTermDebt')),
        'Total Stockholder Equity': _raw(b.get('totalStockholderEquity')),
        'Retained Earnings': _raw(b.get('retainedEarnings')),
    }

    # Cash flow — most recent annual period
    cf_list = (r.get('cashflowStatementHistory') or {}).get('cashflowStatements') or []
    c = cf_list[0] if cf_list else {}
    cf = {
        'Operating Cash Flow': _raw(c.get('totalCashFromOperatingActivities')),
        'Free Cash Flow':      _raw(c.get('freeCashFlow')),
        'Capital Expenditure': _raw(c.get('capitalExpenditures')),
        'Common Stock Dividends Paid': _raw(c.get('dividendsPaid')),
    }
    # Derive FCF if not provided directly
    if cf['Free Cash Flow'] is None:
        ocf   = cf.get('Operating Cash Flow')
        capex = cf.get('Capital Expenditure')
        if ocf is not None and capex is not None:
            cf['Free Cash Flow'] = ocf - abs(capex)

    # Key metrics from defaultKeyStatistics + financialData
    ks = r.get('defaultKeyStatistics') or {}
    fd = r.get('financialData') or {}
    km = {
        'shares_outstanding': _raw(ks.get('sharesOutstanding')),
        'pe_ratio':           _raw(ks.get('trailingPE') or ks.get('forwardPE')),
        'pb_ratio':           _raw(ks.get('priceToBook')),
        'ps_ratio':           _raw(ks.get('priceToSalesTrailing12Months')),
        'current_ratio':      _raw(fd.get('currentRatio')),
        'roe':                _raw(fd.get('returnOnEquity')),
        'roa':                _raw(fd.get('returnOnAssets')),
        'debt_to_equity':     None,
    }
    # Yahoo reports debt/equity as a percentage-style number (170 = 1.70×) — normalise
    de_raw = _raw(fd.get('debtToEquity'))
    if de_raw is not None:
        km['debt_to_equity'] = round(de_raw / 100, 4)

    # Derive any missing ratios from balance sheet / income statement
    net_income   = inc.get('Net Income')
    equity       = bal.get('Total Stockholder Equity')
    total_assets = bal.get('Total Assets')
    cur_assets   = bal.get('Current Assets')
    cur_liab     = bal.get('Current Liabilities')
    debt         = bal.get('Long Term Debt')
    if km['roe'] is None and net_income is not None and equity and equity != 0:
        km['roe'] = round(net_income / equity, 4)
    if km['roa'] is None and net_income is not None and total_assets and total_assets != 0:
        km['roa'] = round(net_income / total_assets, 4)
    if km['debt_to_equity'] is None and debt is not None and equity and equity != 0:
        km['debt_to_equity'] = round(debt / equity, 4)
    if km['current_ratio'] is None and cur_assets is not None and cur_liab and cur_liab != 0:
        km['current_ratio'] = round(cur_assets / cur_liab, 4)

    # Yahoo provides financialCurrency as a plain string in financialData
    fin_currency = fd.get('financialCurrency') or 'USD'

    if not any(_has_real_values(d) for d in [inc, bal, cf] if d):
        print(f"[Yahoo Financials] No usable data for {symbol}")
        return None

    print(f"[Yahoo Financials] Fetched data for {symbol} (FY: {fiscal_year}, currency: {fin_currency})")
    return {
        'income_statement': inc,
        'balance_sheet':    bal,
        'cashflow':         cf,
        'key_metrics':      km,
        'fiscal_year':      fiscal_year,
        'currency':         fin_currency,
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
            """Return the most recent period's data, converting Decimals to float.
            Sorts period keys by zero-padding each component so 'YYYY' < 'YYYY-MM-DD'
            and mixed formats compare correctly."""
            if not section:
                return {}
            def _sort_key(p: str) -> str:
                # Pad each dash-separated part to 4 digits so "2024" < "2024-03-31"
                return '-'.join(part.zfill(4) for part in p.split('-'))
            period = sorted(section.keys(), key=_sort_key, reverse=True)[0]
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
            'currency':         item.get('financial_currency', 'USD'),
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


# ---------------------------------------------------------------------------
# Valuation preset weights (match frontend fallbackPresets in ticker/page.tsx)
# P/E weight = 1 - dcf - epv - asset
# ---------------------------------------------------------------------------
PRESET_WEIGHTS = {
    'default':            {'dcf': 0.40, 'pe': 0.30, 'epv': 0.20, 'asset': 0.10},
    'high_growth':        {'dcf': 0.60, 'pe': 0.15, 'epv': 0.20, 'asset': 0.05},
    'growth_company':     {'dcf': 0.50, 'pe': 0.25, 'epv': 0.15, 'asset': 0.10},
    'mature_company':     {'dcf': 0.35, 'pe': 0.35, 'epv': 0.20, 'asset': 0.10},
    'cyclical':           {'dcf': 0.25, 'pe': 0.25, 'epv': 0.35, 'asset': 0.15},
    'asset_heavy':        {'dcf': 0.20, 'pe': 0.10, 'epv': 0.25, 'asset': 0.45},
    'distressed_company': {'dcf': 0.10, 'pe': 0.05, 'epv': 0.15, 'asset': 0.70},
    'bank':               {'dcf': 0.20, 'pe': 0.30, 'epv': 0.35, 'asset': 0.15},
    'reit':               {'dcf': 0.30, 'pe': 0.10, 'epv': 0.15, 'asset': 0.45},
    'insurance':          {'dcf': 0.20, 'pe': 0.25, 'epv': 0.40, 'asset': 0.15},
    'utility':            {'dcf': 0.40, 'pe': 0.20, 'epv': 0.30, 'asset': 0.10},
    'technology':         {'dcf': 0.50, 'pe': 0.25, 'epv': 0.20, 'asset': 0.05},
    'healthcare':         {'dcf': 0.45, 'pe': 0.25, 'epv': 0.25, 'asset': 0.05},
    'retail':             {'dcf': 0.40, 'pe': 0.30, 'epv': 0.20, 'asset': 0.10},
    'energy':             {'dcf': 0.25, 'pe': 0.15, 'epv': 0.40, 'asset': 0.20},
}

PRESET_DESCRIPTIONS = {
    'high_growth':        'Technology startups, high-growth SaaS, biotech',
    'growth_company':     'Established growth companies, expanding businesses',
    'mature_company':     'Stable blue-chips, dividend payers',
    'technology':         'Software, internet, semiconductors',
    'healthcare':         'Pharma, biotech, medical devices, healthcare services',
    'retail':             'Retail stores, consumer goods, e-commerce',
    'utility':            'Electric, water, gas utilities',
    'cyclical':           'Industrials, manufacturing, materials',
    'energy':             'Oil & gas, mining, energy exploration',
    'bank':               'Banks, financial services, credit institutions',
    'insurance':          'Insurance companies, reinsurance',
    'asset_heavy':        'Infrastructure, capital-intensive businesses',
    'reit':               'Real Estate Investment Trusts',
    'distressed_company': 'Companies in financial difficulty, turnaround situations',
    'default':            'General purpose, balanced approach',
}


def _recommend_preset(ticker: str, company_name: str, sector: str = '', industry: str = '') -> str:
    """Use Bedrock to recommend the most appropriate valuation preset for a company."""
    preset_list = '\n'.join(f'- {k}: {v}' for k, v in PRESET_DESCRIPTIONS.items())
    prompt = (
        f"You are a valuation analyst. Select the single most appropriate valuation preset for:\n"
        f"Company: {company_name} ({ticker})\n"
        f"Sector: {sector or 'Unknown'}\n"
        f"Industry: {industry or 'Unknown'}\n\n"
        f"Available presets:\n{preset_list}\n\n"
        f"Respond with ONLY the preset key (e.g. \"technology\", \"bank\"). Nothing else."
    )
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        body = json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 20,
            'messages': [{'role': 'user', 'content': prompt}]
        })
        response = bedrock.invoke_model(
            modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
            contentType='application/json',
            accept='application/json',
            body=body
        )
        raw = json.loads(response['body'].read())['content'][0]['text'].strip().lower()
        # Accept the key verbatim or with spaces→underscores
        preset = raw.replace(' ', '_')
        if preset in PRESET_WEIGHTS:
            print(f"[Preset] LLM recommended '{preset}' for {ticker}")
            return preset
        # Partial match fallback
        for key in PRESET_WEIGHTS:
            if key in preset or preset in key:
                print(f"[Preset] LLM partial match '{preset}' → '{key}' for {ticker}")
                return key
    except Exception as exc:
        print(f"[WARN] Preset recommendation failed for {ticker}: {exc}")
    return 'default'


def _generate_ai_commentary(
    ticker: str, company_name: str, sector: str, industry: str,
    current_price: float, currency: str,
    fair_value: float | None, margin_of_safety: float | None,
    recommendation: str | None, resolved_preset: str | None,
    inc: dict, bal: dict, cf: dict, km: dict,
) -> str:
    """
    Generate a plain-language AI commentary on the stock: what's driving the
    current price and whether buying is a good idea.  Returns a markdown string.
    """
    # Build a compact data summary for the prompt
    def _fmt(v, decimals=2, pct=False, prefix=''):
        if v is None or (isinstance(v, float) and not (v == v)):
            return 'N/A'
        s = f'{v:,.{decimals}f}'
        if pct:
            s += '%'
        return f'{prefix}{s}'

    rev   = inc.get('Total Revenue')
    ni    = inc.get('Net Income')
    ocf   = cf.get('Operating Cash Flow')
    fcf   = cf.get('Free Cash Flow')
    eq    = bal.get('Total Stockholder Equity')
    debt  = bal.get('Long Term Debt')
    cash  = bal.get('Cash And Cash Equivalents')
    roe   = km.get('roe')
    roa   = km.get('roa')
    d2e   = km.get('debt_to_equity')
    cr    = km.get('current_ratio')
    pe    = km.get('pe_ratio')
    eps   = inc.get('Diluted EPS') or inc.get('Basic EPS')

    def _scale(v):
        """Return human-readable scale (B/M) for large currency numbers."""
        if v is None:
            return 'N/A'
        abs_v = abs(v)
        if abs_v >= 1e9:
            return f'{currency} {v/1e9:,.2f}B'
        if abs_v >= 1e6:
            return f'{currency} {v/1e6:,.2f}M'
        return f'{currency} {v:,.2f}'

    mos_str = f'{margin_of_safety:+.1f}%' if margin_of_safety is not None else 'N/A'
    fv_str  = f'{currency} {fair_value:,.2f}' if fair_value else 'N/A'

    prompt = (
        f"You are an independent senior equity analyst reviewing {company_name} ({ticker}). "
        f"Reason from the raw financial data below to your own conclusion. "
        f"You have no prior bias — you give strong buy ratings when the data supports it just as readily as avoid ratings.\n\n"
        f"Write a concise investment commentary in 3 short paragraphs:\n"
        f"1. What the business does and what financial or sector factors drive the current "
        f"market price of {currency} {current_price:,.2f}.\n"
        f"2. Whether the stock appears undervalued or overvalued based on the fundamentals. "
        f"A DCF-based fair value estimate of {fv_str} (implied margin of safety: {mos_str}) is "
        f"provided as one reference point — assess it critically against the underlying numbers.\n"
        f"3. Your overall assessment — weigh both the positives and negatives equally, then state your conviction level.\n\n"
        f"Financial data:\n"
        f"- Sector: {sector or 'N/A'} | Industry: {industry or 'N/A'}\n"
        f"- Revenue: {_scale(rev)} | Net Income: {_scale(ni)}\n"
        f"- Operating CF: {_scale(ocf)} | Free CF: {_scale(fcf)}\n"
        f"- Equity: {_scale(eq)} | LT Debt: {_scale(debt)} | Cash: {_scale(cash)}\n"
        f"- ROE: {_fmt(None if roe is None else roe * 100, pct=True)} | "
        f"ROA: {_fmt(None if roa is None else roa * 100, pct=True)} | "
        f"D/E: {_fmt(d2e)} | Current ratio: {_fmt(cr)} | P/E: {_fmt(pe)} | EPS: {_fmt(eps, prefix=currency+' ')}\n\n"
        f"Write in plain English, 3 paragraphs, no bullet lists. "
        f"It is fine to disagree with the DCF estimate if the fundamentals justify it. "
        f"Do not fabricate specific news events — stick to the data provided.\n\n"
        f"Rating guidance (use the full spectrum based purely on the data):\n"
        f"  Strong Buy — compelling value, strong fundamentals, significant upside\n"
        f"  Buy        — attractively priced with solid fundamentals\n"
        f"  Hold       — fairly valued or mixed picture, no clear edge\n"
        f"  Reduce     — overvalued or fundamentals deteriorating\n"
        f"  Avoid      — significantly overvalued or materially weak fundamentals\n\n"
        f"After the 3 paragraphs, on a new line write exactly one of:\n"
        f"ANALYST RECOMMENDATION: Strong Buy\n"
        f"ANALYST RECOMMENDATION: Buy\n"
        f"ANALYST RECOMMENDATION: Hold\n"
        f"ANALYST RECOMMENDATION: Reduce\n"
        f"ANALYST RECOMMENDATION: Avoid"
    )
    try:
        text = _call_bedrock_claude(prompt, max_tokens=650)
        text = text.strip()
        # Extract structured AI recommendation from the final line
        ai_rec = None
        lines = text.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('ANALYST RECOMMENDATION:'):
                raw = stripped.replace('ANALYST RECOMMENDATION:', '').strip()
                if raw in ('Strong Buy', 'Buy', 'Hold', 'Reduce', 'Avoid'):
                    ai_rec = raw
                # Remove the tag line from the displayed commentary
                text = '\n'.join(lines[:i] + lines[i+1:]).strip()
                break
        return text, ai_rec
    except Exception as exc:
        print(f"[WARN] AI commentary failed for {ticker}: {exc}")
        return '', None


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


def _get_fx_scale(fin_currency: str, price_currency: str) -> float | None:
    """
    Return the multiplier to convert monetary values from fin_currency to
    price_currency so that per-share fair values and the live price are
    expressed in the same unit.

    Returns 1.0 if the currencies are the same.
    Returns None if the rate could not be determined (valuation will be skipped
    or flagged as unreliable).

    Sub-unit pseudo-currencies (ZAC = 1/100 ZAR, GBX = 1/100 GBP) are handled
    with a fixed ratio so no external lookup is needed.

    All other cross-currency pairs are resolved via the Frankfurter API (ECB
    daily rates, no key required, standard-library urllib only).
    """
    fc = (fin_currency or 'USD').upper()
    pc = (price_currency or 'USD').upper()

    if fc == pc:
        return 1.0

    # Sub-unit fixed ratios — no external lookup needed
    _SUB_UNIT = {
        ('ZAR', 'ZAC'): 100.0,
        ('ZAC', 'ZAR'): 0.01,
        ('GBP', 'GBX'): 100.0,
        ('GBX', 'GBP'): 0.01,
    }
    if (fc, pc) in _SUB_UNIT:
        return _SUB_UNIT[(fc, pc)]

    # Cross-currency sub-units (e.g. GBX financials vs USD price):
    # decompose into the parent currency, then apply the FX rate
    if fc == 'GBX':
        rate = _get_fx_scale('GBP', pc)
        return rate * 0.01 if rate is not None else None
    if pc == 'GBX':
        rate = _get_fx_scale(fc, 'GBP')
        return rate * 100 if rate is not None else None
    if fc == 'ZAC':
        rate = _get_fx_scale('ZAR', pc)
        return rate * 0.01 if rate is not None else None
    if pc == 'ZAC':
        rate = _get_fx_scale(fc, 'ZAR')
        return rate * 100 if rate is not None else None

    # Live rate: invoke the stock-data Lambda with the Yahoo Finance forex symbol
    # (e.g. JPYUSD=X for JPY→USD). The stock-data Lambda has yfinance/urllib and
    # handles Yahoo Finance's auth requirements. No external API dependency.
    try:
        lc = boto3.client('lambda', region_name='eu-west-1')
        fx_symbol = f'{fc}{pc}=X'
        payload = {
            'path': f'/api/ticker/{fx_symbol}',
            'httpMethod': 'GET',
            'queryStringParameters': {},
            'headers': {}
        }
        resp = lc.invoke(
            FunctionName=os.getenv('STOCK_DATA_LAMBDA', 'stock-analysis-stock-data'),
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        body = json.loads(json.loads(resp['Payload'].read()).get('body', '{}'))
        rate = body.get('currentPrice') or body.get('price')
        if rate and float(rate) > 0:
            print(f'[FX] {fc} → {pc}: {float(rate):.6f} (via {fx_symbol})')
            return float(rate)
    except Exception as e:
        print(f'[FX] Could not fetch {fc} → {pc} rate: {e}')

    return None


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

    total_steps = 8

    # ------------------------------------------------------------------
    # Step 1: Fetch live stock price
    # Private companies (PRIVATE# prefix) skip external APIs entirely and
    # use the price / metadata supplied by the caller.
    # ------------------------------------------------------------------
    is_private = ticker.startswith('PRIVATE#')
    current_price = 0
    company_name = f'{ticker} Corporation'
    currency = 'USD'
    sector = ''
    industry = ''

    if is_private:
        progress_events.append(progress(1, total_steps, 'Loading private company details...'))
        display_name = ticker[len('PRIVATE#'):]
        company_name = params.get('company_name', display_name) or display_name
        currency = params.get('currency', 'USD') or 'USD'
        sector = params.get('sector', '') or ''
        try:
            current_price = float(params.get('price_override', 0) or 0)
        except (TypeError, ValueError):
            current_price = 0
    else:
        progress_events.append(progress(1, total_steps, 'Fetching live stock price...'))
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
            sector   = stock_body.get('sector', '')
            industry = stock_body.get('industry', '')
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Resolve valuation weights: explicit preset > custom JSON > auto-LLM
    # ------------------------------------------------------------------
    requested_preset = (params.get('business_type') or '').strip().lower().replace(' ', '_')
    custom_weights_json = params.get('weights', '')

    resolved_preset = None  # will be set below

    if requested_preset and requested_preset != 'automatic' and requested_preset in PRESET_WEIGHTS:
        # Caller specified a known preset
        w = PRESET_WEIGHTS[requested_preset]
        resolved_preset = requested_preset
        print(f"[Preset] Using requested preset '{resolved_preset}' for {ticker}")
    elif custom_weights_json:
        # Caller passed raw JSON weights (legacy / manual config)
        try:
            cw = json.loads(custom_weights_json)
            w = {
                'dcf':   float(cw.get('dcf_weight', 0.40)),
                'pe':    float(cw.get('pe_weight',  0.30)),
                'epv':   float(cw.get('epv_weight', 0.20)),
                'asset': float(cw.get('asset_weight', 0.10)),
            }
            resolved_preset = requested_preset or None
        except Exception:
            w = PRESET_WEIGHTS['default']
            resolved_preset = 'default'
    else:
        # No preset specified or 'automatic' — ask LLM
        progress_events.append(progress(1, total_steps, 'Auto-selecting valuation preset...'))
        resolved_preset = _recommend_preset(ticker, company_name, sector, industry)
        w = PRESET_WEIGHTS.get(resolved_preset, PRESET_WEIGHTS['default'])

    # ------------------------------------------------------------------
    # Step 2: Retrieve financial data (cache → SEC EDGAR → Yahoo Finance → Claude AI)
    # force_refresh=true bypasses the cache and always fetches the latest
    # ------------------------------------------------------------------
    force_refresh = str(params.get('force_refresh', 'false')).lower() == 'true'

    fin = None if force_refresh else _load_cached_financial_data(ticker)
    from_cache = fin is not None

    fin_source = 'manual_data' if is_private else 'ai_bedrock'
    section_sources: dict = {}

    if is_private:
        # Private companies: only use manually-entered data stored in DynamoDB.
        # Never call external market data APIs or AI knowledge fetch for these.
        if from_cache:
            progress_events.append(progress(2, total_steps, 'Loading stored financial data...'))
        else:
            progress_events.append(progress(2, total_steps, 'No financial data stored yet — enter data manually.'))
            fin = {'income_statement': {}, 'balance_sheet': {}, 'cashflow': {}, 'key_metrics': {},
                   'error': 'No financial data stored for this private company. Use Manual Data Entry to add figures.'}
    else:
        # On a fresh fetch, scrub any empty period stubs left by previous failed AI calls
        if not from_cache:
            _cleanup_empty_financial_periods(ticker)

        if from_cache:
            progress_events.append(progress(2, total_steps, 'Loading stored financial data...'))
        else:
            # Try SEC EDGAR first for US-listed stocks (official filings, always current)
            sec_fin = get_financial_data_from_sec(ticker)
            if sec_fin:
                progress_events.append(progress(2, total_steps, 'Fetching latest SEC EDGAR filings...'))
                fin = sec_fin
                fin_source = 'sec_edgar'
            else:
                # Try Yahoo Finance for non-US stocks (JSE, LSE, etc.)
                yf_fin = get_financial_data_from_yahoo(ticker)
                if yf_fin:
                    progress_events.append(progress(2, total_steps, 'Fetching financial data from Yahoo Finance...'))
                    fin = dict(yf_fin)  # mutable copy so we can fill in gaps
                    fin_source = 'yahoo_finance'

                    # Identify sections Yahoo Finance could not provide
                    missing_sections = [
                        s for s in ('income_statement', 'balance_sheet', 'cashflow')
                        if not _has_real_values(fin.get(s) or {})
                    ]
                    if missing_sections:
                        print(f"[Hybrid] Yahoo missing {missing_sections} for {ticker} — supplementing with AI")
                        progress_events.append(progress(2, total_steps,
                            f'Supplementing {len(missing_sections)} missing section(s) with AI...'))
                        ai_supp = get_financial_data_with_ai(ticker, company_name)
                        if ai_supp and not ai_supp.get('error'):
                            for section in missing_sections:
                                ai_data = ai_supp.get(section) or {}
                                if _has_real_values(ai_data):
                                    fin[section] = ai_data
                                    section_sources[section] = 'ai_bedrock'
                                    print(f"[Hybrid] AI filled {section} for {ticker}")
                                else:
                                    print(f"[Hybrid] AI also has no data for {section} ({ticker})")
                else:
                    # Final fallback: Claude AI (last resort for unknown tickers)
                    progress_events.append(progress(2, total_steps, 'Retrieving financial data with AI...'))
                    fin = get_financial_data_with_ai(ticker, company_name)
                    fin_source = 'ai_bedrock'

    ai_error = fin.get('error')
    data_confidence = fin.get('data_confidence', 'low') if not ai_error else 'none'
    fiscal_year = fin.get('fiscal_year', '')

    inc = fin.get('income_statement', {}) or {}
    bal = fin.get('balance_sheet', {}) or {}
    cf  = fin.get('cashflow', {}) or {}
    km  = fin.get('key_metrics', {}) or {}
    fin_currency = fin.get('currency', 'USD')

    # Persist freshly-fetched data in the original reporting currency (e.g. ZAR for JSE
    # stocks) so the UI displays human-readable values. Scaling for valuation happens below.
    if not from_cache and not ai_error and any(_has_real_values(d) for d in [inc, bal, cf, km] if d):
        _save_ai_financial_data(ticker, inc, bal, cf, km, fiscal_year, fin_currency,
                                fin_source, section_sources or None)

    # ------------------------------------------------------------------
    # Currency conversion (valuation only — does NOT affect stored data)
    # Financial statements are in their reporting currency (e.g. JPY, ZAR),
    # but the live price may be in a different currency or sub-unit (e.g. USD,
    # ZAC). Fetch an FX scale factor and convert all monetary statement values
    # so that per-share fair values and the current price use the same unit.
    # Dimensionless ratios (P/E, ROE, ROA) and share counts are NOT scaled.
    # ------------------------------------------------------------------
    fx_scale = _get_fx_scale(fin_currency, currency)
    if fx_scale is not None and fx_scale != 1.0:
        print(f"[Currency] Scaling financials ×{fx_scale:.6f} ({fin_currency} → {currency}) for {ticker}")
        def _scale_stmt(d: dict) -> dict:
            return {k: v * fx_scale if isinstance(v, (int, float)) else v for k, v in d.items()}
        inc = _scale_stmt(inc)
        bal = _scale_stmt(bal)
        cf  = _scale_stmt(cf)
        # key_metrics: shares_outstanding is a count; ratios are dimensionless — no scaling
    elif fx_scale is None and fin_currency.upper() != currency.upper():
        print(f"[Currency] WARNING: could not determine FX rate {fin_currency} → {currency} "
              f"for {ticker}. Valuation numbers may be unreliable.")

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

    # Use preset weights (resolved above from business_type param or LLM auto-selection)
    fair_value = weighted_fair_value([
        (dcf_value,      w['dcf']),
        (pe_value,       w['pe']),
        (earnings_power, w['epv']),
        (book_value,     w['asset']),
    ])

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
        recommendation = None  # No recommendation without financial data

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

    # ------------------------------------------------------------------
    # Step 8: AI commentary — plain-language price & buy opinion
    # ------------------------------------------------------------------
    progress_events.append(progress(8, total_steps, 'Generating AI commentary...'))
    ai_commentary, ai_recommendation = _generate_ai_commentary(
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        industry=industry,
        current_price=current_price,
        currency=currency,
        fair_value=fair_value,
        margin_of_safety=margin_of_safety,
        recommendation=recommendation,
        resolved_preset=resolved_preset,
        inc=inc,
        bal=bal,
        cf=cf,
        km=km,
    )

    # Detect AI conflict: model is bullish/bearish but AI disagrees
    model_recommendation = recommendation  # preserve original before possible override

    def _rec_bucket(r):
        if r in ('Strong Buy', 'Buy'):
            return 'bullish'
        if r in ('Reduce', 'Avoid'):
            return 'bearish'
        return 'neutral'

    def _worst_rec(m, a):
        """Return the more pessimistic of model rec (m) and AI rec (a: Buy/Hold/Avoid)."""
        severity = {'Strong Buy': 1, 'Buy': 2, 'Hold': 3, 'Reduce': 4, 'Avoid': 5}
        ai_mapped = a if a in severity else None
        if not m and not ai_mapped:
            return None
        if not m:
            return ai_mapped
        if not ai_mapped:
            return m
        return m if severity.get(m, 0) >= severity.get(ai_mapped, 0) else ai_mapped

    model_bucket = _rec_bucket(recommendation) if recommendation else None
    ai_bucket = _rec_bucket(ai_recommendation) if ai_recommendation else None
    if (model_bucket and ai_bucket
            and model_bucket != 'neutral' and ai_bucket != 'neutral'
            and model_bucket != ai_bucket):
        recommendation = 'AI Conflict'

    # Worst-of recommendation for watchlist display (always most cautious)
    worst_recommendation = _worst_rec(model_recommendation, ai_recommendation)

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
        'modelRecommendation': model_recommendation or None,
        'aiRecommendation': ai_recommendation or None,
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
        'aiCommentary': ai_commentary or None,
        'timestamp': datetime.now().isoformat(),
        'dataSource': 'ai-bedrock-claude',
        # Preset / weight info so the frontend can sync its dropdown
        'businessType': resolved_preset,
        'recommendedPreset': resolved_preset,
        'analysisWeights': {
            'dcf_weight':   w['dcf'],
            'epv_weight':   w['epv'],
            'asset_weight': w['asset'],
        },
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
            'recommendation': worst_recommendation,  # most cautious for watchlist display
            'modelRecommendation': analysis.get('modelRecommendation'),
            'aiRecommendation': analysis.get('aiRecommendation'),
            'recommendationReasoning': analysis['recommendationReasoning'],
            'valuation': analysis['valuation'],
            'pe_ratio': float(pe_from_km) if pe_from_km is not None else None,
            'timestamp': analysis['timestamp'],
            'dataSource': analysis['dataSource'],
            'businessType': analysis.get('businessType'),
            'analysisWeights': analysis.get('analysisWeights'),
            'aiCommentary': analysis.get('aiCommentary'),
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

def handle_delete_financial_period(event: dict) -> dict:
    """
    DELETE /api/financial-data/period?ticker=XXX&section=income_statement&period=2023-12-31
    Removes a single period key from one section of the stored financial data.
    """
    params = (event.get('queryStringParameters') or {})
    ticker  = params.get('ticker', '').strip().upper()
    section = params.get('section', '').strip()
    period  = params.get('period', '').strip()

    valid_sections = {'income_statement', 'balance_sheet', 'cashflow', 'key_metrics'}
    if not ticker or not section or not period:
        return {'statusCode': 400, 'body': json.dumps({'error': 'ticker, section, and period are required'})}
    if section not in valid_sections:
        return {'statusCode': 400, 'body': json.dumps({'error': f'section must be one of {sorted(valid_sections)}'})}

    try:
        table = boto3.resource('dynamodb', region_name='eu-west-1').Table(MANUAL_DATA_TABLE)
        table.update_item(
            Key={'ticker': ticker},
            UpdateExpression='REMOVE financial_data.#sec.#per',
            ExpressionAttributeNames={'#sec': section, '#per': period},
        )
        print(f"[DeletePeriod] Removed {ticker} / {section} / {period}")
        return {'statusCode': 200, 'body': json.dumps({'success': True, 'ticker': ticker, 'section': section, 'period': period})}
    except Exception as e:
        print(f"[DeletePeriod] Error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


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
# PDF upload handler — presigned S3 URL flow + Claude text analysis
# ---------------------------------------------------------------------------

S3_PDF_BUCKET = os.environ.get('PDF_BUCKET', 'stock-analysis-pdfs')

# Optional pypdf for text extraction (bundled in deployment package)
try:
    from pypdf import PdfReader as _PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def _extract_pdf_text(pdf_bytes: bytes, start_page: int = 0, max_pages: int = 80) -> tuple:
    """
    Extract text from a page range of a PDF using pypdf.
    Returns (text: str, total_page_count: int).
    text is empty string on failure or when pypdf is unavailable.
    """
    if not PYPDF_AVAILABLE:
        return '', 0
    import io
    try:
        reader = _PdfReader(io.BytesIO(pdf_bytes))
        total_pages = len(reader.pages)
        end_page = min(start_page + max_pages, total_pages)
        text_parts = []
        for page in reader.pages[start_page:end_page]:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
        return '\n'.join(text_parts), total_pages
    except Exception as e:
        print(f"[PDF text extract] Error: {e}")
        return '', 0


def _call_claude_extraction(bedrock_client, ticker: str, currency_hint: str, text: str) -> tuple:
    """
    Send extracted PDF text to Claude and return (parsed_dict, raw_text).
    Raises on Bedrock errors so the caller can handle them.
    """
    response = bedrock_client.invoke_model(
        modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 2000,
            'temperature': 0,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': f"Here is financial statement text extracted from a PDF:\n\n{text}"},
                    {'type': 'text', 'text': _build_extraction_prompt(ticker, currency_hint)}
                ]
            }]
        })
    )
    ai_text = json.loads(response['body'].read())['content'][0]['text']
    return _extract_json(ai_text), ai_text


def _merge_extracted_data(d1: dict, d2: dict) -> dict:
    """
    Merge two Claude extraction dicts.
    For scalar fields (fiscal_year, currency) prefer d1 unless empty.
    For section dicts, prefer d1's field value unless it is None, then use d2's.
    """
    merged: dict = {}
    for key in ('fiscal_year', 'currency'):
        merged[key] = d1.get(key) or d2.get(key)
    for section in ('income_statement', 'balance_sheet', 'cashflow', 'key_metrics'):
        s1 = d1.get(section) or {}
        s2 = d2.get(section) or {}
        merged[section] = {
            field: (s1[field] if s1.get(field) is not None else s2.get(field))
            for field in set(list(s1) + list(s2))
        }
    return merged


def handle_get_pdf_upload_url(event: dict) -> dict:
    """
    Step 1: Generate a presigned S3 PUT URL so the browser can upload
    the PDF directly to S3 (bypasses API Gateway's 10 MB payload limit).
    GET /api/upload-pdf?ticker=BEL.XJSE
    Returns: { upload_url, s3_key }
    """
    params = event.get('queryStringParameters') or {}
    ticker = params.get('ticker', '').strip().upper()
    if not ticker:
        return {'statusCode': 400, 'body': json.dumps({'error': 'ticker parameter required'})}

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    s3_key = f"uploads/{ticker}_{timestamp}.pdf"

    try:
        s3 = boto3.client('s3', region_name='eu-west-1')
        upload_url = s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_PDF_BUCKET, 'Key': s3_key, 'ContentType': 'application/pdf'},
            ExpiresIn=3600,
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'upload_url': upload_url, 's3_key': s3_key})
        }
    except Exception as e:
        print(f"[PDF Upload] Presigned URL error: {e}")
        return {'statusCode': 500, 'body': json.dumps({'error': f'Could not generate upload URL: {e}'})}


def _build_extraction_prompt(ticker: str, currency_hint: str) -> str:
    return f"""Extract all financial data from this PDF financial statement for {ticker}.
Return ONLY a JSON object with this exact structure (no markdown, no explanation):
{{
  "fiscal_year": "YYYY-MM-DD",
  "currency": "ISO 3-letter currency code",
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
    "shares_outstanding": <number or null>,
    "pe_ratio": <number or null>,
    "pb_ratio": <number or null>,
    "debt_to_equity": <number or null>,
    "current_ratio": <number or null>,
    "roe": <number or null>,
    "roa": <number or null>
  }}
}}
RULES:
- Use actual absolute numbers (not thousands/millions). E.g. 394328000000 not 394.3B.
- Report values in the document's native reporting currency (do NOT convert).
{f'- The currency is likely {currency_hint}.' if currency_hint else ''}
- For fiscal_year, use the period end date in YYYY-MM-DD format.
- If the document shows multiple periods (e.g. comparative statements with current and prior year), extract data for the MOST RECENT fiscal year only.
- Use null for any value not found in the document. Do NOT fabricate numbers."""


def _process_pdf_from_s3(ticker: str, s3_key: str, currency_hint: str) -> dict:
    """
    Core extraction: read PDF from S3, extract text in up to 2 chunks,
    call Claude for each, merge results, save to DynamoDB.
    Returns a summary dict. Raises on error.
    """
    s3 = boto3.client('s3', region_name='eu-west-1')
    pdf_bytes = s3.get_object(Bucket=S3_PDF_BUCKET, Key=s3_key)['Body'].read()
    print(f"[PDF Upload] Read {len(pdf_bytes):,} bytes from s3://{S3_PDF_BUCKET}/{s3_key}")

    CHUNK_SIZE = 80
    chunk1_text, total_pages = _extract_pdf_text(pdf_bytes, start_page=0, max_pages=CHUNK_SIZE)
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

    if chunk1_text:
        print(f"[PDF Upload] {total_pages} pages. Chunk 1: pp 1-{min(CHUNK_SIZE, total_pages)} ({len(chunk1_text):,} chars)")
        data1, raw1 = _call_claude_extraction(bedrock, ticker, currency_hint, chunk1_text)
        print(f"[PDF Upload] Chunk 1 response: {raw1[:200]}")
        if total_pages > CHUNK_SIZE:
            chunk2_text, _ = _extract_pdf_text(pdf_bytes, start_page=CHUNK_SIZE, max_pages=CHUNK_SIZE)
            if chunk2_text:
                print(f"[PDF Upload] Chunk 2: pp {CHUNK_SIZE+1}-{min(CHUNK_SIZE*2, total_pages)} ({len(chunk2_text):,} chars)")
                data2, raw2 = _call_claude_extraction(bedrock, ticker, currency_hint, chunk2_text)
                print(f"[PDF Upload] Chunk 2 response: {raw2[:200]}")
                data = _merge_extracted_data(data1, data2)
            else:
                data = data1
        else:
            data = data1
    else:
        # pypdf unavailable — fall back to document block (100-page limit applies)
        print(f"[PDF Upload] pypdf unavailable — using document block for {ticker}")
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')
        resp = bedrock.invoke_model(
            modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 2000,
                'temperature': 0,
                'messages': [{'role': 'user', 'content': [
                    {'type': 'document', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': pdf_b64}},
                    {'type': 'text', 'text': _build_extraction_prompt(ticker, currency_hint)},
                ]}]
            })
        )
        ai_text = json.loads(resp['body'].read())['content'][0]['text']
        print(f"[PDF Upload] Document-block response: {ai_text[:200]}")
        data = _extract_json(ai_text)

    if not data:
        raise ValueError('Could not parse Claude response')

    inc = {k: v for k, v in data.get('income_statement', {}).items() if v is not None}
    bal = {k: v for k, v in data.get('balance_sheet', {}).items() if v is not None}
    cf  = {k: v for k, v in data.get('cashflow', {}).items() if v is not None}
    km  = {k: v for k, v in data.get('key_metrics', {}).items() if v is not None}
    fiscal_year = data.get('fiscal_year', f"{datetime.now().year - 1}-12-31")
    currency = data.get('currency') or currency_hint or 'USD'

    print(f"[PDF Upload] Merged extraction for {ticker}: "
          f"inc={len(inc)} fields, bal={len(bal)} fields, cf={len(cf)} fields, "
          f"km={len(km)} fields, year={fiscal_year}, currency={currency}")
    if inc:
        sample = list(inc.items())[:2]
        print(f"[PDF Upload] inc sample: {sample}")
    if bal:
        sample = list(bal.items())[:2]
        print(f"[PDF Upload] bal sample: {sample}")

    _save_ai_financial_data(ticker, inc, bal, cf, km,
                            fiscal_year=fiscal_year, fin_currency=currency, source='pdf_upload')
    return {
        'sections_with_data': sum(1 for s in [inc, bal, cf, km] if s),
        'fiscal_year': fiscal_year,
        'currency': currency,
    }


def _handle_pdf_upload_async(event: dict) -> None:
    """
    Called by async Lambda self-invocation. Does the actual PDF extraction
    and writes the result / error status back to DynamoDB.
    """
    ticker = event.get('ticker', '')
    s3_key = event.get('s3_key', '')
    currency_hint = event.get('currency_hint', '')
    table = boto3.resource('dynamodb', region_name='eu-west-1').Table(MANUAL_DATA_TABLE)
    try:
        result = _process_pdf_from_s3(ticker, s3_key, currency_hint)
        table.update_item(
            Key={'ticker': ticker},
            UpdateExpression='SET pdf_status = :s, pdf_completed_at = :t',
            ExpressionAttributeValues={':s': 'complete', ':t': datetime.now().isoformat()},
        )
        print(f"[PDF Async] Complete for {ticker}: {result['sections_with_data']} sections")
    except Exception as e:
        print(f"[PDF Async] Failed for {ticker}: {e}")
        try:
            table.update_item(
                Key={'ticker': ticker},
                UpdateExpression='SET pdf_status = :s, pdf_error = :e',
                ExpressionAttributeValues={':s': 'error', ':e': str(e)},
            )
        except Exception:
            pass


def handle_pdf_upload(event: dict, context) -> dict:
    """
    POST /api/upload-pdf — marks status as 'processing', fires an async
    self-invocation to do the actual work, and returns immediately so we
    stay well within API Gateway's 29-second integration timeout.
    Body: { "s3_key": "uploads/BEL.XJSE_20260301_120000.pdf", "currency": "ZAR" }
    """
    params = event.get('queryStringParameters') or {}
    ticker = params.get('ticker', '').strip().upper()
    if not ticker:
        return {'statusCode': 400, 'body': json.dumps({'error': 'ticker parameter required'})}

    body_raw = event.get('body', '') or ''
    try:
        body_json = json.loads(body_raw)
        s3_key = body_json.get('s3_key', '')
        currency_hint = body_json.get('currency', '')
    except Exception as e:
        return {'statusCode': 400, 'body': json.dumps({'error': f'Invalid JSON body: {e}'})}

    if not s3_key:
        return {'statusCode': 400, 'body': json.dumps({'error': 's3_key field required'})}

    # Write 'processing' status so the frontend can poll
    try:
        table = boto3.resource('dynamodb', region_name='eu-west-1').Table(MANUAL_DATA_TABLE)
        table.update_item(
            Key={'ticker': ticker},
            UpdateExpression='SET pdf_status = :s, pdf_s3_key = :k, pdf_started_at = :t',
            ExpressionAttributeValues={
                ':s': 'processing', ':k': s3_key, ':t': datetime.now().isoformat(),
            },
        )
    except Exception as e:
        print(f"[PDF Upload] Could not write processing status: {e}")

    # Async self-invocation — fire and forget
    try:
        fn_name = getattr(context, 'function_name', 'stock-analysis-analyzer')
        boto3.client('lambda', region_name='eu-west-1').invoke(
            FunctionName=fn_name,
            InvocationType='Event',
            Payload=json.dumps({
                '_pdf_async': True,
                'ticker': ticker,
                's3_key': s3_key,
                'currency_hint': currency_hint,
            }),
        )
        print(f"[PDF Upload] Async job fired for {ticker} / {s3_key}")
    except Exception as e:
        print(f"[PDF Upload] Failed to invoke async processor: {e}")
        try:
            table.update_item(
                Key={'ticker': ticker},
                UpdateExpression='SET pdf_status = :s, pdf_error = :e',
                ExpressionAttributeValues={':s': 'error', ':e': str(e)},
            )
        except Exception:
            pass
        return {'statusCode': 500, 'body': json.dumps({'error': f'Could not start PDF processing: {e}'})}

    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'processing',
            'message': 'PDF received. Extraction is running in the background.',
            'ticker': ticker,
        }),
    }


def handle_pdf_status(event: dict) -> dict:
    """GET /api/upload-pdf/status?ticker=XXX — returns current processing status."""
    params = event.get('queryStringParameters') or {}
    ticker = params.get('ticker', '').strip().upper()
    if not ticker:
        return {'statusCode': 400, 'body': json.dumps({'error': 'ticker required'})}
    try:
        item = (boto3.resource('dynamodb', region_name='eu-west-1')
                .Table(MANUAL_DATA_TABLE)
                .get_item(Key={'ticker': ticker})
                .get('Item') or {})
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': item.get('pdf_status', 'unknown'),
                'has_data': bool(item.get('has_data')),
                'error': item.get('pdf_error'),
                'ticker': ticker,
            }),
        }
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Bulk analysis (orchestrator + worker + status)
# ---------------------------------------------------------------------------

BULK_JOB_PREFIX = 'BULK_JOB#'


def handle_bulk_analyze(event, context):
    """POST /api/bulk-analyze { tickers: [...] }
    Creates a job record in DynamoDB and fires an async Lambda invocation for
    each ticker.  Returns { jobId, total } immediately — no waiting.
    """
    try:
        body = event.get('body') or '{}'
        if isinstance(body, str):
            body = json.loads(body)
    except Exception:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Invalid JSON body'})}

    tickers = body.get('tickers') or []
    if not tickers or not isinstance(tickers, list):
        return {'statusCode': 400, 'body': json.dumps({'error': 'tickers list required'})}

    tickers = [str(t).strip().upper() for t in tickers if t]
    total = len(tickers)
    job_id = str(uuid.uuid4())

    # Create job record
    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table(MANUAL_DATA_TABLE)
    table.put_item(Item={
        'ticker': f'{BULK_JOB_PREFIX}{job_id}',
        'status': 'running',
        'total': total,
        'completed': 0,
        'failed': 0,
        'created_at': datetime.now().isoformat(),
    })

    # Fire a single async self-invocation to do the per-ticker fan-out.
    # This lets us return jobId immediately without waiting for 200+ invocations.
    function_name = context.function_name if context and hasattr(context, 'function_name') else 'stock-analysis-analyzer'
    lc = boto3.client('lambda', region_name='eu-west-1')
    lc.invoke(
        FunctionName=function_name,
        InvocationType='Event',  # async, fire-and-forget
        Payload=json.dumps({'_bulk_fanout': True, 'bulk_job_id': job_id, 'tickers': tickers}),
    )

    return {'statusCode': 200, 'body': json.dumps({'jobId': job_id, 'total': total})}


def handle_bulk_status(event):
    """GET /api/bulk-status?jobId=xxx"""
    params = event.get('queryStringParameters') or {}
    job_id = params.get('jobId', '').strip()
    if not job_id:
        return {'statusCode': 400, 'body': json.dumps({'error': 'jobId required'})}

    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table(MANUAL_DATA_TABLE)
    item = table.get_item(Key={'ticker': f'{BULK_JOB_PREFIX}{job_id}'}).get('Item')
    if not item:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Job not found'})}

    return {
        'statusCode': 200,
        'body': json.dumps({
            'jobId': job_id,
            'status': item.get('status', 'running'),
            'total': int(item.get('total', 0)),
            'completed': int(item.get('completed', 0)),
            'failed': int(item.get('failed', 0)),
        }),
    }


def _handle_bulk_fanout(event):
    """Invoked asynchronously by handle_bulk_analyze.
    Fans out one async Lambda invocation per ticker.
    """
    job_id = event.get('bulk_job_id')
    tickers = event.get('tickers', [])
    if not job_id or not tickers:
        return

    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'stock-analysis-analyzer')
    lc = boto3.client('lambda', region_name='eu-west-1')

    failed_invokes = 0

    def _invoke(ticker):
        lc.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps({'_bulk_job': True, 'bulk_job_id': job_id, 'ticker': ticker}),
        )

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(_invoke, t): t for t in tickers}
        for future in as_completed(futures):
            exc = future.exception()
            if exc:
                print(f"[BulkFanout] Failed to invoke {futures[future]}: {exc}")
                failed_invokes += 1

    if failed_invokes:
        try:
            dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
            table = dynamodb.Table(MANUAL_DATA_TABLE)
            table.update_item(
                Key={'ticker': f'{BULK_JOB_PREFIX}{job_id}'},
                UpdateExpression='ADD failed :n',
                ExpressionAttributeValues={':n': failed_invokes},
            )
        except Exception:
            pass


def _handle_bulk_job_ticker(event):
    """Called when this Lambda is invoked asynchronously as part of a bulk job.
    Runs analysis for a single ticker and atomically updates the job record.
    """
    job_id = event.get('bulk_job_id')
    ticker = event.get('ticker', '').strip().upper()
    if not job_id or not ticker:
        return

    dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
    table = dynamodb.Table(MANUAL_DATA_TABLE)

    success = False
    try:
        result = analyze_stock_get(ticker, stream=False, params={})
        success = result.get('statusCode') == 200
    except Exception as exc:
        print(f"[BulkJob] {ticker} failed: {exc}")

    try:
        resp = table.update_item(
            Key={'ticker': f'{BULK_JOB_PREFIX}{job_id}'},
            UpdateExpression='ADD completed :c, failed :f',
            ExpressionAttributeValues={
                ':c': 1 if success else 0,
                ':f': 0 if success else 1,
            },
            ReturnValues='ALL_NEW',
        )
        attrs = resp.get('Attributes', {})
        done = int(attrs.get('completed', 0)) + int(attrs.get('failed', 0))
        total = int(attrs.get('total', 0))
        if total > 0 and done >= total:
            table.update_item(
                Key={'ticker': f'{BULK_JOB_PREFIX}{job_id}'},
                UpdateExpression='SET #s = :done',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':done': 'complete'},
            )
    except Exception as exc:
        print(f"[BulkJob] Failed to update job {job_id}: {exc}")


# Lambda entry point
# ---------------------------------------------------------------------------

def lambda_handler(event, context):
    """AWS Lambda handler for stock analysis"""

    # Async PDF processing — invoked by handle_pdf_upload with InvocationType='Event'
    if event.get('_pdf_async'):
        _handle_pdf_upload_async(event)
        return

    # Async bulk fan-out — fires one async invocation per ticker, then exits
    if event.get('_bulk_fanout'):
        _handle_bulk_fanout(event)
        return

    # Async bulk-job worker — invoked by _handle_bulk_fanout with InvocationType='Event'
    if event.get('_bulk_job'):
        _handle_bulk_job_ticker(event)
        return

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
            ticker = unquote(path.split('/api/analysis/')[-1])
            result = analyze_stock(ticker, event)

        elif '/api/analyze/' in path and method == 'GET':
            ticker = unquote(path.split('/api/analyze/')[-1].split('?')[0])
            query_params = event.get('queryStringParameters') or {}
            stream = query_params.get('stream', 'false').lower() == 'true'
            result = analyze_stock_get(ticker, stream, query_params)

        elif '/api/analysis-presets' in path and method == 'GET':
            result = get_analysis_presets()

        elif '/api/batch-analyze' in path and method == 'POST':
            result = handle_batch_analyze(event)

        elif '/api/bulk-analyze' in path and method == 'POST':
            result = handle_bulk_analyze(event, context)

        elif '/api/bulk-status' in path and method == 'GET':
            result = handle_bulk_status(event)

        # /api/upload-pdf/status must be checked before /api/upload-pdf
        elif '/api/upload-pdf/status' in path and method == 'GET':
            result = handle_pdf_status(event)

        elif '/api/upload-pdf' in path and method == 'GET':
            result = handle_get_pdf_upload_url(event)

        elif '/api/upload-pdf' in path and method == 'POST':
            result = handle_pdf_upload(event, context)

        elif '/api/financial-data/period' in path and method == 'DELETE':
            result = handle_delete_financial_period(event)

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
