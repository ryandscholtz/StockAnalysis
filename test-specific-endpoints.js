const https = require('https');

// Test the specific endpoints that were failing
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

function testEndpoint(path, description) {
    return new Promise((resolve, reject) => {
        console.log(`\n🧪 Testing ${description}...`);
        console.log(`URL: ${API_BASE_URL}${path}`);
        
        const options = {
            hostname: 'dx0w31lbc1.execute-api.eu-west-1.amazonaws.com',
            port: 443,
            path: `/production${path}`,
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
                    if (res.statusCode === 200) {
                        console.log(`✅ ${description} - Success`);
                        console.log('Response:', JSON.stringify(jsonData, null, 2));
                    } else {
                        console.log(`❌ ${description} - Failed (${res.statusCode})`);
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
            console.log(`❌ ${description} - Error:`, error.message);
            reject(error);
        });

        req.setTimeout(10000, () => {
            console.log(`⏰ ${description} - Timeout`);
            req.destroy();
            reject(new Error('Request timeout'));
        });

        req.end();
    });
}

async function runTests() {
    console.log('🚀 Testing Specific Endpoints That Were Failing');
    console.log('================================================');
    
    try {
        // Test the endpoints that were returning 404
        await testEndpoint('/api/watchlist/GOOGL', 'Individual Watchlist Item (GOOGL)');
        await testEndpoint('/api/watchlist/AAPL', 'Individual Watchlist Item (AAPL)');
        await testEndpoint('/api/manual-data/GOOGL', 'Financial Data (GOOGL)');
        await testEndpoint('/api/manual-data/AAPL', 'Financial Data (AAPL)');
        await testEndpoint('/api/watchlist/live-prices', 'Live Prices');
        await testEndpoint('/api/version', 'Version Info');
        
        console.log('\n✅ All specific endpoint tests completed');
        
    } catch (error) {
        console.log('\n❌ Test suite failed:', error.message);
    }
}

runTests();