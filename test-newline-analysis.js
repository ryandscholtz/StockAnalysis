/**
 * Analyze the exact newline characters
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testNewlineAnalysis() {
    console.log('🔍 Analyzing Newline Characters...\n');
    
    try {
        const response = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        const text = await response.text();
        
        console.log('📊 Response length:', text.length);
        
        // Check for different newline types
        const lfCount = (text.match(/\\n/g) || []).length;
        const crlfCount = (text.match(/\\r\\n/g) || []).length;
        const crCount = (text.match(/\\r/g) || []).length;
        
        console.log(`📊 \\n (LF) count: ${lfCount}`);
        console.log(`📊 \\r\\n (CRLF) count: ${crlfCount}`);
        console.log(`📊 \\r (CR) count: ${crCount}`);
        
        // Try different split methods
        console.log('\\n📊 Testing different split methods:');
        
        const splitByLF = text.split('\\n');
        console.log(`Split by \\n: ${splitByLF.length} parts`);
        
        const splitByDoubleLF = text.split('\\n\\n');
        console.log(`Split by \\n\\n: ${splitByDoubleLF.length} parts`);
        
        const splitByCRLF = text.split('\\r\\n');
        console.log(`Split by \\r\\n: ${splitByCRLF.length} parts`);
        
        const splitByDoubleCRLF = text.split('\\r\\n\\r\\n');
        console.log(`Split by \\r\\n\\r\\n: ${splitByDoubleCRLF.length} parts`);
        
        // Show first few parts of the most promising split
        if (splitByDoubleLF.length > 1) {
            console.log('\\n📊 Parts from \\n\\n split:');
            splitByDoubleLF.slice(0, 3).forEach((part, i) => {
                if (part.trim()) {
                    console.log(`Part ${i}: "${part.trim()}"`);
                }
            });
        } else if (splitByLF.length > 1) {
            console.log('\\n📊 First few lines from \\n split:');
            splitByLF.slice(0, 10).forEach((line, i) => {
                console.log(`Line ${i}: "${line}"`);
            });
        }
        
        // Check if we can find data: lines
        const dataLines = splitByLF.filter(line => line.trim().startsWith('data: '));
        console.log(`\\n📊 Found ${dataLines.length} data: lines`);
        
        dataLines.forEach((line, i) => {
            try {
                const jsonStr = line.trim().slice(6); // Remove 'data: '
                const data = JSON.parse(jsonStr);
                console.log(`Data line ${i}: ${data.type} - ${data.type === 'progress' ? data.message : 'completion'}`);
            } catch (e) {
                console.log(`Data line ${i}: Parse error - ${e.message}`);
            }
        });
        
    } catch (error) {
        console.error('❌ Error:', error);
    }
}

testNewlineAnalysis();