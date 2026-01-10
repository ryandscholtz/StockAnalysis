// Test script to verify business type mapping for multiple tickers
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testBusinessTypeMapping() {
    const testCases = [
        { ticker: 'KO', expected: 'Mature', expectedWeights: [50, 35, 15] },
        { ticker: 'AAPL', expected: 'Technology', expectedWeights: [50, 35, 15] },
        { ticker: 'TSLA', expected: 'High Growth', expectedWeights: [55, 25, 20] },
        { ticker: 'JPM', expected: 'Bank', expectedWeights: [25, 50, 25] },
        { ticker: 'XYZ', expected: 'Default', expectedWeights: [50, 35, 15] } // Non-existent ticker should use default
    ];
    
    console.log('🧪 Testing Business Type Mapping...\n');
    
    for (const testCase of testCases) {
        try {
            console.log(`Testing ${testCase.ticker}...`);
            
            const response = await fetch(`${API_BASE_URL}/api/analyze/${testCase.ticker}`);
            
            if (!response.ok) {
                console.log(`❌ ${testCase.ticker}: HTTP ${response.status}`);
                continue;
            }
            
            const data = await response.json();
            
            const actualBusinessType = data.businessType;
            const actualWeights = data.analysisWeights ? [
                Math.round(data.analysisWeights.dcf_weight * 100),
                Math.round(data.analysisWeights.epv_weight * 100),
                Math.round(data.analysisWeights.asset_weight * 100)
            ] : null;
            
            const businessTypeMatch = actualBusinessType === testCase.expected;
            const weightsMatch = actualWeights && 
                actualWeights[0] === testCase.expectedWeights[0] &&
                actualWeights[1] === testCase.expectedWeights[1] &&
                actualWeights[2] === testCase.expectedWeights[2];
            
            const status = businessTypeMatch && weightsMatch ? '✅' : '❌';
            
            console.log(`${status} ${testCase.ticker}:`);
            console.log(`   Business Type: ${actualBusinessType} (expected: ${testCase.expected})`);
            console.log(`   Weights: DCF ${actualWeights?.[0] || 'N/A'}%, EPV ${actualWeights?.[1] || 'N/A'}%, Asset ${actualWeights?.[2] || 'N/A'}%`);
            console.log(`   Expected: DCF ${testCase.expectedWeights[0]}%, EPV ${testCase.expectedWeights[1]}%, Asset ${testCase.expectedWeights[2]}%`);
            
            if (!businessTypeMatch) {
                console.log(`   ⚠️  Business type mismatch!`);
            }
            if (!weightsMatch) {
                console.log(`   ⚠️  Weights mismatch!`);
            }
            
            console.log('');
            
            // Add delay between requests
            await new Promise(resolve => setTimeout(resolve, 1000));
            
        } catch (error) {
            console.log(`❌ ${testCase.ticker}: Error - ${error.message}\n`);
        }
    }
    
    console.log('🏁 Business type mapping test completed!');
}

testBusinessTypeMapping();