import boto3
import json
import base64
import time

session = boto3.Session(profile_name='cerebrum', region_name='eu-west-1')
client = session.client('lambda', region_name='eu-west-1')

payload = {
    "path": "/api/analyze/AAPL",
    "httpMethod": "GET",
    "queryStringParameters": {"stream": "false"},
    "headers": {}
}

print("Invoking stock-analysis-analyzer Lambda directly...")
start = time.time()

response = client.invoke(
    FunctionName='stock-analysis-analyzer',
    InvocationType='RequestResponse',
    LogType='Tail',
    Payload=json.dumps(payload).encode()
)

elapsed = time.time() - start
print(f"Duration: {elapsed:.2f}s")
print(f"Status: {response['StatusCode']}")

# Decode and print logs
if 'LogResult' in response:
    logs = base64.b64decode(response['LogResult']).decode('utf-8', errors='replace')
    print("\n=== Lambda Logs (tail) ===")
    print(logs)

# Print response body
result = json.loads(response['Payload'].read())
print("\n=== Response ===")
body = json.loads(result.get('body', '{}'))
print(json.dumps(body, indent=2)[:2000])
