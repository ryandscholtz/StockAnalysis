/**
 * Test script to verify AMZN endpoints are working
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testAMZNEndpoints() {
    console.log('🧪 Testing AMZN Endpoints...\n');
    
    try {
        // Test 1: Watchlist endpoint for AMZN
        console.log('1️⃣ Testing AMZN watchlist endpoint...');
        const watchlistResponse = await fetch(`${API_BASE}/api/watchlist/AMZN`);
        
        if (watchlistResponse.ok) {
            const watchlistData = await watchlistResponse.json();
            console.log('✅ AMZN watchlist data received');
            console.log('📊 Company:', watchlistData.company_name);
            console.log('📊 Current Price:', watchlistData.current_price);
            console.log('📊 Fair Value:', watchlistData.fair_value);
            console.log('📊 Recommendation:', watchlistData.recommendation);
        } else {
            console.log(`❌ Watchlist failed: ${watchlistResponse.status}`);
        }
        
        // Test 2: Financial data endpoint for AMZN
        console.log('\n2️⃣ Testing AMZN financial data endpoint...');
        const financialResponse = await fetch(`${API_BASE}/api/manual-data/AMZN`);
        
        if (financialResponse.ok) {
            const financialData = await financialResponse.json();
            console.log('✅ AMZN financial data received');
            console.log('📊 Revenue:', financialData.financial_data?.income_statement?.revenue);
            console.log('📊 Net Income:', financialData.financial_data?.income_statement?.net_income);
            console.log('📊 P/E Ratio:', financialData.financial_data?.key_metrics?.latest?.pe_ratio);
        } else {
            console.log(`❌ Financial data failed: ${financialResponse.status}`);
        }
        
        // Test 3: Analysis endpoint for AMZN
        console.log('\n3️⃣ Testing AMZN analysis endpoint...');
        const analysisResponse = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        
        if (analysisResponse.ok) {
            const analysisData = await analysisResponse.json();
            console.log('✅ AMZN analysis data received');
            console.log('📊 Analysis available:', !!analysisData.analysis);
            if (analysisData.analysis) {
                console.log('📊 Current Price:', analysisData.analysis.currentPrice);
                console.log('📊 Fair Value:', analysisData.analysis.fairValue);
                console.log('📊 Margin of Safety:', analysisData.analysis.marginOfSafety + '%');
                console.log('📊 Recommendation:', analysisData.analysis.recommendation);
            }
        } else {
            console.log(`❌ Analysis failed: ${analysisResponse.status}`);
        }
        
        // Test 4: Check if AMZN is in the main watchlist
        console.log('\n4️⃣ Testing main watchlist includes AMZN...');
        const mainWatchlistResponse = await fetch(`${API_BASE}/api/watchlist`);
        
        if (mainWatchlistResponse.ok) {
            const mainWatchlistData = await mainWatchlistResponse.json();
            const amznInList = mainWatchlistData.items?.some(item => item.ticker === 'AMZN');
            console.log('✅ Main watchlist received');
            console.log('📊 AMZN in watchlist:', amznInList ? 'Yes' : 'No');
            console.log('📊 Total items:', mainWatchlistData.items?.length || 0);
        } else {
            console.log(`❌ Main watchlist failed: ${mainWatchlistResponse.status}`);
        }
        
        console.log('\n🎉 AMZN endpoint tests completed!');
        console.log('✅ AMZN should now be accessible in the frontend');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        console.error('🔍 Full error:', error);
    }
}

// Run the test
testAMZNEndpoints();