/**
 * Test to see the exact bytes in the response
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testRawResponseBytes() {
    console.log('🔍 Testing Raw Response Bytes...\n');
    
    try {
        const response = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        const arrayBuffer = await response.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        
        console.log('📊 Response length:', uint8Array.length);
        console.log('📊 First 200 bytes as string:');
        
        const decoder = new TextDecoder();
        const first200 = decoder.decode(uint8Array.slice(0, 200));
        console.log(JSON.stringify(first200));
        
        console.log('\\n📊 Looking for newline patterns:');
        let newlineCount = 0;
        let doubleNewlineCount = 0;
        
        for (let i = 0; i < uint8Array.length - 1; i++) {
            if (uint8Array[i] === 10) { // \\n
                newlineCount++;
                if (uint8Array[i + 1] === 10) { // \\n\\n
                    doubleNewlineCount++;
                    console.log(`Found \\n\\n at position ${i}`);
                }
            }
        }
        
        console.log(`📊 Total \\n characters: ${newlineCount}`);
        console.log(`📊 Total \\n\\n sequences: ${doubleNewlineCount}`);
        
        // Convert to string and split by \\n\\n
        const fullText = decoder.decode(uint8Array);
        const chunks = fullText.split('\\n\\n');
        console.log(`📊 Chunks when split by \\n\\n: ${chunks.length}`);
        
        chunks.forEach((chunk, i) => {
            if (chunk.trim()) {
                console.log(`Chunk ${i}: "${chunk.trim().substring(0, 100)}..."`);
            }
        });
        
    } catch (error) {
        console.error('❌ Error:', error);
    }
}

testRawResponseBytes();