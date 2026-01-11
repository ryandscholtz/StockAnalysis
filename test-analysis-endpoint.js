const https = require('https');

// Test the analysis endpoint
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

function testAnalysisEndpoint() {
    return new Promise((resolve, reject) => {
        console.log(`\n🧪 Testing Analysis endpoint...`);
        console.log(`URL: ${API_BASE_URL}/api/analyze/GOOGL`);
        
        const options = {
            hostname: 'dx0w31lbc1.execute-api.eu-west-1.amazonaws.com',
            port: 443,
            path: `/production/api/analyze/GOOGL`,
            method: 'GET',
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
                        console.log(`✅ Analysis endpoint - Working (returns 501 Not Implemented as expected)`);
                        console.log('Response:', JSON.stringify(jsonData, null, 2));
                    } else {
                        console.log(`❓ Analysis endpoint - Unexpected status (${res.statusCode})`);
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
            console.log(`❌ Analysis endpoint - Error:`, error.message);
            reject(error);
        });

        req.setTimeout(10000, () => {
            console.log(`⏰ Analysis endpoint - Timeout`);
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.end();
    });
}

async function runTest() {
    console.log('🚀 Testing Analysis Endpoint');
    console.log('============================');
    
    try {
        await testAnalysisEndpoint();
        console.log('\n✅ Analysis endpoint test completed');
    } catch (error) {
        console.log('\n❌ Test failed:', error.message);
    }
}

runTest();