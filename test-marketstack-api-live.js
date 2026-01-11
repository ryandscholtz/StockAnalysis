/**
 * Test MarketStack API Integration with Real API Key
 * Tests if the hybrid search is using the API correctly
 */

const API_BASE_URL = process.env.API_URL || 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testMarketStackAPI() {
    console.log('🧪 Testing MarketStack API Integration');
    console.log('=====================================');
    
    try {
        // Test 1: Check if API key is configured
        console.log('\n1️⃣ Testing API Health and Configuration...');
        const healthResponse = await fetch(`${API_BASE_URL}/health`);
        const healthData = await healthResponse.json();
        
        console.log('✅ Health check:', healthData.status);
        console.log('📦 Version:', healthData.version);
        console.log('🔧 Features:', healthData.features);
        
        // Test 2: Search for Bell Equipment (should use API if available)
        console.log('\n2️⃣ Testing Bell Equipment Search...');
        const bellResponse = await fetch(`${API_BASE_URL}/api/search?q=BELL%20EQUIPMENT`);
        const bellData = await bellResponse.json();
        
        console.log('🔍 Search query:', bellData.query);
        console.log('📊 Data source:', bellData.data_source);
        console.log('🌐 API integration:', bellData.api_integration);
        console.log('📈 Results found:', bellData.total);
        
        if (bellData.results && bellData.results.length > 0) {
            console.log('🎯 Bell Equipment results:');
            bellData.results.forEach((result, index) => {
                if (result.name.toLowerCase().includes('bell') || result.ticker.includes('BCF')) {
                    console.log(`   ${index + 1}. ${result.ticker} - ${result.name} (${result.exchange})`);
                    console.log(`      Match type: ${result.match_type}, Score: ${result.relevance_score}`);
                }
            });
        }
        
        // Test 3: Search for a common ticker (should definitely use API)
        console.log('\n3️⃣ Testing Common Ticker Search (AAPL)...');
        const aaplResponse = await fetch(`${API_BASE_URL}/api/search?q=AAPL`);
        const aaplData = await aaplResponse.json();
        
        console.log('🔍 Search query:', aaplData.query);
        console.log('📊 Data source:', aaplData.data_source);
        console.log('🌐 API integration:', aaplData.api_integration);
        console.log('📈 Results found:', aaplData.total);
        
        if (aaplData.results && aaplData.results.length > 0) {
            console.log('🍎 AAPL results:');
            aaplData.results.slice(0, 3).forEach((result, index) => {
                console.log(`   ${index + 1}. ${result.ticker} - ${result.name} (${result.exchange})`);
                console.log(`      Country: ${result.country}, Sector: ${result.sector}`);
            });
        }
        
        // Test 4: Search for a less common company
        console.log('\n4️⃣ Testing Less Common Company Search...');
        const uncommonResponse = await fetch(`${API_BASE_URL}/api/search?q=PALANTIR`);
        const uncommonData = await uncommonResponse.json();
        
        console.log('🔍 Search query:', uncommonData.query);
        console.log('📊 Data source:', uncommonData.data_source);
        console.log('📈 Results found:', uncommonData.total);
        
        if (uncommonData.results && uncommonData.results.length > 0) {
            console.log('🔮 Palantir results:');
            uncommonData.results.slice(0, 3).forEach((result, index) => {
                console.log(`   ${index + 1}. ${result.ticker} - ${result.name} (${result.exchange})`);
            });
        }
        
        // Test 5: Test analysis with streaming
        console.log('\n5️⃣ Testing Analysis with Streaming...');
        const analysisResponse = await fetch(`${API_BASE_URL}/api/analyze/AAPL?stream=true`, {
            headers: {
                'Accept': 'text/event-stream'
            }
        });
        
        console.log('📡 Analysis response status:', analysisResponse.status);
        console.log('📋 Content-Type:', analysisResponse.headers.get('content-type'));
        
        if (analysisResponse.ok) {
            const analysisText = await analysisResponse.text();
            console.log('📊 Analysis response length:', analysisText.length);
            
            // Parse the streaming response
            const lines = analysisText.split('\n');
            let progressCount = 0;
            let completionFound = false;
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'progress') {
                            progressCount++;
                        } else if (data.type === 'complete') {
                            completionFound = true;
                            console.log('✅ Analysis completed successfully');
                            console.log('💰 Fair value:', data.data?.fairValue);
                            console.log('💵 Current price:', data.data?.currentPrice);
                            console.log('🎯 Recommendation:', data.data?.recommendation);
                            console.log('🏢 Business type:', data.data?.businessType);
                        }
                    } catch (e) {
                        // Skip parsing errors
                    }
                }
            }
            
            console.log(`📈 Progress updates received: ${progressCount}`);
            console.log(`✅ Completion found: ${completionFound}`);
        }
        
        // Summary
        console.log('\n📋 SUMMARY');
        console.log('==========');
        
        const isUsingAPI = bellData.data_source === 'marketstack_api' || aaplData.data_source === 'marketstack_api';
        
        if (isUsingAPI) {
            console.log('✅ MarketStack API is ACTIVE and working');
            console.log('🌐 Search is using live API data');
            console.log('📊 Comprehensive ticker coverage available');
        } else {
            console.log('⚠️  MarketStack API is NOT active');
            console.log('💾 Using local database fallback');
            console.log('🔑 Check API key configuration');
        }
        
        console.log(`🔍 Bell Equipment searchable: ${bellData.results?.some(r => r.name.toLowerCase().includes('bell')) ? 'YES' : 'NO'}`);
        console.log(`📈 Analysis streaming: ${analysisResponse.ok ? 'WORKING' : 'FAILED'}`);
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        console.error('🔧 Make sure the backend server is running on', API_BASE_URL);
    }
}

// Run the test
testMarketStackAPI();