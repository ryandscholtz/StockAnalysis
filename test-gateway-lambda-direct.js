// Test Gateway Lambda directly via AWS SDK
const { LambdaClient, InvokeCommand } = require('@aws-sdk/client-lambda');

const client = new LambdaClient({ 
    region: 'eu-west-1',
    credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
    }
});

const testEvent = {
    resource: '/health',
    path: '/health',
    httpMethod: 'GET',
    headers: {},
    queryStringParameters: null,
    pathParameters: null,
    body: null,
    isBase64Encoded: false
};

async function testLambda() {
    console.log('Testing stock-analysis-gateway Lambda...\n');
    
    try {
        const command = new InvokeCommand({
            FunctionName: 'stock-analysis-gateway',
            Payload: JSON.stringify(testEvent)
        });
        
        const response = await client.send(command);
        const result = JSON.parse(Buffer.from(response.Payload).toString());
        
        console.log('Lambda Response:');
        console.log(JSON.stringify(result, null, 2));
        
        if (result.statusCode === 200) {
            console.log('\n✓ Lambda is working correctly!');
        } else {
            console.log('\n✗ Lambda returned error status:', result.statusCode);
        }
    } catch (error) {
        console.error('Error invoking Lambda:', error.message);
        if (error.$metadata) {
            console.error('AWS Error Details:', error.$metadata);
        }
    }
}

testLambda();
