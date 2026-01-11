/**
 * Test MarketStack Ticker Endpoint
 * Check if the /tickers/{ticker} endpoint works for BEL.XJSE
 */

async function testMarketStackTickerEndpoint() {
    console.log('🔍 Testing MarketStack Ticker Endpoint');
    console.log('=====================================');
    
    const apiKey = 'b435b1cd06228185916b7b7afd790dc6';
    
    try {
        // Test 1: Try the specific ticker endpoint for BEL.XJSE
        console.log('\n1️⃣ Testing /tickers/BEL.XJSE endpoint...');
        const tickerUrl = `http://api.marketstack.com/v1/tickers/BEL.XJSE?access_key=${apiKey}`;
        console.log('🌐 URL:', tickerUrl);
        
        const tickerResponse = await fetch(tickerUrl);
        const tickerData = await tickerResponse.json();
        
        console.log('📊 Response status:', tickerResponse.status);
        console.log('📊 Response data:', JSON.stringify(tickerData, null, 2));
        
        if (tickerData.data) {
            console.log('✅ Ticker endpoint works!');
            console.log('📊 Company name:', tickerData.data.name);
        } else if (tickerData.error) {
            console.log('❌ Ticker endpoint failed:', tickerData.error.message);
        }
        
        // Test 2: Try without the .XJSE suffix
        console.log('\n2️⃣ Testing /tickers/BEL endpoint...');
        const belUrl = `http://api.marketstack.com/v1/tickers/BEL?access_key=${apiKey}`;
        
        const belResponse = await fetch(belUrl);
        const belData = await belResponse.json();
        
        console.log('📊 BEL Response status:', belResponse.status);
        if (belData.data) {
            console.log('✅ BEL ticker found:', belData.data.name);
        } else if (belData.error) {
            console.log('❌ BEL ticker failed:', belData.error.message);
        }
        
        // Test 3: Try a known working ticker for comparison
        console.log('\n3️⃣ Testing /tickers/AAPL endpoint for comparison...');
        const aaplUrl = `http://api.marketstack.com/v1/tickers/AAPL?access_key=${apiKey}`;
        
        const aaplResponse = await fetch(aaplUrl);
        const aaplData = await aaplResponse.json();
        
        console.log('📊 AAPL Response status:', aaplResponse.status);
        if (aaplData.data) {
            console.log('✅ AAPL ticker works:', aaplData.data.name);
        }
        
        console.log('\n💡 SOLUTION');
        console.log('===========');
        console.log('The issue is likely that the /tickers/{ticker} endpoint');
        console.log('doesn\'t work for all ticker formats (like BEL.XJSE).');
        console.log('');
        console.log('We should modify the Lambda to:');
        console.log('1. Use the search results we already have from the search endpoint');
        console.log('2. Extract company names from search results instead of ticker endpoint');
        console.log('3. Cache company names from successful searches');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Run the test
testMarketStackTickerEndpoint();