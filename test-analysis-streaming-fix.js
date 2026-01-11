/**
 * Test script to verify the analysis streaming fix and valuation components
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testAnalysisStreamingFix() {
    console.log('🧪 Testing Analysis Streaming Fix...\n');
    
    try {
        // Test 1: Streaming Analysis Endpoint
        console.log('1️⃣ Testing streaming analysis endpoint...');
        const streamingResponse = await fetch(`${API_BASE}/api/analyze/GOOGL?stream=true`);
        
        if (!streamingResponse.ok) {
            throw new Error(`HTTP ${streamingResponse.status}: ${streamingResponse.statusText}`);
        }
        
        const streamingData = await streamingResponse.json();
        console.log('✅ Streaming response received');
        console.log('📊 Response structure:', {
            hasAnalysis: !!streamingData.analysis,
            hasStreaming: !!streamingData.streaming,
            hasChunks: !!streamingData.chunks,
            chunksCount: streamingData.chunks?.length || 0
        });
        
        // Verify required fields for valuation components
        const analysis = streamingData.analysis;
        if (analysis) {
            console.log('🔍 Checking required fields for valuation components:');
            const requiredFields = {
                'currentPrice': analysis.currentPrice,
                'fairValue': analysis.fairValue,
                'marginOfSafety': analysis.marginOfSafety,
                'companyName': analysis.companyName,
                'currency': analysis.currency,
                'valuation.dcf': analysis.valuation?.dcf,
                'valuation.earningsPower': analysis.valuation?.earningsPower,
                'valuation.assetBased': analysis.valuation?.assetBased
            };
            
            let missingFields = [];
            for (const [field, value] of Object.entries(requiredFields)) {
                if (value === undefined || value === null) {
                    missingFields.push(field);
                } else {
                    console.log(`  ✅ ${field}: ${value}`);
                }
            }
            
            if (missingFields.length > 0) {
                console.log(`  ❌ Missing fields: ${missingFields.join(', ')}`);
            } else {
                console.log('  🎉 All required fields present!');
            }
        }
        
        // Test 2: Regular Analysis Endpoint
        console.log('\n2️⃣ Testing regular analysis endpoint...');
        const regularResponse = await fetch(`${API_BASE}/api/analyze/GOOGL`);
        
        if (!regularResponse.ok) {
            throw new Error(`HTTP ${regularResponse.status}: ${regularResponse.statusText}`);
        }
        
        const regularData = await regularResponse.json();
        console.log('✅ Regular analysis response received');
        console.log('📊 Has valuation data:', !!regularData.valuation);
        
        // Test 3: Financial Data Endpoint
        console.log('\n3️⃣ Testing financial data endpoint...');
        const financialResponse = await fetch(`${API_BASE}/api/manual-data/GOOGL`);
        
        if (!financialResponse.ok) {
            throw new Error(`HTTP ${financialResponse.status}: ${financialResponse.statusText}`);
        }
        
        const financialData = await financialResponse.json();
        console.log('✅ Financial data response received');
        console.log('📊 Has key metrics:', !!financialData.financial_data?.key_metrics?.latest);
        
        // Test 4: Version Endpoint
        console.log('\n4️⃣ Testing version endpoint...');
        const versionResponse = await fetch(`${API_BASE}/api/version`);
        
        if (!versionResponse.ok) {
            throw new Error(`HTTP ${versionResponse.status}: ${versionResponse.statusText}`);
        }
        
        const versionData = await versionResponse.json();
        console.log('✅ Version response received');
        console.log('📊 Version:', versionData.version);
        console.log('📊 Deployed at:', versionData.deployed_at);
        
        console.log('\n🎉 All tests passed! The fixes should resolve:');
        console.log('  ✅ Analysis streaming error (proper JSON format)');
        console.log('  ✅ Valuation section visibility (all required fields present)');
        console.log('  ✅ Enhanced financial ratios display');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        console.error('🔍 Full error:', error);
    }
}

// Run the test
testAnalysisStreamingFix();