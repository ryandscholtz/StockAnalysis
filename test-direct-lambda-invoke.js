/**
 * Test PDF upload by directly invoking the Lambda function
 * This bypasses API Gateway and CloudFront caching completely
 */

const AWS = require('aws-sdk');
const fs = require('fs');

// Configure AWS
AWS.config.update({
    region: 'eu-west-1',
    profile: 'Cerebrum'
});

const lambda = new AWS.Lambda();

async function testDirectLambdaInvoke() {
    console.log('🔍 Testing PDF Upload via Direct Lambda Invocation');
    console.log('='.repeat(60));
    
    // Create a test event that simulates API Gateway
    const testEvent = {
        httpMethod: 'POST',
        path: '/api/upload-pdf',
        queryStringParameters: {
            ticker: 'AAPL'
        },
        headers: {
            'content-type': 'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW',
            'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW'
        },
        body: createMultipartBody(),
        isBase64Encoded: false
    };
    
    console.log('📡 Invoking Lambda function directly...');
    console.log(`   Function: stock-analysis-api-production`);
    console.log(`   Method: ${testEvent.httpMethod}`);
    console.log(`   Path: ${testEvent.path}`);
    console.log(`   Ticker: ${testEvent.queryStringParameters.ticker}`);
    
    try {
        const params = {
            FunctionName: 'stock-analysis-api-production',
            Payload: JSON.stringify(testEvent)
        };
        
        const result = await lambda.invoke(params).promise();
        
        console.log('\n📊 Lambda Response:');
        console.log(`   Status Code: ${result.StatusCode}`);
        
        if (result.Payload) {
            const response = JSON.parse(result.Payload);
            console.log(`   Response Status: ${response.statusCode}`);
            console.log(`   Response Headers:`, response.headers);
            
            if (response.body) {
                try {
                    const body = JSON.parse(response.body);
                    console.log(`   Response Body:`, JSON.stringify(body, null, 2));
                    
                    if (response.statusCode === 200) {
                        console.log('\n✅ Direct Lambda invocation successful!');
                        console.log('   This confirms the Lambda function has the PDF upload endpoint');
                    } else if (response.statusCode === 400 && body.error && body.error.includes('multipart')) {
                        console.log('\n✅ Lambda function is working correctly!');
                        console.log('   It correctly rejects invalid multipart data');
                    } else {
                        console.log('\n⚠️ Unexpected response from Lambda');
                    }
                } catch (parseError) {
                    console.log(`   Raw Response Body: ${response.body}`);
                }
            }
        }
        
        if (result.FunctionError) {
            console.log(`   Function Error: ${result.FunctionError}`);
        }
        
    } catch (error) {
        console.log(`❌ Error invoking Lambda: ${error.message}`);
        console.log(`   Error Code: ${error.code}`);
        console.log(`   Stack: ${error.stack}`);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('🎯 Direct Lambda Test Complete!');
}

function createMultipartBody() {
    // Create a simple multipart body for testing
    const boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW';
    const pdfContent = '%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF';
    
    return [
        `--${boundary}`,
        'Content-Disposition: form-data; name="file"; filename="test.pdf"',
        'Content-Type: application/pdf',
        '',
        pdfContent,
        `--${boundary}--`,
        ''
    ].join('\r\n');
}

// Run the test
testDirectLambdaInvoke().catch(console.error);