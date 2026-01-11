/**
 * Test Direct MarketStack API Response
 * Check what data the API actually returns for Bell Equipment
 */

async function testDirectMarketStackAPI() {
    console.log('🔍 Testing Direct MarketStack API Response');
    console.log('==========================================');
    
    const apiKey = 'b435b1cd06228185916b7b7afd790dc6';
    
    try {
        // Test 1: Direct search for Bell Equipment
        console.log('\n1️⃣ Direct API Search for "BELL EQUIPMENT"...');
        const searchUrl = `http://api.marketstack.com/v1/tickers?access_key=${apiKey}&limit=20&search=BELL%20EQUIPMENT`;
        console.log('🌐 URL:', searchUrl);
        
        const searchResponse = await fetch(searchUrl);
        const searchData = await searchResponse.json();
        
        console.log('📊 API Response Status:', searchResponse.status);
        console.log('📈 Total results:', searchData.data?.length || 0);
        
        if (searchData.data && searchData.data.length > 0) {
            console.log('\n🎯 Bell Equipment Results from API:');
            searchData.data.forEach((ticker, index) => {
                console.log(`\n   ${index + 1}. Ticker: ${ticker.symbol || 'N/A'}`);
                console.log(`      Name: "${ticker.name || 'N/A'}"`);
                console.log(`      Exchange: ${ticker.stock_exchange?.name || 'N/A'} (${ticker.stock_exchange?.acronym || 'N/A'})`);
                console.log(`      Country: ${ticker.stock_exchange?.country || 'N/A'}`);
                console.log(`      Currency: ${ticker.stock_exchange?.currency || 'N/A'}`);
                console.log(`      Timezone: ${ticker.stock_exchange?.timezone || 'N/A'}`);
                console.log(`      MIC: ${ticker.stock_exchange?.mic || 'N/A'}`);
                console.log(`      Raw data:`, JSON.stringify(ticker, null, 2));
            });
        } else {
            console.log('❌ No results found in direct API call');
        }
        
        // Test 2: Search for specific ticker BEL
        console.log('\n2️⃣ Direct API Search for ticker "BEL"...');
        const belUrl = `http://api.marketstack.com/v1/tickers?access_key=${apiKey}&limit=20&search=BEL`;
        
        const belResponse = await fetch(belUrl);
        const belData = await belResponse.json();
        
        console.log('📊 BEL Search Results:', belData.data?.length || 0);
        
        if (belData.data && belData.data.length > 0) {
            console.log('\n🎯 BEL Ticker Results:');
            belData.data.forEach((ticker, index) => {
                if (ticker.symbol?.includes('BEL') || ticker.name?.toLowerCase().includes('bell')) {
                    console.log(`\n   ${index + 1}. Ticker: ${ticker.symbol}`);
                    console.log(`      Name: "${ticker.name}"`);
                    console.log(`      Exchange: ${ticker.stock_exchange?.name} (${ticker.stock_exchange?.acronym})`);
                    console.log(`      Country: ${ticker.stock_exchange?.country}`);
                }
            });
        }
        
        // Test 3: Try specific JSE exchange search
        console.log('\n3️⃣ Checking JSE Exchange Tickers...');
        const jseUrl = `http://api.marketstack.com/v1/tickers?access_key=${apiKey}&limit=50`;
        
        const jseResponse = await fetch(jseUrl);
        const jseData = await jseResponse.json();
        
        if (jseData.data) {
            const jseTickers = jseData.data.filter(ticker => 
                ticker.stock_exchange?.acronym === 'JSE' || 
                ticker.stock_exchange?.acronym === 'XJSE' ||
                ticker.symbol?.includes('BEL') ||
                ticker.name?.toLowerCase().includes('bell')
            );
            
            console.log(`📊 JSE/Bell related tickers found: ${jseTickers.length}`);
            
            jseTickers.forEach((ticker, index) => {
                console.log(`\n   ${index + 1}. ${ticker.symbol} - "${ticker.name}"`);
                console.log(`      Exchange: ${ticker.stock_exchange?.name} (${ticker.stock_exchange?.acronym})`);
                console.log(`      Country: ${ticker.stock_exchange?.country}`);
            });
        }
        
        // Test 4: Check our Lambda's processing
        console.log('\n4️⃣ Testing Our Lambda Processing...');
        const lambdaUrl = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/search?q=BELL%20EQUIPMENT';
        
        const lambdaResponse = await fetch(lambdaUrl);
        const lambdaData = await lambdaResponse.json();
        
        console.log('📊 Lambda Response:');
        console.log('   Data source:', lambdaData.data_source);
        console.log('   Results found:', lambdaData.total);
        
        if (lambdaData.results) {
            console.log('\n🎯 Lambda Processed Results:');
            lambdaData.results.forEach((result, index) => {
                console.log(`\n   ${index + 1}. Ticker: ${result.ticker}`);
                console.log(`      Name: "${result.name}"`);
                console.log(`      Exchange: ${result.exchange}`);
                console.log(`      Country: ${result.country}`);
                console.log(`      Sector: ${result.sector}`);
                console.log(`      Match Type: ${result.match_type}`);
                console.log(`      Score: ${result.relevance_score}`);
            });
        }
        
        console.log('\n📋 ANALYSIS');
        console.log('===========');
        console.log('🔍 Checking if the issue is:');
        console.log('   1. MarketStack API not returning company names');
        console.log('   2. Lambda function not processing names correctly');
        console.log('   3. Frontend not displaying names properly');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Run the test
testDirectMarketStackAPI();