import boto3, json, base64, time

session = boto3.Session(profile_name='Cerebrum')
client = session.client('lambda', region_name='eu-west-1')

for market in ['JSE', 'NYSE', 'NASDAQ']:
    payload = {
        'httpMethod': 'GET',
        'path': '/api/explore/stocks',
        'queryStringParameters': {'market': market, 'force_refresh': 'true'}
    }
    start = time.time()
    response = client.invoke(
        FunctionName='stock-analysis-stock-data',
        InvocationType='RequestResponse',
        LogType='Tail',
        Payload=json.dumps(payload)
    )
    elapsed = time.time() - start
    result = json.loads(response['Payload'].read())
    body = json.loads(result.get('body', '{}'))
    stocks = body.get('stocks', [])
    print(f"\n=== {market} ({elapsed:.1f}s) ===")
    print(f"Status: {result.get('statusCode')}, Stocks: {len(stocks)}")
    if stocks:
        for s in stocks[:3]:
            mc = s.get('marketCap') or 0
            print(f"  {s['ticker']}: {s['companyName']} ${mc/1e9:.1f}B")

    log = base64.b64decode(response.get('LogResult', '')).decode()
    for line in log.split('\n'):
        if 'DEBUG' in line and ('Screener' in line or 'Fetching' in line or 'session' in line):
            print(' ', line.strip())
