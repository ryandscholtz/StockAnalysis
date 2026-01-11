const https = require('https');

function testAnalysis(ticker) {
    return new Promise((resolve, reject) => {
        const url = `https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/${ticker}?stream=true`;
        
        https.get(url, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const analysis = JSON.parse(data);
                    console.log(`\n=== ${ticker} Analysis ===`);
                    console.log(`Company: ${analysis.company_name}`);
                    console.log(`Current Price: $${analysis.current_price}`);
                    console.log(`Fair Value: $${analysis.fair_value}`);
                    console.log(`Margin of Safety: ${analysis.margin_of_safety_pct}%`);
                    console.log(`Recommendation: ${analysis.recommendation}`);
                    console.log(`P/E Ratio: ${analysis.priceRatios.priceToEarnings}`);
                    console.log(`P/B Ratio: ${analysis.priceRatios.priceToBook}`);
                    console.log(`ROE: ${analysis.growthMetrics.roe}%`);
                    console.log(`Financial Health Score: ${analysis.financial_health.score}/10`);
                    resolve(analysis);
                } catch (error) {
                    console.error(`Error parsing ${ticker} analysis:`, error);
                    reject(error);
                }
            });
        }).on('error', (error) => {
            console.error(`Error fetching ${ticker} analysis:`, error);
            reject(error);
        });
    });
}

async function testAllStocks() {
    const tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA'];
    
    for (const ticker of tickers) {
        try {
            await testAnalysis(ticker);
        } catch (error) {
            console.error(`Failed to test ${ticker}:`, error.message);
        }
    }
}

testAllStocks();