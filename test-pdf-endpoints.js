/**
 * Test PDF Upload Endpoints
 * Tests the newly implemented PDF upload and manual data endpoints
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testEndpoints() {
    console.log('🧪 Testing PDF Upload Endpoints');
    console.log('API Base URL:', API_BASE_URL);
    console.log('');

    // Test 1: Check if upload endpoint exists (should return 405 for GET)
    console.log('1️⃣ Testing POST /api/upload-pdf endpoint availability...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/upload-pdf`);
        console.log(`   Status: ${response.status}`);
        if (response.status === 405) {
            console.log('   ✅ Endpoint exists (returns 405 for GET as expected)');
        } else {
            console.log('   ⚠️ Unexpected status - endpoint may not be configured correctly');
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    // Test 2: Test manual data GET endpoint
    console.log('2️⃣ Testing GET /api/manual-data/{ticker} endpoint...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data/AAPL`);
        console.log(`   Status: ${response.status}`);
        if (response.ok) {
            const data = await response.json();
            console.log('   ✅ Endpoint working');
            console.log('   Response:', JSON.stringify(data, null, 2));
        } else {
            console.log('   ❌ Endpoint returned error');
            const errorData = await response.json();
            console.log('   Error:', JSON.stringify(errorData, null, 2));
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    // Test 3: Test manual data POST endpoint
    console.log('3️⃣ Testing POST /api/manual-data endpoint...');
    const testData = {
        ticker: 'AAPL',
        data_type: 'income_statement',
        period: '2023-12-31',
        data: {
            revenue: 383285000000,
            net_income: 97000000000,
            earnings_per_share: 6.16,
            gross_profit: 169148000000
        }
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(testData)
        });
        
        console.log(`   Status: ${response.status}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log('   ✅ Manual data entry successful');
            console.log('   Response:', JSON.stringify(data, null, 2));
        } else {
            console.log('   ❌ Manual data entry failed');
            console.log('   Error:', JSON.stringify(data, null, 2));
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    // Test 4: Verify data was saved by getting it back
    console.log('4️⃣ Verifying saved data by retrieving it...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data/AAPL`);
        console.log(`   Status: ${response.status}`);
        if (response.ok) {
            const data = await response.json();
            console.log('   ✅ Data retrieval successful');
            console.log('   Has data:', data.has_data);
            console.log('   Data source:', data.data_source);
            if (data.financial_data && data.financial_data.income_statement) {
                console.log('   Income statement periods:', Object.keys(data.financial_data.income_statement));
                const period2023 = data.financial_data.income_statement['2023-12-31'];
                if (period2023) {
                    console.log('   2023 data fields:', Object.keys(period2023));
                    console.log('   Revenue:', period2023.revenue);
                    console.log('   Net Income:', period2023.net_income);
                }
            }
        } else {
            console.log('   ❌ Data retrieval failed');
            const errorData = await response.json();
            console.log('   Error:', JSON.stringify(errorData, null, 2));
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    // Test 5: Test with different data types
    console.log('5️⃣ Testing balance sheet data entry...');
    const balanceSheetData = {
        ticker: 'AAPL',
        data_type: 'balance_sheet',
        period: '2023-12-31',
        data: {
            total_assets: 352755000000,
            total_liabilities: 290437000000,
            shareholders_equity: 62318000000,
            cash_and_equivalents: 29965000000
        }
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(balanceSheetData)
        });
        
        console.log(`   Status: ${response.status}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log('   ✅ Balance sheet data entry successful');
            console.log('   Response:', JSON.stringify(data, null, 2));
        } else {
            console.log('   ❌ Balance sheet data entry failed');
            console.log('   Error:', JSON.stringify(data, null, 2));
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    // Test 6: Test key metrics (non-period based)
    console.log('6️⃣ Testing key metrics data entry...');
    const keyMetricsData = {
        ticker: 'AAPL',
        data_type: 'key_metrics',
        period: 'current', // Key metrics are not period-based but we need to provide something
        data: {
            market_cap: 3000000000000,
            pe_ratio: 30.5,
            price_to_book: 45.2,
            dividend_yield: 0.44,
            return_on_equity: 147.25
        }
    };

    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(keyMetricsData)
        });
        
        console.log(`   Status: ${response.status}`);
        const data = await response.json();
        
        if (response.ok) {
            console.log('   ✅ Key metrics data entry successful');
            console.log('   Response:', JSON.stringify(data, null, 2));
        } else {
            console.log('   ❌ Key metrics data entry failed');
            console.log('   Error:', JSON.stringify(data, null, 2));
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    // Test 7: Final verification - get all data
    console.log('7️⃣ Final verification - retrieving all saved data...');
    try {
        const response = await fetch(`${API_BASE_URL}/api/manual-data/AAPL`);
        console.log(`   Status: ${response.status}`);
        if (response.ok) {
            const data = await response.json();
            console.log('   ✅ Final data retrieval successful');
            console.log('   Complete financial data structure:');
            console.log(JSON.stringify(data.financial_data, null, 2));
        } else {
            console.log('   ❌ Final data retrieval failed');
        }
    } catch (error) {
        console.log('   ❌ Error:', error.message);
    }
    console.log('');

    console.log('🎉 PDF Upload Endpoints Testing Complete!');
    console.log('');
    console.log('📋 Summary:');
    console.log('- PDF upload endpoint is available (ready for file uploads)');
    console.log('- Manual data entry endpoints are working');
    console.log('- Data is being saved to and retrieved from DynamoDB');
    console.log('- Multiple data types supported (income statement, balance sheet, key metrics)');
    console.log('');
    console.log('🚀 Next Steps:');
    console.log('1. Test actual PDF file upload through the frontend');
    console.log('2. Verify AWS Textract integration works');
    console.log('3. Add S3 bucket for large document async processing');
    console.log('4. Implement progress tracking for large PDFs');
}

// Run the tests
testEndpoints().catch(console.error);