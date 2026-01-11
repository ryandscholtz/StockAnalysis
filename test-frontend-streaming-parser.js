/**
 * Test the exact same parsing logic as the frontend
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testFrontendStreamingParser() {
    console.log('🧪 Testing Frontend Streaming Parser Logic...\n');
    
    try {
        const response = await fetch(`${API_BASE}/api/analyze/AMZN?stream=true`);
        
        if (!response.ok) {
            console.log(`❌ Request failed: ${response.status}`);
            return;
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let chunkCount = 0;
        
        while (true) {
            const { done, value } = await reader.read();
            chunkCount++;
            
            if (chunkCount === 1) {
                console.log('✅ First chunk received, stream is working!');
            }
            
            if (done) {
                console.log(`📊 Stream ended after ${chunkCount} chunks. Buffer length:`, buffer.length);
                
                // Try to parse the buffer as streaming format (same logic as frontend)
                const lines = buffer.split('\\n');
                console.log(`📊 Total lines in buffer: ${lines.length}`);
                
                let foundCompletion = false;
                let completionData = null;
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i];
                    const trimmed = line.trim();
                    
                    if (trimmed.startsWith('data: ')) {
                        try {
                            const data = trimmed.slice(6).trim(); // Remove 'data: ' prefix
                            if (data) {
                                const update = JSON.parse(data);
                                console.log(`📋 Line ${i}: ${update.type} - ${update.type === 'progress' ? update.message : 'completion data'}`);
                                
                                if (update.type === 'complete' && update.data) {
                                    foundCompletion = true;
                                    completionData = update.data;
                                    console.log('✅ Found completion message!');
                                    console.log('📊 Completion data keys:', Object.keys(update.data));
                                }
                            }
                        } catch (error) {
                            console.log(`❌ Error parsing line ${i}:`, error.message);
                            console.log(`📋 Problematic line: "${trimmed.substring(0, 100)}..."`);
                        }
                    }
                }
                
                if (foundCompletion) {
                    console.log('\\n🎉 SUCCESS: Completion message found and parsed!');
                    console.log('📊 Analysis Results:');
                    console.log('  - Ticker:', completionData.ticker);
                    console.log('  - Company:', completionData.companyName);
                    console.log('  - Current Price:', completionData.currentPrice);
                    console.log('  - Fair Value:', completionData.fairValue);
                    console.log('  - Recommendation:', completionData.recommendation);
                    console.log('\\n✅ Frontend should NOT show \"Stream ended without completion\" error');
                } else {
                    console.log('\\n❌ FAILURE: No completion message found');
                    console.log('❌ Frontend will show \"Stream ended without completion\" error');
                }
                
                break;
            }
            
            const chunk = decoder.decode(value, { stream: true });
            buffer += chunk;
            
            // Process complete lines (same as frontend)
            const lines = buffer.split('\\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                const trimmed = line.trim();
                if (trimmed.startsWith('data: ')) {
                    try {
                        const data = trimmed.slice(6).trim();
                        if (data) {
                            const update = JSON.parse(data);
                            console.log(`[Chunk ${chunkCount}] ${update.type}:`, 
                                update.type === 'progress' ? `${update.message} (${update.progress}%)` : 'completion');
                            
                            if (update.type === 'complete' && update.data) {
                                console.log('🎯 COMPLETION FOUND DURING STREAMING!');
                                console.log('📊 This should resolve successfully');
                                // In real frontend, this would resolve the promise
                                return;
                            }
                        }
                    } catch (error) {
                        console.log('❌ Parse error during streaming:', error.message);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

testFrontendStreamingParser();