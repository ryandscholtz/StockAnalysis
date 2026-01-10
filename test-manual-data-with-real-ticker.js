// Test manual data entry with a real ticker that has price data
const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testManualDataWithRealTicker() {
    console.log('🧪 Testing Manual Data Entry with Real Ticker (AAPL)...\n');
    
    try {
        // Add comprehensive financial data for AAPL
        console.log('📊 Adding comprehensive financial data for AAPL...');
        
        // Income statement data
        const incomeData = {
            ticker: 'AAPL',
            data_type: 'income_statement',
            period: '2023-12-31',
            data: {
                revenue: 383285000000,
                net_income: 97000000000,
                operating_income: 114301000000,
                gross_profit: 169148000000,
                earnings_before_tax: 113000000000
            }
        };
        
        const incomeResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(incomeData)
        });
        console.log('Income statement:', await incomeResponse.json());
        
        // Balance sheet data
        const balanceData = {
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
        
        const balanceResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(balanceData)
        });
        console.log('Balance sheet:', await balanceResponse.json());
        
        // Cashflow data
        const cashflowData = {
            ticker: 'AAPL',
            data_type: 'cashflow',
            period: '2023-12-31',
            data: {
                operating_cash_flow: 110543000000,
                free_cash_flow: 99584000000,
                capital_expenditures: 10959000000
            }
        };
        
        const cashflowResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cashflowData)
        });
        console.log('Cashflow:', await cashflowResponse.json());
        
        // Key metrics
        const keyMetricsData = {
            ticker: 'AAPL',
            data_type: 'key_metrics',
            period: 'latest',
            data: {
                shares_outstanding: 15728700000,
                market_cap: 3000000000000,
                pe_ratio: 30.9,
                book_value_per_share: 3.96
            }
        };
        
        const keyMetricsResponse = await fetch(`${API_URL}/api/manual-data`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(keyMetricsData)
        });
        console.log('Key metrics:', await keyMetricsResponse.json());
        
        // Wait a moment for data to be saved
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Test analysis with manual data
        console.log('\n📊 Testing analysis with manual data (force refresh)...');
        const analysisResponse = await fetch(`${API_URL}/api/analyze/AAPL?force_refresh=true`);
        const analysisResult = await analysisResponse.json();
        
        console.log('\n=== ANALYSIS RESULTS ===');
        console.log('Ticker:', analysisResult.ticker);
        console.log('Current Price:', analysisResult.currentPrice);
        console.log('Fair Value:', analysisResult.fairValue);
        console.log('Margin of Safety:', analysisResult.marginOfSafety);
        console.log('Recommendation:', analysisResult.recommendation);
        console.log('Recommendation Reasoning:', analysisResult.recommendationReasoning);
        
        console.log('\n=== VALUATION BREAKDOWN ===');
        console.log('DCF Value:', analysisResult.valuation?.dcf);
        console.log('EPV Value:', analysisResult.valuation?.earningsPower);
        console.log('Asset Value:', analysisResult.valuation?.assetBased);
        console.log('Weighted Average:', analysisResult.valuation?.weightedAverage);
        
        console.log('\n=== MISSING DATA STATUS ===');
        console.log('Has Missing Data:', analysisResult.missingData?.has_missing_data);
        console.log('Missing Fields:', analysisResult.missingData?.missing_fields);
        
        if (analysisResult.fairValue !== null && analysisResult.fairValue > 0) {
            console.log('\n✅ SUCCESS: Fair value calculated using manual financial data!');
            console.log(`💰 Fair Value: $${analysisResult.fairValue.toFixed(2)}`);
            console.log(`📊 Current Price: $${analysisResult.currentPrice}`);
            
            if (analysisResult.marginOfSafety !== null) {
                const status = analysisResult.marginOfSafety > 0 ? 'Undervalued' : 'Overvalued';
                console.log(`📈 Status: ${Math.abs(analysisResult.marginOfSafety).toFixed(1)}% ${status}`);
            }
        } else {
            console.log('\n⚠️ Fair value is still null - checking what went wrong...');
            console.log('Full response:', JSON.stringify(analysisResult, null, 2));
        }
        
    } catch (error) {
        console.error('❌ Error:', error.message);
    }
}

testManualDataWithRealTicker();