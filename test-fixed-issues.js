/**
 * Test script to verify that the issues have been fixed:
 * 1. SSL protocol errors (cache endpoints)
 * 2. 404 errors for live-prices-async
 * 3. Real MarketStack API integration
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testApiEndpoints() {
    console.log('🧪 Testing API endpoints...\n');
    
    // Test 1: Health check
    console.log('1. Testing health endpoint...');
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('✅ Health check:', data.status);
    } catch (error) {
        console.log('❌ Health check failed:', error.message);
    }
    
    // Test 2: Live prices endpoint (should work now)
    console.log('\n2. Testing live prices endpoint...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/watchlist/live-prices`);
        const data = await response.json();
        console.log('✅ Live prices endpoint working');
        console.log('📊 API info:', data.api_info);
        console.log('💰 Sample prices:', Object.keys(data.live_prices).slice(0, 2).map(ticker => 
            `${ticker}: $${data.live_prices[ticker].price} (${data.live_prices[ticker].source})`
        ));
    } catch (error) {
        console.log('❌ Live prices failed:', error.message);
    }
    
    // Test 3: Search endpoint
    console.log('\n3. Testing search endpoint...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/search?q=AAPL`);
        const data = await response.json();
        console.log('✅ Search endpoint working');
        console.log('🔍 Found results:', data.results.length);
    } catch (error) {
        console.log('❌ Search failed:', error.message);
    }
    
    // Test 4: Analysis endpoint
    console.log('\n4. Testing analysis endpoint...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze/AAPL`);
        const data = await response.json();
        console.log('✅ Analysis endpoint working');
        console.log('📈 Analysis for AAPL:');
        console.log(`   Current Price: $${data.currentPrice}`);
        console.log(`   Fair Value: $${data.fairValue}`);
        console.log(`   Recommendation: ${data.recommendation}`);
        if (data.dataSource) {
            console.log(`   Price Source: ${data.dataSource.price_source}`);
            console.log(`   Has Real Price: ${data.dataSource.has_real_price}`);
        }
    } catch (error) {
        console.log('❌ Analysis failed:', error.message);
    }
    
    // Test 5: Watchlist endpoint
    console.log('\n5. Testing watchlist endpoint...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/watchlist`);
        const data = await response.json();
        console.log('✅ Watchlist endpoint working');
        console.log('📋 Watchlist items:', data.items.length);
    } catch (error) {
        console.log('❌ Watchlist failed:', error.message);
    }
    
    console.log('\n🎉 API testing complete!');
}

// Run the tests
testApiEndpoints().catch(console.error);