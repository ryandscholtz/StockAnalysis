// Test the manual data entry functionality
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testManualDataEntry() {
    console.log('🧪 Testing Manual Data Entry Functionality...\n');
    
    try {
        // Test adding income statement data
        console.log('📊 Adding income statement data for TEST ticker...');
        const incomeData = {
            ticker: 'TEST',
            data_type: 'income_statement',
            period: '2023-12-31',
            data: {
                revenue: 100000000,
                net_income: 15000000,
                operating_income: 20000000,
                gross_profit: 40000000
            }
        };
        
        const incomeResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(incomeData)
        });
        
        const incomeResult = await incomeResponse.json();
        console.log('Income statement response:', incomeResult);
        
        // Test adding balance sheet data
        console.log('\n📊 Adding balance sheet data for TEST ticker...');
        const balanceData = {
            ticker: 'TEST',
            data_type: 'balance_sheet',
            period: '2023-12-31',
            data: {
                total_assets: 500000000,
                total_liabilities: 200000000,
                shareholders_equity: 300000000,
                cash_and_equivalents: 50000000
            }
        };
        
        const balanceResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(balanceData)
        });
        
        const balanceResult = await balanceResponse.json();
        console.log('Balance sheet response:', balanceResult);
        
        // Test adding cashflow data
        console.log('\n📊 Adding cashflow data for TEST ticker...');
        const cashflowData = {
            ticker: 'TEST',
            data_type: 'cashflow',
            period: '2023-12-31',
            data: {
                operating_cash_flow: 25000000,
                free_cash_flow: 18000000,
                capital_expenditures: 7000000
            }
        };
        
        const cashflowResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(cashflowData)
        });
        
        const cashflowResult = await cashflowResponse.json();
        console.log('Cashflow response:', cashflowResult);
        
        // Test adding key metrics
        console.log('\n📊 Adding key metrics for TEST ticker...');
        const keyMetricsData = {
            ticker: 'TEST',
            data_type: 'key_metrics',
            period: 'latest',
            data: {
                shares_outstanding: 10000000,
                market_cap: 1000000000,
                pe_ratio: 20,
                book_value_per_share: 30
            }
        };
        
        const keyMetricsResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(keyMetricsData)
        });
        
        const keyMetricsResult = await keyMetricsResponse.json();
        console.log('Key metrics response:', keyMetricsResult);
        
        // Test retrieving the data
        console.log('\n📊 Retrieving manual data for TEST ticker...');
        const retrieveResponse = await fetch(`${API_URL}/api/manual-data/TEST`);
        const retrieveResult = await retrieveResponse.json();
        console.log('Retrieved data:', JSON.stringify(retrieveResult, null, 2));
        
        // Test analysis with manual data
        console.log('\n📊 Testing analysis with manual data (force refresh)...');
        const analysisResponse = await fetch(`${API_URL}/api/analyze/TEST?force_refresh=true`);
        const analysisResult = await analysisResponse.json();
        
        console.log('Analysis with manual data:');
        console.log('- Ticker:', analysisResult.ticker);
        console.log('- Fair Value:', analysisResult.fairValue);
        console.log('- DCF Value:', analysisResult.valuation?.dcf);
        console.log('- EPV Value:', analysisResult.valuation?.earningsPower);
        console.log('- Asset Value:', analysisResult.valuation?.assetBased);
        console.log('- Missing Data:', analysisResult.missingData);
        
        if (analysisResult.fairValue !== null) {
            console.log('✅ SUCCESS: Fair value calculated using manual data!');
        } else {
            console.log('⚠️ Fair value is still null - may need more data or debugging');
        }
        
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

testManualDataEntry();