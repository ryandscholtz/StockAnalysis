const https = require('https');

// Test the PDF upload endpoint
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

function testPDFEndpoint() {
    return new Promise((resolve, reject) => {
        console.log(`\n🧪 Testing PDF Upload endpoint...`);
        console.log(`URL: ${API_BASE_URL}/api/upload-pdf?ticker=AMZN`);
        
        const options = {
            hostname: 'dx0w31lbc1.execute-api.eu-west-1.amazonaws.com',
            port: 443,
            path: `/production/api/upload-pdf?ticker=AMZN`,
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            
            console.log(`Status: ${res.statusCode}`);
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    if (res.statusCode === 501) {
                        console.log(`✅ PDF Upload endpoint - Working (returns 501 Not Implemented as expected)`);
                        console.log('Response:', JSON.stringify(jsonData, null, 2));
                    } else {
                        console.log(`❓ PDF Upload endpoint - Unexpected status (${res.statusCode})`);
                        console.log('Response:', JSON.stringify(jsonData, null, 2));
                    }
                    resolve({ status: res.statusCode, data: jsonData });
                } catch (e) {
                    console.log(`Response (raw):`, data);
                    resolve({ status: res.statusCode, data: data });
                }
            });
        });

        req.on('error', (error) => {
            console.log(`❌ PDF Upload endpoint - Error:`, error.message);
            reject(error);
        });

        req.setTimeout(10000, () => {
            console.log(`⏰ PDF Upload endpoint - Timeout`);
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.end();
    });
}

async function runTest() {
    console.log('🚀 Testing PDF Upload Endpoint');
    console.log('===============================');
    
    try {
        await testPDFEndpoint();
        console.log('\n✅ PDF endpoint test completed');
    } catch (error) {
        console.log('\n❌ Test failed:', error.message);
    }
}

runTest();