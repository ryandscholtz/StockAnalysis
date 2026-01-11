// Test the actual frontend company name display issue
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

console.log('🔍 Testing Frontend Company Name Display Issue');
console.log('==============================================');

async function testFrontendFlow() {
    try {
        console.log('\n1️⃣ Testing if BEL.XJSE is in the main watchlist...');
        
        const watchlistResponse = await fetch(`${API_URL}/api/watchlist`);
        const watchlistData = await watchlistResponse.json();
        
        console.log('📊 Watchlist items found:', watchlistData.items?.length || 0);
        
        const belItem = watchlistData.items?.find(item => item.ticker === 'BEL.XJSE');
        if (belItem) {
            console.log('✅ BEL.XJSE found in watchlist:');
            console.log('   Company Name:', belItem.company_name);
            console.log('   Ticker:', belItem.ticker);
        } else {
            console.log('❌ BEL.XJSE NOT found in main watchlist');
            console.log('   Available tickers:', watchlistData.items?.map(item => item.ticker).join(', '));
        }
        
        console.log('\n2️⃣ Testing individual watchlist item endpoint...');
        
        const itemResponse = await fetch(`${API_URL}/api/watchlist/BEL.XJSE`);
        const itemData = await itemResponse.json();
        
        if (itemResponse.ok) {
            console.log('✅ Individual watchlist item found:');
            console.log('   Company Name:', itemData.company_name);
            console.log('   Ticker:', itemData.ticker);
            console.log('   Has latest_analysis:', !!itemData.latest_analysis);
            
            if (itemData.latest_analysis) {
                console.log('   Analysis Company Name:', itemData.latest_analysis.companyName);
            }
        } else {
            console.log('❌ Individual watchlist item failed:', itemData.message);
        }
        
        console.log('\n3️⃣ Testing direct analysis endpoint...');
        
        const analysisResponse = await fetch(`${API_URL}/api/analyze/BEL.XJSE`);
        const analysisData = await analysisResponse.json();
        
        if (analysisResponse.ok) {
            console.log('✅ Analysis endpoint working:');
            console.log('   Company Name (companyName):', analysisData.companyName);
            console.log('   Company Name (company_name):', analysisData.company_name);
            console.log('   Ticker:', analysisData.ticker);
        } else {
            console.log('❌ Analysis endpoint failed:', analysisData.message);
        }
        
        console.log('\n4️⃣ Frontend Logic Simulation...');
        
        // Simulate the frontend logic from page.tsx
        const analysis = analysisResponse.ok ? analysisData : null;
        const watchlistItem = itemResponse.ok ? { watchlist_item: itemData } : null;
        const ticker = 'BEL.XJSE';
        
        // This is the exact logic from frontend/app/watchlist/[ticker]/page.tsx line 415
        const companyName = analysis?.companyName || analysis?.company_name || watchlistItem?.watchlist_item?.company_name || ticker;
        
        console.log('   Analysis data available:', !!analysis);
        console.log('   Watchlist data available:', !!watchlistItem);
        console.log('   Final company name:', companyName);
        console.log('   Expected: BELL EQUIPMENT LTD');
        console.log('   Status:', companyName === 'BELL EQUIPMENT LTD' ? '✅ CORRECT' : '❌ INCORRECT');
        
        console.log('\n💡 DIAGNOSIS:');
        if (companyName === 'BELL EQUIPMENT LTD') {
            console.log('   ✅ The backend is working correctly!');
            console.log('   ✅ The frontend logic should display the correct name.');
            console.log('   🔍 If the frontend still shows wrong name, check:');
            console.log('      - Browser cache (hard refresh: Ctrl+F5)');
            console.log('      - Frontend dev server restart');
            console.log('      - Check if BEL.XJSE is actually in your local watchlist');
        } else {
            console.log('   ❌ Issue found in the data flow:');
            console.log('      - Analysis company name:', analysis?.companyName);
            console.log('      - Watchlist company name:', watchlistItem?.watchlist_item?.company_name);
            console.log('      - Need to investigate further...');
        }
        
    } catch (error) {
        console.error('❌ Error testing frontend flow:', error.message);
    }
}

testFrontendFlow();