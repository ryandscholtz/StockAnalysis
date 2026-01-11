/**
 * Check the exact character codes in the response
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testCharacterCodes() {
    console.log('🔍 Analyzing Character Codes...\n');
    
    try {
        const response = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        const text = await response.text();
        
        console.log('📊 First 300 characters with codes:');
        
        for (let i = 0; i < Math.min(300, text.length); i++) {
            const char = text[i];
            const code = text.charCodeAt(i);
            
            if (code === 10) {
                console.log(`Position ${i}: \\n (LF, code 10)`);
            } else if (code === 13) {
                console.log(`Position ${i}: \\r (CR, code 13)`);
            } else if (code < 32 || code > 126) {
                console.log(`Position ${i}: [${code}] (non-printable)`);
            } else if (i % 50 === 0) {
                console.log(`Position ${i}: "${char}" (${code})`);
            }
        }
        
        // Look for sequences that might be newlines
        console.log('\\n📊 Looking for potential newline sequences:');
        
        const positions = [];
        for (let i = 0; i < text.length - 1; i++) {
            const code1 = text.charCodeAt(i);
            const code2 = text.charCodeAt(i + 1);
            
            if ((code1 === 10 && code2 === 10) || // \\n\\n
                (code1 === 13 && code2 === 10) || // \\r\\n
                (code1 === 10 && code2 === 13)) { // \\n\\r
                positions.push({ pos: i, seq: `${code1}-${code2}` });
            }
        }
        
        console.log(`Found ${positions.length} potential newline sequences:`, positions);
        
        // Try to manually split on character code 10 (LF)
        const parts = [];
        let start = 0;
        
        for (let i = 0; i < text.length; i++) {
            if (text.charCodeAt(i) === 10) {
                parts.push(text.substring(start, i));
                start = i + 1;
            }
        }
        if (start < text.length) {
            parts.push(text.substring(start));
        }
        
        console.log(`\\n📊 Manual split by LF (code 10): ${parts.length} parts`);
        
        // Look for data: lines
        const dataLines = parts.filter(part => part.trim().startsWith('data: '));
        console.log(`📊 Found ${dataLines.length} data: lines after manual split`);
        
        dataLines.forEach((line, i) => {
            try {
                const jsonStr = line.trim().slice(6);
                const data = JSON.parse(jsonStr);
                console.log(`✅ Data line ${i}: ${data.type}`);
                if (data.type === 'complete') {
                    console.log('🎯 FOUND COMPLETION MESSAGE!');
                }
            } catch (e) {
                console.log(`❌ Data line ${i}: ${e.message} - "${line.trim().substring(0, 50)}..."`);
            }
        });
        
    } catch (error) {
        console.error('❌ Error:', error);
    }
}

testCharacterCodes();