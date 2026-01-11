/**
 * Test script to verify PDF upload functionality after the fix
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testPDFUploadEndpoint() {
    console.log('🧪 Testing PDF Upload Endpoint Fix...');
    
    try {
        // Test 1: Check if endpoint exists (GET should return 405 Method Not Allowed)
        console.log('\n1️⃣ Testing endpoint availability...');
        const getResponse = await fetch(`${API_BASE}/api/upload-pdf`);
        console.log(`GET /api/upload-pdf: ${getResponse.status} ${getResponse.statusText}`);
        
        if (getResponse.status === 405) {
            console.log('✅ Endpoint exists and correctly rejects GET requests');
        } else {
            console.log('❌ Unexpected response for GET request');
        }
        
        // Test 2: Test POST without file (should return 400)
        console.log('\n2️⃣ Testing POST without file...');
        const emptyPostResponse = await fetch(`${API_BASE}/api/upload-pdf?ticker=AAPL`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        console.log(`POST without file: ${emptyPostResponse.status} ${emptyPostResponse.statusText}`);
        const emptyResult = await emptyPostResponse.json();
        console.log('Response:', JSON.stringify(emptyResult, null, 2));
        
        // Test 3: Test with missing ticker
        console.log('\n3️⃣ Testing POST without ticker...');
        const noTickerResponse = await fetch(`${API_BASE}/api/upload-pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        console.log(`POST without ticker: ${noTickerResponse.status} ${noTickerResponse.statusText}`);
        const noTickerResult = await noTickerResponse.json();
        console.log('Response:', JSON.stringify(noTickerResult, null, 2));
        
        console.log('\n✅ Basic endpoint tests completed');
        console.log('📝 To test actual PDF upload, use the HTML test page with a real PDF file');
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run the test
testPDFUploadEndpoint();