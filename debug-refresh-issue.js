/**
 * Comprehensive debugging script to identify why the UI refresh isn't working
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function debugRefreshIssue() {
    console.log('🔍 COMPREHENSIVE REFRESH DEBUG...\n');
    
    // Test 1: Check if the simple endpoint works
    console.log('1️⃣ Testing simple analysis endpoint:');
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze/AAPL`);
        const data = await response.json();
        console.log(`✅ Status: ${response.status}`);
        console.log(`💰 Current Price: $${data.currentPrice}`);
        console.log(`🎯 Fair Value: $${data.fairValue?.toFixed(2) || 'N/A'}`);
        console.log(`📊 Has Real Price: ${data.dataSource?.has_real_price || 'N/A'}`);
    } catch (error) {
        console.log(`❌ Simple endpoint error: ${error.message}`);
    }
    
    console.log('\n2️⃣ Testing streaming endpoint (should fail):');
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze/AAPL?stream=true`);
        console.log(`Status: ${response.status}`);
        if (response.status === 404) {
            console.log('✅ Streaming endpoint correctly returns 404 (expected)');
        } else {
            console.log('⚠️ Streaming endpoint unexpectedly works');
        }
    } catch (error) {
        console.log(`✅ Streaming endpoint error (expected): ${error.message}`);
    }
    
    console.log('\n3️⃣ Testing with force_refresh parameter:');
    try {
        const response = await fetch(`${API_BASE_URL}/api/analyze/AAPL?force_refresh=true`);
        const data = await response.json();
        console.log(`✅ Status: ${response.status}`);
        console.log(`💰 Current Price: $${data.currentPrice}`);
        console.log(`🎯 Fair Value: $${data.fairValue?.toFixed(2) || 'N/A'}`);
    } catch (error) {
        console.log(`❌ Force refresh error: ${error.message}`);
    }
    
    console.log('\n4️⃣ Testing multiple calls to see if data changes:');
    for (let i = 1; i <= 3; i++) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/analyze/AAPL?force_refresh=true&t=${Date.now()}`);
            const data = await response.json();
            console.log(`Call ${i}: Price=$${data.currentPrice}, Fair=$${data.fairValue?.toFixed(2) || 'N/A'}`);
        } catch (error) {
            console.log(`Call ${i}: Error - ${error.message}`);
        }
        
        if (i < 3) await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log('\n🎯 DIAGNOSIS:');
    console.log('If all calls show real prices ($259.37 for AAPL), the API is working.');
    console.log('If UI still shows $150.00, the issue is in the frontend.');
    
    console.log('\n🔧 NEXT STEPS:');
    console.log('1. Open browser dev tools (F12)');
    console.log('2. Go to Network tab');
    console.log('3. Click "Refresh Data" button');
    console.log('4. Check what URL is being called');
    console.log('5. Check the response data');
    console.log('6. Look for any JavaScript errors in Console tab');
    
    console.log('\n💡 POSSIBLE ISSUES:');
    console.log('- Browser caching the old response');
    console.log('- Frontend not calling the API at all');
    console.log('- Frontend calling wrong endpoint');
    console.log('- State not updating after API call');
    console.log('- Component not re-rendering after state change');
}

// Run the debug
debugRefreshIssue().catch(console.error);