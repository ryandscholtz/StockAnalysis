/**
 * Test Bell Equipment Analysis Data
 * Check what company name the analysis endpoint returns
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testBellEquipmentAnalysis() {
    console.log('🔍 Testing Bell Equipment Analysis Data');
    console.log('=====================================');
    
    try {
        // Test 1: Get watchlist item data for BEL.XJSE
        console.log('\n1️⃣ Testing Watchlist Item Data...');
        const watchlistResponse = await fetch(`${API_BASE_URL}/api/watchlist/BEL.XJSE`);
        
        if (watchlistResponse.ok) {
            const watchlistData = await watchlistResponse.json();
            console.log('📊 Watchlist item company name:', watchlistData.watchlist_item?.company_name);
            console.log('📊 Latest analysis company name:', watchlistData.latest_analysis?.companyName);
            console.log('📊 Latest analysis company_name:', watchlistData.latest_analysis?.company_name);
            console.log('📊 Current quote company name:', watchlistData.current_quote?.companyName);
        } else {
            console.log('❌ Watchlist item not found, trying to analyze directly...');
        }
        
        // Test 2: Run analysis for BEL.XJSE
        console.log('\n2️⃣ Testing Direct Analysis...');
        const analysisResponse = await fetch(`${API_BASE_URL}/api/analyze/BEL.XJSE`);
        
        if (analysisResponse.ok) {
            const analysisData = await analysisResponse.json();
            console.log('📊 Analysis company name (companyName):', analysisData.companyName);
            console.log('📊 Analysis company name (company_name):', analysisData.company_name);
            console.log('📊 Analysis ticker:', analysisData.ticker);
            console.log('📊 Analysis data source:', analysisData.data_source);
        } else {
            console.log('❌ Analysis failed');
        }
        
        // Test 3: Check what the Lambda's stock data function returns
        console.log('\n3️⃣ Testing Stock Data Function...');
        // The Lambda has a _get_stock_data_with_ratios function that should return company names
        // Let's see if we can infer what it's returning by checking a known stock
        
        const aaplAnalysisResponse = await fetch(`${API_BASE_URL}/api/analyze/AAPL`);
        if (aaplAnalysisResponse.ok) {
            const aaplData = await aaplAnalysisResponse.json();
            console.log('📊 AAPL company name for comparison:', aaplData.companyName);
            console.log('📊 AAPL has detailed data:', !!aaplData.companyName);
        }
        
        // Test 4: Check if BEL.XJSE is in the detailed stock database
        console.log('\n4️⃣ Analysis of the Issue...');
        console.log('🔍 The issue might be:');
        console.log('   1. BEL.XJSE is not in the Lambda\'s detailed stock database');
        console.log('   2. The Lambda falls back to basic API data or defaults');
        console.log('   3. The frontend prioritizes stored watchlist names over API names');
        
        console.log('\n💡 Solution:');
        console.log('   1. Update Lambda to use MarketStack API company names for all stocks');
        console.log('   2. Update frontend to prefer API company names over stored names');
        console.log('   3. Update stored watchlist items with correct company names');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Run the test
testBellEquipmentAnalysis();