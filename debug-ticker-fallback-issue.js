// Debug why the frontend is showing Ticker (Ticker) instead of Company Name (Ticker)
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

console.log('🔍 Debugging Ticker (Ticker) Display Issue');
console.log('==========================================');

async function debugTickerFallback() {
    try {
        console.log('\n1️⃣ Testing what the frontend should receive...');
        
        // Test the watchlist item endpoint (what loads when page opens)
        const watchlistResponse = await fetch(`${API_URL}/api/watchlist/BEL.XJSE`);
        const watchlistData = await watchlistResponse.json();
        
        console.log('📊 Watchlist API Response:');
        console.log('   Status:', watchlistResponse.status);
        console.log('   Company Name:', watchlistData.company_name);
        console.log('   Ticker:', watchlistData.ticker);
        console.log('   Has latest_analysis:', !!watchlistData.latest_analysis);
        
        if (watchlistData.latest_analysis) {
            console.log('   Analysis Company Name:', watchlistData.latest_analysis.companyName);
        }
        
        console.log('\n2️⃣ Simulating frontend data structure...');
        
        // This is how the frontend structures the data
        const analysis = watchlistData.latest_analysis || null;
        const watchlistItem = { watchlist_item: watchlistData };
        const ticker = 'BEL.XJSE';
        
        console.log('📋 Frontend Data Structure:');
        console.log('   analysis:', analysis);
        console.log('   watchlistData.watchlist_item:', watchlistItem.watchlist_item);
        console.log('   ticker:', ticker);
        
        console.log('\n3️⃣ Step-by-step priority evaluation...');
        
        const step1 = analysis?.companyName;
        const step2 = analysis?.company_name;
        const step3 = watchlistItem?.watchlist_item?.company_name;
        const step4 = ticker;
        
        console.log('   1. analysis?.companyName =', step1 || 'undefined');
        console.log('   2. analysis?.company_name =', step2 || 'undefined');
        console.log('   3. watchlistData?.watchlist_item?.company_name =', step3 || 'undefined');
        console.log('   4. ticker =', step4);
        
        const finalResult = step1 || step2 || step3 || step4;
        console.log('\n   Final result:', finalResult);
        console.log('   Expected: BELL EQUIPMENT LTD');
        console.log('   Status:', finalResult === 'BELL EQUIPMENT LTD' ? '✅ CORRECT' : '❌ INCORRECT');
        
        console.log('\n4️⃣ Diagnosis...');
        
        if (finalResult === ticker) {
            console.log('   🔍 ISSUE FOUND: All company name sources are undefined!');
            console.log('   📋 This explains why you see "BEL.XJSE (BEL.XJSE)"');
            console.log('');
            console.log('   🔧 Root Cause Analysis:');
            
            if (!step1 && !step2) {
                console.log('   ❌ No analysis data loaded (analysis is null)');
                console.log('   💡 This is normal on initial page load');
            }
            
            if (!step3) {
                console.log('   ❌ watchlistData.watchlist_item.company_name is undefined');
                console.log('   💡 This should NOT be undefined - API returns company_name');
                console.log('   🔍 Possible causes:');
                console.log('      - Frontend API call is failing');
                console.log('      - Data structure mismatch');
                console.log('      - Caching issue preventing fresh data');
            }
            
            console.log('\n   🛠️ SOLUTION:');
            console.log('   The API is returning the correct data, but the frontend isn\'t receiving it.');
            console.log('   This is likely a browser cache or data loading issue.');
            
        } else if (finalResult === 'BELL EQUIPMENT LTD') {
            console.log('   ✅ Logic is working correctly!');
            console.log('   💡 If you still see wrong display, it\'s a browser cache issue.');
        }
        
        console.log('\n5️⃣ Testing MSFT for comparison...');
        
        try {
            const msftResponse = await fetch(`${API_URL}/api/watchlist/MSFT`);
            const msftData = await msftResponse.json();
            
            const msftAnalysis = msftData.latest_analysis || null;
            const msftWatchlistItem = { watchlist_item: msftData };
            const msftTicker = 'MSFT';
            
            const msftCompanyName = msftAnalysis?.companyName || 
                                  msftAnalysis?.company_name || 
                                  msftWatchlistItem?.watchlist_item?.company_name || 
                                  msftTicker;
            
            console.log('   MSFT API company_name:', msftData.company_name);
            console.log('   MSFT final display:', msftCompanyName);
            console.log('   MSFT shows as:', msftCompanyName === msftTicker ? 'MSFT (MSFT)' : `${msftCompanyName} (MSFT)`);
            
            if (msftCompanyName === msftTicker) {
                console.log('   🔍 MSFT also shows Ticker (Ticker) - this confirms the pattern!');
                console.log('   💡 The issue affects all stocks, not just BEL.XJSE');
            }
            
        } catch (error) {
            console.log('   ❌ Could not test MSFT:', error.message);
        }
        
    } catch (error) {
        console.error('❌ Error debugging ticker fallback:', error.message);
    }
}

debugTickerFallback();