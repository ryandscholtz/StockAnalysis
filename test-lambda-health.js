// Test Lambda health and basic functionality
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testLambdaHealth() {
    try {
        console.log('🏥 Testing Lambda health...');
        
        // Test health endpoint
        const healthResponse = await fetch(`${API_BASE_URL}/health`);
        console.log(`Health endpoint status: ${healthResponse.status}`);
        
        if (healthResponse.ok) {
            const healthData = await healthResponse.json();
            console.log('Health data:', healthData);
        } else {
            console.log('Health check failed:', await healthResponse.text());
        }
        
        // Test a simple analysis
        console.log('\n🧪 Testing KO analysis...');
        const analysisResponse = await fetch(`${API_BASE_URL}/api/analyze/KO`);
        console.log(`Analysis endpoint status: ${analysisResponse.status}`);
        
        if (analysisResponse.ok) {
            const analysisData = await analysisResponse.json();
            console.log('Analysis data keys:', Object.keys(analysisData));
            console.log('Business Type:', analysisData.businessType);
            console.log('Analysis Weights:', analysisData.analysisWeights);
            console.log('Current Price:', analysisData.currentPrice);
            console.log('Fair Value:', analysisData.fairValue);
        } else {
            const errorText = await analysisResponse.text();
            console.log('Analysis failed:', errorText);
        }
        
    } catch (error) {
        console.error('❌ Error testing Lambda:', error.message);
    }
}

testLambdaHealth();