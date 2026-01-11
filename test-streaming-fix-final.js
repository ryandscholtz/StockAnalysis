/**
 * Test script to verify streaming analysis fix
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testStreamingFix() {
    console.log('🧪 Testing Streaming Analysis Fix...\n');
    
    try {
        console.log('1️⃣ Testing AMZN streaming analysis...');
        const response = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        
        if (!response.ok) {
            console.log(`❌ Request failed: ${response.status}`);
            return;
        }
        
        console.log('✅ Response received');
        console.log('📊 Status:', response.status);
        console.log('📊 Content-Type:', response.headers.get('content-type'));
        
        const responseText = await response.text();
        console.log('📊 Response length:', responseText.length);
        
        // Check if response is in SSE format
        const isSSEFormat = responseText.includes('data: ');
        console.log('📊 Is SSE format:', isSSEFormat);
        
        // Parse SSE chunks
        const lines = responseText.split('\\n');
        const dataLines = lines.filter(line => line.startsWith('data: '));
        console.log('📊 Number of data chunks:', dataLines.length);
        
        let hasProgressMessages = false;
        let hasCompletionMessage = false;
        let completionData = null;
        
        for (const line of dataLines) {
            try {
                const data = JSON.parse(line.slice(6)); // Remove 'data: ' prefix
                
                if (data.type === 'progress') {
                    hasProgressMessages = true;
                    console.log(`📈 Progress: Step ${data.step} - ${data.message} (${data.progress}%)`);
                } else if (data.type === 'complete') {
                    hasCompletionMessage = true;
                    completionData = data.data;
                    console.log('✅ Completion message found!');
                    console.log('📊 Analysis data keys:', Object.keys(completionData || {}));
                }
            } catch (e) {
                console.log('⚠️ Could not parse line:', line.substring(0, 100));
            }
        }
        
        console.log('\\n📋 Test Results:');
        console.log('✅ SSE Format:', isSSEFormat ? 'Yes' : 'No');
        console.log('✅ Progress Messages:', hasProgressMessages ? 'Yes' : 'No');
        console.log('✅ Completion Message:', hasCompletionMessage ? 'Yes' : 'No');
        
        if (hasCompletionMessage && completionData) {
            console.log('\\n📊 Analysis Results:');
            console.log('📊 Ticker:', completionData.ticker);
            console.log('📊 Company:', completionData.companyName);
            console.log('📊 Current Price:', completionData.currentPrice);
            console.log('📊 Fair Value:', completionData.fairValue);
            console.log('📊 Recommendation:', completionData.recommendation);
            console.log('📊 Margin of Safety:', completionData.marginOfSafety + '%');
        }
        
        if (hasCompletionMessage) {
            console.log('\\n🎉 STREAMING FIX SUCCESSFUL!');
            console.log('✅ Frontend should no longer show \"Stream ended without completion\" error');
        } else {
            console.log('\\n❌ STREAMING FIX FAILED');
            console.log('❌ Completion message still missing');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
        console.error('🔍 Full error:', error);
    }
}

// Run the test
testStreamingFix();