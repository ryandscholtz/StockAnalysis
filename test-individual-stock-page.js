// Test the individual stock page data flow
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

console.log('🔍 Testing Individual Stock Page Data Flow');
console.log('==========================================');

async function testIndividualStockPage() {
    try {
        console.log('\n1️⃣ Testing watchlist item endpoint (what loads first)...');
        
        const watchlistResponse = await fetch(`${API_URL}/api/watchlist/BEL.XJSE`);
        const watchlistData = await watchlistResponse.json();
        
        if (watchlistResponse.ok) {
            console.log('✅ Watchlist item loaded:');
            console.log('   Company Name:', watchlistData.company_name);
            console.log('   Ticker:', watchlistData.ticker);
            console.log('   Has latest_analysis:', !!watchlistData.latest_analysis);
            
            if (watchlistData.latest_analysis) {
                console.log('   Analysis Company Name:', watchlistData.latest_analysis.companyName);
                console.log('   Analysis Company Name (alt):', watchlistData.latest_analysis.company_name);
            } else {
                console.log('   ❌ No latest_analysis in watchlist data');
            }
        } else {
            console.log('❌ Watchlist item failed:', watchlistData.message);
            return;
        }
        
        console.log('\n2️⃣ Testing analysis endpoint (what loads when "Run Analysis" is clicked)...');
        
        const analysisResponse = await fetch(`${API_URL}/api/analyze/BEL.XJSE`);
        const analysisData = await analysisResponse.json();
        
        if (analysisResponse.ok) {
            console.log('✅ Analysis data loaded:');
            console.log('   Company Name (companyName):', analysisData.companyName);
            console.log('   Company Name (company_name):', analysisData.company_name);
            console.log('   Ticker:', analysisData.ticker);
        } else {
            console.log('❌ Analysis failed:', analysisData.message);
        }
        
        console.log('\n3️⃣ Simulating frontend page load logic...');
        
        // This simulates what happens when the page first loads
        // Based on frontend/app/watchlist/[ticker]/page.tsx line 415
        
        // Initial state: only watchlist data, no analysis yet
        const initialAnalysis = watchlistData.latest_analysis || null;
        const initialWatchlistData = { watchlist_item: watchlistData };
        const ticker = 'BEL.XJSE';
        
        const initialCompanyName = initialAnalysis?.companyName || 
                                 initialAnalysis?.company_name || 
                                 initialWatchlistData?.watchlist_item?.company_name || 
                                 ticker;
        
        console.log('   Initial page load (before analysis):');
        console.log('     Analysis data:', !!initialAnalysis);
        console.log('     Watchlist company name:', initialWatchlistData?.watchlist_item?.company_name);
        console.log('     Displayed company name:', initialCompanyName);
        console.log('     Expected: BELL EQUIPMENT LTD');
        console.log('     Status:', initialCompanyName === 'BELL EQUIPMENT LTD' ? '✅ CORRECT' : '❌ INCORRECT');
        
        // After running analysis
        if (analysisResponse.ok) {
            const afterAnalysisCompanyName = analysisData?.companyName || 
                                           analysisData?.company_name || 
                                           initialWatchlistData?.watchlist_item?.company_name || 
                                           ticker;
            
            console.log('\n   After running analysis:');
            console.log('     Analysis company name:', analysisData?.companyName);
            console.log('     Final displayed name:', afterAnalysisCompanyName);
            console.log('     Expected: BELL EQUIPMENT LTD');
            console.log('     Status:', afterAnalysisCompanyName === 'BELL EQUIPMENT LTD' ? '✅ CORRECT' : '❌ INCORRECT');
        }
        
        console.log('\n💡 DIAGNOSIS:');
        if (initialCompanyName === 'BELL EQUIPMENT LTD') {
            console.log('   ✅ The individual stock page should show the correct name immediately');
            console.log('   ✅ No need to run analysis first');
        } else {
            console.log('   ❌ Issue found: Individual stock page shows wrong name on initial load');
            console.log('   🔍 Root cause: watchlist item data has wrong company name');
            console.log('   💡 Solution needed: Update watchlist item to include correct company name');
            
            if (analysisResponse.ok && analysisData.companyName === 'BELL EQUIPMENT LTD') {
                console.log('   ✅ Analysis data is correct, so running analysis fixes the display');
                console.log('   🔧 Need to ensure watchlist item includes latest_analysis data');
            }
        }
        
    } catch (error) {
        console.error('❌ Error testing individual stock page:', error.message);
    }
}

testIndividualStockPage();