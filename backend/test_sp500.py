import boto3, json, base64, time

session = boto3.Session(profile_name='Cerebrum')
client = session.client('lambda', region_name='eu-west-1')

payload = {
    'httpMethod': 'GET',
    'path': '/api/explore/stocks',
    'queryStringParameters': {'market': 'SP500'}
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
print(f'Elapsed: {elapsed:.1f}s')
print(f'Status: {result.get("statusCode")}')
print(f'Stocks returned: {len(stocks)}')
if stocks:
    print('Top 5 by market cap:')
    for s in stocks[:5]:
        mc = s.get('marketCap') or 0
        print(f'  {s["ticker"]}: {s["companyName"]} - ${mc/1e12:.2f}T')

log_b64 = response.get('LogResult', '')
if log_b64:
    log = base64.b64decode(log_b64).decode()
    for l in log.split('\n'):
        if 'DEBUG' in l or 'ERROR' in l or 'Task timed' in l:
            print(l)
