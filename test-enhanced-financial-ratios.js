/**
 * Test script for enhanced Lambda function with financial ratios
 * Shows all available financial metrics and ratios
 */

const BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testFinancialRatios() {
    console.log('🚀 Testing Enhanced Lambda Function with Financial Ratios');
    console.log('=' * 60);
    
    const tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA'];
    
    for (const ticker of tickers) {
        console.log(`\n📊 ${ticker} - Financial Analysis`);
        console.log('-'.repeat(40));
        
        try {
            // Test individual watchlist item (has most comprehensive data)
            const response = await fetch(`${BASE_URL}/api/watchlist/${ticker}`);
            const data = await response.json();
            
            if (response.ok) {
                console.log(`🏢 Company: ${data.company_name}`);
                console.log(`💰 Current Price: $${data.current_price}`);
                console.log(`🎯 Fair Value: $${data.fair_value}`);
                console.log(`📈 Recommendation: ${data.recommendation}`);
                console.log(`🛡️ Margin of Safety: ${data.margin_of_safety_pct}%`);
                
                console.log('\n📊 Financial Ratios:');
                const ratios = data.financial_ratios;
                console.log(`   P/E Ratio: ${ratios.pe_ratio}`);
                console.log(`   P/B Ratio: ${ratios.pb_ratio}`);
                console.log(`   P/S Ratio: ${ratios.ps_ratio}`);
                console.log(`   Debt/Equity: ${ratios.debt_to_equity}`);
                console.log(`   ROE: ${ratios.roe}%`);
                console.log(`   Current Ratio: ${ratios.current_ratio}`);
                console.log(`   Gross Margin: ${ratios.gross_margin}%`);
                console.log(`   Operating Margin: ${ratios.operating_margin}%`);
                console.log(`   Net Margin: ${ratios.net_margin}%`);
                
                console.log('\n🏦 Market Data:');
                const market = data.market_data;
                console.log(`   Market Cap: $${(market.market_cap / 1e9).toFixed(1)}B`);
                console.log(`   Shares Outstanding: ${(market.shares_outstanding / 1e6).toFixed(0)}M`);
                console.log(`   Enterprise Value: $${(market.enterprise_value / 1e9).toFixed(1)}B`);
                
            } else {
                console.log(`❌ Error: ${data.error}`);
            }
            
        } catch (error) {
            console.log(`💥 Network Error: ${error.message}`);
        }
    }
    
    // Test live prices endpoint
    console.log('\n\n🔴 Live Prices with Ratios');
    console.log('=' * 40);
    
    try {
        const response = await fetch(`${BASE_URL}/api/watchlist/live-prices`);
        const data = await response.json();
        
        if (response.ok) {
            Object.entries(data.live_prices).forEach(([ticker, info]) => {
                console.log(`\n${ticker}:`);
                console.log(`  Price: $${info.price}`);
                console.log(`  Market Cap: $${(info.market_cap / 1e9).toFixed(1)}B`);
                console.log(`  P/E: ${info.pe_ratio}`);
                console.log(`  P/B: ${info.pb_ratio}`);
                console.log(`  D/E: ${info.debt_to_equity}`);
                console.log(`  ROE: ${info.roe}%`);
            });
        }
    } catch (error) {
        console.log(`💥 Live Prices Error: ${error.message}`);
    }
    
    // Test comprehensive analysis
    console.log('\n\n🔬 Comprehensive Analysis Example (AAPL)');
    console.log('=' * 50);
    
    try {
        const response = await fetch(`${BASE_URL}/api/analyze/AAPL`);
        const data = await response.json();
        
        if (response.ok) {
            console.log(`📊 Analysis Summary:`);
            console.log(`   ${data.summary}`);
            
            console.log(`\n💊 Financial Health (Score: ${data.financial_health.score}/10):`);
            console.log(`   ${data.financial_health.assessment}`);
            console.log(`   Debt/Equity: ${data.financial_health.debt_to_equity}`);
            console.log(`   Current Ratio: ${data.financial_health.current_ratio}`);
            console.log(`   ROE: ${data.financial_health.roe}%`);
            
            console.log(`\n📈 Valuation Metrics:`);
            console.log(`   Current P/E: ${data.valuation.current_pe}`);
            console.log(`   Current P/B: ${data.valuation.current_pb}`);
            console.log(`   Current P/S: ${data.valuation.current_ps}`);
            console.log(`   DCF Value: $${data.valuation.dcf_value}`);
            console.log(`   P/E Fair Value: $${data.valuation.pe_fair_value}`);
            
            console.log(`\n📊 Profitability Metrics:`);
            const growth = data.growth_metrics;
            console.log(`   ROE: ${growth.roe}%`);
            console.log(`   Gross Margin: ${growth.gross_margin}%`);
            console.log(`   Operating Margin: ${growth.operating_margin}%`);
            console.log(`   Net Margin: ${growth.net_margin}%`);
            
        }
    } catch (error) {
        console.log(`💥 Analysis Error: ${error.message}`);
    }
    
    console.log('\n\n✅ Enhanced Financial Ratios Test Complete!');
    console.log('\n🎯 Available Metrics:');
    console.log('   • P/E, P/B, P/S Ratios');
    console.log('   • Debt-to-Equity Ratio');
    console.log('   • Return on Equity (ROE)');
    console.log('   • Current Ratio');
    console.log('   • Profit Margins (Gross, Operating, Net)');
    console.log('   • Market Cap & Enterprise Value');
    console.log('   • DCF and P/E-based Fair Values');
    console.log('   • Financial Health Scores');
    console.log('   • Investment Recommendations');
}

// Run the test
testFinancialRatios().catch(console.error);