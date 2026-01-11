/**
 * Test the AI-enhanced PDF processing functionality
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testAIPDFProcessing() {
    console.log('🤖 Testing AI-Enhanced PDF Processing');
    console.log('='.repeat(60));
    
    // Test 1: Check if the endpoint is working
    console.log('\n1. Testing PDF upload endpoint availability...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/upload-pdf?ticker=AAPL`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        console.log(`   Status: ${response.status}`);
        
        if (response.status === 400 && data.error && data.error.includes('multipart/form-data')) {
            console.log('   ✅ PDF upload endpoint is working correctly');
        } else {
            console.log('   ❌ Unexpected response from PDF upload endpoint');
            console.log(`   Response: ${JSON.stringify(data, null, 2)}`);
        }
    } catch (error) {
        console.log(`   ❌ Error testing endpoint: ${error.message}`);
    }
    
    // Test 2: Check manual data endpoint for verification
    console.log('\n2. Testing manual data retrieval...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data/AMZN`);
        const data = await response.json();
        
        console.log(`   Status: ${response.status}`);
        console.log(`   Ticker: ${data.ticker}`);
        console.log(`   Has Data: ${data.has_data}`);
        console.log(`   Data Source: ${data.data_source}`);
        
        if (data.financial_data) {
            const financialData = data.financial_data;
            
            // Check what data is available
            const incomeStatementPeriods = Object.keys(financialData.income_statement || {}).length;
            const balanceSheetPeriods = Object.keys(financialData.balance_sheet || {}).length;
            const cashflowPeriods = Object.keys(financialData.cashflow || {}).length;
            const keyMetricsCount = Object.keys(financialData.key_metrics || {}).length;
            
            console.log(`   📊 Current Data Summary:`);
            console.log(`   • Income Statement Periods: ${incomeStatementPeriods}`);
            console.log(`   • Balance Sheet Periods: ${balanceSheetPeriods}`);
            console.log(`   • Cash Flow Periods: ${cashflowPeriods}`);
            console.log(`   • Key Metrics: ${keyMetricsCount}`);
            
            if (incomeStatementPeriods > 0 || balanceSheetPeriods > 0 || cashflowPeriods > 0) {
                console.log('   ✅ Financial data found - AI extraction may have worked!');
                
                // Show sample extracted data
                console.log('\n   📈 Sample Extracted Data:');
                if (financialData.income_statement) {
                    Object.entries(financialData.income_statement).forEach(([period, data]) => {
                        console.log(`   Income Statement ${period}:`);
                        Object.entries(data).forEach(([field, value]) => {
                            if (typeof value === 'number') {
                                const formatted = new Intl.NumberFormat('en-US', { 
                                    style: 'currency', 
                                    currency: 'USD',
                                    minimumFractionDigits: 0,
                                    maximumFractionDigits: 0
                                }).format(value);
                                console.log(`     ${field}: ${formatted}`);
                            }
                        });
                    });
                }
            } else {
                console.log('   ⚠️ No financial data periods found - may need to re-upload PDF');
            }
        }
        
    } catch (error) {
        console.log(`   ❌ Error retrieving data: ${error.message}`);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('🎯 AI PDF Processing Test Complete!');
    console.log('\n📋 Next Steps:');
    console.log('1. Upload your Amazon Annual Report PDF via the test page');
    console.log('2. The system will now use AWS Textract + Claude AI for extraction');
    console.log('3. Check the extracted data display for structured financial data');
    console.log('4. Verify the data using the "Verify Stored Data" button');
    console.log('\n🚀 The AI-enhanced system should extract actual financial values!');
}

// Run the test
testAIPDFProcessing().catch(console.error);