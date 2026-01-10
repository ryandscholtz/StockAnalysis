// Test the manual data API endpoints
const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testManualDataAPI() {
    console.log('🧪 Testing Manual Data API Endpoints...');
    
    // Test 1: GET financial data for AAPL
    console.log('\n📊 Test 1: GET /api/manual-data/AAPL');
    try {
        const response = await fetch(`${API_BASE}/api/manual-data/AAPL`);
        console.log('Status:', response.status);
        const data = await response.json();
        console.log('Response:', JSON.stringify(data, null, 2));
    } catch (error) {
        console.error('❌ GET Error:', error.message);
    }
    
    // Test 2: POST manual data for AAPL
    console.log('\n📝 Test 2: POST /api/manual-data');
    try {
        const testData = {
            ticker: 'AAPL',
            data_type: 'income_statement',
            period: '2023-12-31',
            data: {
                revenue: 100000000,
                net_income: 15000000,
                earnings_per_share: 1.50
            }
        };
        
        const response = await fetch(`${API_BASE}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(testData)
        });
        
        console.log('Status:', response.status);
        const result = await response.json();
        console.log('Response:', JSON.stringify(result, null, 2));
    } catch (error) {
        console.error('❌ POST Error:', error.message);
    }
    
    // Test 3: GET financial data again to see if data was saved
    console.log('\n🔄 Test 3: GET /api/manual-data/AAPL (after POST)');
    try {
        const response = await fetch(`${API_BASE}/api/manual-data/AAPL`);
        console.log('Status:', response.status);
        const data = await response.json();
        console.log('Response:', JSON.stringify(data, null, 2));
    } catch (error) {
        console.error('❌ GET Error:', error.message);
    }
    
    // Test 4: Test analysis with manual data
    console.log('\n🎯 Test 4: GET /api/analyze/AAPL (should use manual data)');
    try {
        const response = await fetch(`${API_BASE}/api/analyze/AAPL?force_refresh=true`);
        console.log('Status:', response.status);
        const data = await response.json();
        console.log('Fair Value:', data.fairValue);
        console.log('Current Price:', data.currentPrice);
        console.log('Valuation:', data.valuation);
        console.log('Data Source:', data.dataSource);
    } catch (error) {
        console.error('❌ Analysis Error:', error.message);
    }
}

// Run the tests
testManualDataAPI().then(() => {
    console.log('\n✅ Manual Data API Tests Complete');
}).catch(error => {
    console.error('❌ Test Suite Error:', error);
});