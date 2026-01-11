const https = require('https');

// Test the watchlist endpoint directly
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
            console.log(`Headers:`, res.headers);
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const jsonData = JSON.parse(data);
                    console.log(`✅ ${description} - Success`);
                    console.log('Response:', JSON.stringify(jsonData, null, 2));
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
    console.log('🚀 Testing Stock Analysis API Endpoints');
    console.log('==========================================');
    
    try {
        // Test health endpoint first
        await testEndpoint('/health', 'Health Check');
        
        // Test root API endpoint
        await testEndpoint('/api', 'API Root');
        
        // Test watchlist endpoint (the problematic one)
        await testEndpoint('/api/watchlist', 'Watchlist Endpoint');
        
        // Test other endpoints to see what's working
        await testEndpoint('/api/search', 'Search Endpoint');
        
        console.log('\n✅ All tests completed');
        
    } catch (error) {
        console.log('\n❌ Test suite failed:', error.message);
    }
}

runTests();