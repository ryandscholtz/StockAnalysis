// Test the updated fair value logic with force refresh
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testFairValueForceRefresh() {
    console.log('🧪 Testing Fair Value Fix with Force Refresh...\n');
    
    try {
        // Test with AAPL and force refresh
        console.log('📊 Testing AAPL analysis with force_refresh=true...');
        const response = await fetch(`${API_URL}/api/analyze/AAPL?force_refresh=true`);
        const data = await response.json();
        
        console.log('Response status:', response.status);
        console.log('Ticker:', data.ticker);
        console.log('Fair Value:', data.fairValue);
        console.log('Margin of Safety:', data.marginOfSafety);
        console.log('Recommendation:', data.recommendation);
        console.log('Recommendation Reasoning:', data.recommendationReasoning);
        console.log('Missing Data:', data.missingData);
        console.log('Valuation breakdown:', data.valuation);
        
        // Check if fair value is null or a calculated value
        if (data.fairValue === null) {
            console.log('✅ Fair value is correctly null (no financial data)');
        } else {
            console.log('⚠️ Fair value is calculated:', data.fairValue);
            console.log('   This suggests the calculation functions are still returning dummy values');
        }
        
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

testFairValueForceRefresh();