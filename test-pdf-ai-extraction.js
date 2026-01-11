/**
 * Test script to verify PDF upload with AI extraction is working
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testPDFAIExtraction() {
    console.log('🤖 Testing PDF Upload with AI Extraction...');
    
    try {
        // Test 1: Check health endpoint
        console.log('\n1️⃣ Testing API health...');
        const healthResponse = await fetch(`${API_BASE}/health`);
        const healthData = await healthResponse.json();
        console.log(`Health check: ${healthResponse.status} - ${healthData.message}`);
        
        // Test 2: Check manual data endpoint for AMZN
        console.log('\n2️⃣ Testing manual data retrieval for AMZN...');
        const manualDataResponse = await fetch(`${API_BASE}/api/manual-data/AMZN`);
        const manualData = await manualDataResponse.json();
        console.log(`Manual data status: ${manualDataResponse.status}`);
        console.log('Has financial data:', manualData.has_data);
        console.log('Data source:', manualData.data_source);
        
        if (manualData.has_data) {
            console.log('\n📊 Available financial data:');
            const financialData = manualData.financial_data;
            
            // Check each statement type
            ['income_statement', 'balance_sheet', 'cashflow', 'key_metrics'].forEach(statementType => {
                if (financialData[statementType] && Object.keys(financialData[statementType]).length > 0) {
                    console.log(`  ✅ ${statementType}: ${Object.keys(financialData[statementType]).length} periods/fields`);
                    
                    // Show sample data
                    const sampleData = financialData[statementType];
                    const firstKey = Object.keys(sampleData)[0];
                    if (firstKey) {
                        const firstValue = sampleData[firstKey];
                        if (typeof firstValue === 'object') {
                            console.log(`     Sample period ${firstKey}: ${Object.keys(firstValue).length} fields`);
                        } else {
                            console.log(`     ${firstKey}: ${firstValue}`);
                        }
                    }
                } else {
                    console.log(`  ❌ ${statementType}: No data`);
                }
            });
            
            // Check extraction metadata
            if (financialData.extraction_metadata) {
                console.log('\n🔍 Extraction metadata:');
                console.log('  Method:', financialData.extraction_metadata.extraction_method);
                console.log('  Extracted at:', financialData.extraction_metadata.extracted_at);
                console.log('  Note:', financialData.extraction_metadata.note);
            }
        }
        
        console.log('\n✅ PDF AI extraction test completed');
        console.log('📝 To test with a new PDF, use the HTML test page');
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run the test
testPDFAIExtraction();