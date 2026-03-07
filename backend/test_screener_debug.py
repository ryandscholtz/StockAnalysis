"""Debug the Yahoo Finance screener to find the correct request format."""
import boto3, json, base64

session = boto3.Session(profile_name='Cerebrum')
client = session.client('lambda', region_name='eu-west-1')

# Invoke a tiny test via Lambda so we have the crumb/cookie
# We'll use a direct Python test instead
import urllib.request, urllib.error, http.cookiejar, time

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}
try:
    opener.open(urllib.request.Request("https://fc.yahoo.com", headers=headers), timeout=10)
except:
    pass

req = urllib.request.Request("https://query1.finance.yahoo.com/v1/test/getcrumb", headers=headers)
with opener.open(req, timeout=10) as r:
    crumb = r.read().decode().strip()
cookie_str = "; ".join(f"{c.name}={c.value}" for c in jar)
print(f"Crumb: {crumb!r}, cookies: {len(cookie_str)} chars")

# Try several body formats
formats = [
    # Format 1: topOperator + EQ uppercase + intradaymarketcap
    {
        "offset": 0, "size": 10,
        "sortField": "intradaymarketcap", "sortType": "DESC",
        "quoteType": "EQUITY",
        "topOperator": "AND",
        "query": {"operator": "AND", "operands": [{"operator": "EQ", "operands": ["exchange", "JNB"]}]},
        "userId": "", "userIdType": "guid",
    },
    # Format 2: eq lowercase + marketcap
    {
        "offset": 0, "size": 10,
        "sortField": "marketcap", "sortType": "DESC",
        "quoteType": "EQUITY",
        "query": {"operator": "AND", "operands": [{"operator": "eq", "operands": ["exchange", "JNB"]}]},
        "userId": "", "userIdType": "guid",
    },
    # Format 3: region filter instead of exchange
    {
        "offset": 0, "size": 10,
        "sortField": "intradaymarketcap", "sortType": "DESC",
        "quoteType": "EQUITY",
        "topOperator": "AND",
        "query": {"operator": "AND", "operands": [{"operator": "EQ", "operands": ["region", "za"]}]},
        "userId": "", "userIdType": "guid",
    },
]

urls = [
    f"https://query2.finance.yahoo.com/v1/finance/screener?crumb={crumb}&lang=en-US&region=US&formatted=false",
    f"https://query2.finance.yahoo.com/v1/finance/screener?crumb={crumb}&lang=en-US&region=US&formatted=false&corsDomain=finance.yahoo.com",
]

for i, body in enumerate(formats):
    for url in urls[:1]:  # try first URL only
        body_bytes = json.dumps(body).encode()
        req = urllib.request.Request(url, data=body_bytes, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": cookie_str,
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode())
            result = data.get('finance', {}).get('result') or []
            quotes = result[0].get('quotes', []) if result else []
            print(f"Format {i+1}: OK — {len(quotes)} results")
            if quotes:
                print(f"  First: {quotes[0].get('symbol')} - {quotes[0].get('shortName')}")
            break
        except urllib.error.HTTPError as e:
            body_resp = e.read().decode()[:200]
            print(f"Format {i+1}: {e.code} {e.reason} — {body_resp}")
        except Exception as e:
            print(f"Format {i+1}: {e}")
