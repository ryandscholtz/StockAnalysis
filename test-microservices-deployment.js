// Test Microservices Deployment
const https = require('https');

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

function makeRequest(path, method = 'GET', body = null) {
    return new Promise((resolve, reject) => {
        const url = new URL(API_BASE + path);
        const options = {
            hostname: url.hostname,
            path: url.pathname + url.search,
            method: method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (body) {
            const bodyStr = JSON.stringify(body);
            options.headers['Content-Length'] = Buffer.byteLength(bodyStr);
        }

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        body: data ? JSON.parse(data) : null
                    });
                } catch (e) {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        body: data
                    });
                }
            });
        });

        req.on('error', reject);
        
        if (body) {
            req.write(JSON.stringify(body));
        }
        
        req.end();
    });
}

async function runTests() {
    console.log('========================================');
    console.log('Testing Microservices Deployment');
    console.log('========================================\n');

    const tests = [
        {
            name: 'Health Check (Gateway)',
            path: '/health',
            expectedStatus: 200
        },
        {
            name: 'API Version',
            path: '/api/version',
            expectedStatus: 200
        },
        {
            name: 'Search Endpoint (Stock Data Lambda)',
            path: '/api/search?query=AAPL',
            expectedStatus: 200
        },
        {
            name: 'Ticker Info (Stock Data Lambda)',
            path: '/api/ticker/AAPL',
            expectedStatus: 200
        }
    ];

    let passed = 0;
    let failed = 0;

    for (const test of tests) {
        try {
            console.log(`Testing: ${test.name}`);
            console.log(`  Path: ${test.path}`);
            
            const response = await makeRequest(test.path);
            
            if (response.statusCode === test.expectedStatus) {
                console.log(`  ✓ Status: ${response.statusCode} (Expected: ${test.expectedStatus})`);
                if (response.body) {
                    console.log(`  Response: ${JSON.stringify(response.body).substring(0, 100)}...`);
                }
                passed++;
            } else {
                console.log(`  ✗ Status: ${response.statusCode} (Expected: ${test.expectedStatus})`);
                console.log(`  Response: ${JSON.stringify(response.body)}`);
                failed++;
            }
        } catch (error) {
            console.log(`  ✗ Error: ${error.message}`);
            failed++;
        }
        console.log('');
    }

    console.log('========================================');
    console.log('Test Results');
    console.log('========================================');
    console.log(`Passed: ${passed}/${tests.length}`);
    console.log(`Failed: ${failed}/${tests.length}`);
    console.log('');

    if (failed === 0) {
        console.log('✓ All tests passed! Microservices deployment successful!');
    } else {
        console.log('✗ Some tests failed. Check the logs above for details.');
    }
}

runTests().catch(console.error);
