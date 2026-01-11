// Test the fixed data structure
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

console.log('🔍 Testing Fixed Data Structure');
console.log('==============================');

async function testFixedDataStructure() {
    try {
        console.log('\n1️⃣ Testing BEL.XJSE with new data structure...');
        
        const response = await fetch(`${API_URL}/api/watchlist/BEL.XJSE`);
        const data = await response.json();
        
        console.log('📊 API Response Structure:');
        console.log('   Has watchlist_item wrapper:', !!data.watchlist_item);
        console.log('   Has latest_analysis:', !!data.latest_analysis);
        console.log('   Has cache_info:', !!data.cache_info);
        
        if (data.watchlist_item) {
            console.log('\n📋 Watchlist Item Data:');
            console.log('   Company Name:', data.watchlist_item.company_name);
            console.log('   Ticker:', data.watchlist_item.ticker);
            console.log('   Current Price:', data.watchlist_item.current_price);
        }
        
        console.log('\n2️⃣ Simulating frontend logic with correct structure...');
        
        // This is how the frontend should process the data
        const analysis = data.latest_analysis || null;
        const watchlistData = data; // The whole response
        const ticker = 'BEL.XJSE';
        
        // Frontend logic from page.tsx line 415
        const companyName = analysis?.companyName || 
                           analysis?.company_name || 
                           watchlistData?.watchlist_item?.company_name || 
                           ticker;
        
        console.log('   Analysis company name:', analysis?.companyName || 'undefined');
        console.log('   Watchlist company name:', watchlistData?.watchlist_item?.company_name || 'undefined');
        console.log('   Final display name:', companyName);
        console.log('   Expected: BELL EQUIPMENT LTD');
        console.log('   Status:', companyName === 'BELL EQUIPMENT LTD' ? '✅ CORRECT' : '❌ INCORRECT');
        
        console.log('\n3️⃣ Testing MSFT for comparison...');
        
        const msftResponse = await fetch(`${API_URL}/api/watchlist/MSFT`);
        const msftData = await msftResponse.json();
        
        const msftAnalysis = msftData.latest_analysis || null;
        const msftCompanyName = msftAnalysis?.companyName || 
                               msftAnalysis?.company_name || 
                               msftData?.watchlist_item?.company_name || 
                               'MSFT';
        
        console.log('   MSFT company name:', msftData?.watchlist_item?.company_name || 'undefined');
        console.log('   MSFT final display:', msftCompanyName);
        console.log('   MSFT should show as:', `${msftCompanyName} (MSFT)`);
        
        console.log('\n4️⃣ Summary...');
        
        if (companyName === 'BELL EQUIPMENT LTD' && msftCompanyName === 'Microsoft Corporation') {
            console.log('   ✅ DATA STRUCTURE FIX SUCCESSFUL!');
            console.log('   ✅ BEL.XJSE should now show: BELL EQUIPMENT LTD (BEL.XJSE)');
            console.log('   ✅ MSFT should now show: Microsoft Corporation (MSFT)');
            console.log('');
            console.log('   🎉 The Ticker (Ticker) issue has been resolved!');
            console.log('   💡 If you still see the old display, clear your browser cache.');
        } else {
            console.log('   ❌ Issue still exists:');
            console.log('     BEL.XJSE result:', companyName);
            console.log('     MSFT result:', msftCompanyName);
        }
        
    } catch (error) {
        console.error('❌ Error testing fixed data structure:', error.message);
    }
}

testFixedDataStructure();