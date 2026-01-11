/**
 * Debug Lambda Analysis for BEL.XJSE
 * Test the analysis endpoint step by step
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function debugLambdaAnalysis() {
    console.log('🔍 Debugging Lambda Analysis for BEL.XJSE');
    console.log('==========================================');
    
    try {
        // Test 1: Try analysis without streaming first
        console.log('\n1️⃣ Testing Regular Analysis Endpoint...');
        const analysisResponse = await fetch(`${API_BASE_URL}/api/analyze/BEL.XJSE`);
        
        console.log('📊 Response status:', analysisResponse.status);
        console.log('📊 Response headers:', Object.fromEntries(analysisResponse.headers.entries()));
        
        if (analysisResponse.ok) {
            const analysisData = await analysisResponse.json();
            console.log('✅ Analysis succeeded!');
            console.log('📊 Company name:', analysisData.companyName || analysisData.company_name);
            console.log('📊 Ticker:', analysisData.ticker);
            console.log('📊 Current price:', analysisData.currentPrice);
            console.log('📊 Fair value:', analysisData.fairValue);
        } else {
            const errorText = await analysisResponse.text();
            console.log('❌ Analysis failed');
            console.log('📊 Error response:', errorText);
        }
        
        // Test 2: Try streaming analysis
        console.log('\n2️⃣ Testing Streaming Analysis Endpoint...');
        const streamResponse = await fetch(`${API_BASE_URL}/api/analyze/BEL.XJSE?stream=true`, {
            headers: {
                'Accept': 'text/event-stream'
            }
        });
        
        console.log('📊 Stream response status:', streamResponse.status);
        
        if (streamResponse.ok) {
            const streamText = await streamResponse.text();
            console.log('📊 Stream response length:', streamText.length);
            
            // Parse streaming response
            const lines = streamText.split('\n');
            let foundCompletion = false;
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.type === 'complete' && data.data) {
                            foundCompletion = true;
                            console.log('✅ Streaming analysis completed!');
                            console.log('📊 Company name:', data.data.companyName || data.data.company_name);
                            console.log('📊 Current price:', data.data.currentPrice);
                            console.log('📊 Fair value:', data.data.fairValue);
                            break;
                        } else if (data.type === 'error') {
                            console.log('❌ Streaming analysis error:', data.message);
                            break;
                        }
                    } catch (e) {
                        // Skip parsing errors
                    }
                }
            }
            
            if (!foundCompletion) {
                console.log('❌ No completion found in stream');
                console.log('📊 First 500 chars:', streamText.substring(0, 500));
            }
        } else {
            const streamError = await streamResponse.text();
            console.log('❌ Streaming failed:', streamError);
        }
        
        // Test 3: Try a known working ticker for comparison
        console.log('\n3️⃣ Testing AAPL Analysis for Comparison...');
        const aaplResponse = await fetch(`${API_BASE_URL}/api/analyze/AAPL`);
        
        if (aaplResponse.ok) {
            const aaplData = await aaplResponse.json();
            console.log('✅ AAPL analysis works');
            console.log('📊 AAPL company name:', aaplData.companyName);
            console.log('📊 AAPL has detailed data:', !!aaplData.companyName);
        }
        
        console.log('\n💡 DIAGNOSIS');
        console.log('=============');
        console.log('If BEL.XJSE analysis fails but AAPL works, the issue is:');
        console.log('1. BEL.XJSE is not in the detailed stock database');
        console.log('2. The _get_basic_stock_data_from_api function is failing');
        console.log('3. The MarketStack API call in the Lambda is not working');
        console.log('');
        console.log('If both fail, there might be a broader Lambda issue.');
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Run the test
debugLambdaAnalysis();