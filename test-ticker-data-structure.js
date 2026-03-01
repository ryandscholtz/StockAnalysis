// Test what data structure the ticker endpoint returns
const https = require('https');

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';
const ticker = 'AAPL';

function makeRequest(path) {
    return new Promise((resolve, reject) => {
        const url = new URL(API_BASE + path);
        https.get(url, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    resolve({
                        statusCode: res.statusCode,
                        body: JSON.parse(data)
                    });
                } catch (e) {
                    resolve({
                        statusCode: res.statusCode,
                        body: data
                    });
                }
            });
        }).on('error', reject);
    });
}

async function testTickerData() {
    console.log('Testing ticker data structure...\n');
    
    try {
        // Test watchlist endpoint
        console.log(`GET /api/watchlist/${ticker}`);
        const watchlistResponse = await makeRequest(`/api/watchlist/${ticker}`);
        console.log('Status:', watchlistResponse.statusCode);
        console.log('Response:', JSON.stringify(watchlistResponse.body, null, 2));
        console.log('\n---\n');
        
        // Test ticker info endpoint
        console.log(`GET /api/ticker/${ticker}`);
        const tickerResponse = await makeRequest(`/api/ticker/${ticker}`);
        console.log('Status:', tickerResponse.statusCode);
        console.log('Response:', JSON.stringify(tickerResponse.body, null, 2));
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

testTickerData();
