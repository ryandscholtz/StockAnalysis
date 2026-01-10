// Test the updated fair value logic
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testFairValue() {
    console.log('🧪 Testing Fair Value Fix...\n');
    
    try {
        // Test with AAPL
        console.log('📊 Testing AAPL analysis...');
        const response = await fetch(`${API_URL}/api/analyze/AAPL`);
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

testFairValue();