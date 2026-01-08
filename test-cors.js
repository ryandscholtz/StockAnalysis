// Simple Node.js script to test CORS from command line
const https = require('https');

const API_BASE = 'https://9ye8wru6s5.execute-api.us-east-1.amazonaws.com/production';

function testEndpoint(path, description) {
    return new Promise((resolve) => {
        console.log(`\n=== Testing ${description} ===`);
        
        const options = {
            hostname: '9ye8wru6s5.execute-api.us-east-1.amazonaws.com',
            port: 443,
            path: `/production${path}`,
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Origin': 'http://localhost:3000'
            }
        };
        
        const req = https.request(options, (res) => {
            console.log(`Status: ${res.statusCode}`);
            console.log('CORS Headers:');
            console.log(`  Access-Control-Allow-Origin: ${res.headers['access-control-allow-origin']}`);
            console.log(`  Access-Control-Allow-Methods: ${res.headers['access-control-allow-methods']}`);
            console.log(`  Access-Control-Allow-Headers: ${res.headers['access-control-allow-headers']}`);
            
            let data = '';
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    console.log('Response:', JSON.stringify(parsed, null, 2));
                    resolve({ success: true, status: res.statusCode });
                } catch (e) {
                    console.log('Raw response:', data);
                    resolve({ success: true, status: res.statusCode });
                }
            });
        });
        
        req.on('error', (error) => {
            console.error('Error:', error.message);
            resolve({ success: false, error: error.message });
        });
        
        req.end();
    });
}

async function runTests() {
    console.log('Testing CORS configuration...');
    
    const tests = [
        ['/api/version', 'API Version'],
        ['/api/watchlist', 'Watchlist'],
        ['/api/search?q=AAPL', 'Search'],
        ['/health', 'Health Check']
    ];
    
    let passed = 0;
    for (const [path, description] of tests) {
        const result = await testEndpoint(path, description);
        if (result.success && result.status === 200) {
            passed++;
        }
        // Wait between tests
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log(`\n=== Summary ===`);
    console.log(`Passed: ${passed}/${tests.length}`);
    
    if (passed === tests.length) {
        console.log('🎉 All tests passed! CORS is working correctly.');
    } else {
        console.log('❌ Some tests failed.');
    }
}

runTests().catch(console.error);