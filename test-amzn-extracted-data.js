/**
 * Test script to check what data was extracted for AMZN
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function checkAMZNExtractedData() {
    console.log('🔍 Checking AMZN extracted data...');
    
    try {
        const response = await fetch(`${API_BASE}/api/manual-data/AMZN`);
        const data = await response.json();
        
        console.log('Full response:');
        console.log(JSON.stringify(data, null, 2));
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run the test
checkAMZNExtractedData();