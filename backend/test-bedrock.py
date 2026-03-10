import boto3
import json

session = boto3.Session(profile_name='cerebrum', region_name='eu-west-1')
bedrock = session.client('bedrock-runtime', region_name='eu-west-1')

print("Testing Bedrock Claude Haiku 4.5 in eu-west-1...")
try:
    response = bedrock.invoke_model(
        modelId='us.anthropic.claude-haiku-4-5-20251001-v1:0',
        body=json.dumps({
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': 50,
            'messages': [{'role': 'user', 'content': 'Say hello'}]
        })
    )
    result = json.loads(response['body'].read())
    print("SUCCESS:", result.get('content', [{}])[0].get('text', ''))
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
