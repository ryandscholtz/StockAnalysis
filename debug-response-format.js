/**
 * Debug script to see the exact response format
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function debugResponseFormat() {
    console.log('🔍 Debugging Response Format...\n');
    
    try {
        const response = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        const responseText = await response.text();
        
        console.log('📊 Raw response:');
        console.log('---START---');
        console.log(responseText);
        console.log('---END---');
        
        console.log('\\n📊 Response as JSON:');
        console.log(JSON.stringify(responseText));
        
        console.log('\\n📊 Split by \\n:');
        const lines = responseText.split('\\n');
        lines.forEach((line, i) => {
            console.log(`Line ${i}: "${line}"`);
        });
        
    } catch (error) {
        console.error('❌ Error:', error);
    }
}

debugResponseFormat();