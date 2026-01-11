const https = require('https');

function testValuation(ticker) {
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
                    console.log(`\n=== ${ticker} Valuation Test ===`);
                    console.log(`Current Price: $${analysis.currentPrice}`);
                    console.log(`Fair Value: $${analysis.fairValue}`);
                    console.log(`Margin of Safety: ${analysis.marginOfSafety}%`);
                    console.log(`Recommendation: ${analysis.recommendation}`);
                    
                    console.log('\nValuation Breakdown:');
                    console.log(`  DCF Value: $${analysis.valuation.dcf}`);
                    console.log(`  Earnings Power: $${analysis.valuation.earningsPower}`);
                    console.log(`  Asset Based: $${analysis.valuation.assetBased}`);
                    
                    // Check if all required fields are present
                    const hasCurrentPrice = analysis.currentPrice !== null && analysis.currentPrice !== undefined;
                    const hasFairValue = analysis.fairValue !== null && analysis.fairValue !== undefined;
                    const hasMarginOfSafety = analysis.marginOfSafety !== null && analysis.marginOfSafety !== undefined;
                    const hasValuationBreakdown = analysis.valuation && analysis.valuation.dcf && analysis.valuation.earningsPower && analysis.valuation.assetBased;
                    
                    console.log('\nValidation:');
                    console.log(`  ✅ Current Price: ${hasCurrentPrice}`);
                    console.log(`  ✅ Fair Value: ${hasFairValue}`);
                    console.log(`  ✅ Margin of Safety: ${hasMarginOfSafety}`);
                    console.log(`  ✅ Valuation Breakdown: ${hasValuationBreakdown}`);
                    
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
    const tickers = ['GOOGL', 'AAPL'];
    
    for (const ticker of tickers) {
        try {
            await testValuation(ticker);
        } catch (error) {
            console.error(`Failed to test ${ticker}:`, error.message);
        }
    }
}

testAllStocks();