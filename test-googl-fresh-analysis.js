// Test script to check GOOGL analysis endpoint with force refresh
const https = require('https');

function testGOOGLFreshAnalysis() {
    const url = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/GOOGL?force_refresh=true';
    
    console.log('🔍 Testing GOOGL Analysis API with Force Refresh...');
    console.log(`📡 Calling: ${url}`);
    
    https.get(url, (res) => {
        let data = '';
        
        res.on('data', (chunk) => {
            data += chunk;
        });
        
        res.on('end', () => {
            try {
                const response = JSON.parse(data);
                console.log('\n✅ GOOGL Fresh Analysis Response:');
                console.log(`📊 Ticker: ${response.ticker}`);
                console.log(`🏢 Company: ${response.companyName}`);
                console.log(`💰 Current Price: ${response.currentPrice}`);
                console.log(`📈 Fair Value: ${response.fairValue}`);
                console.log(`📊 Margin of Safety: ${response.marginOfSafety}%`);
                console.log(`🎯 Recommendation: ${response.recommendation}`);
                
                // Check if fake data has been removed
                console.log('\n🔍 Data Quality Check:');
                if (response.fairValue === null || response.fairValue === undefined) {
                    console.log('✅ Fair value is properly null (no fake data)');
                } else {
                    console.log(`❌ Fair value still exists: $${response.fairValue} - this should be null without real financial data`);
                }
                
                if (response.financialHealth?.score === null || response.financialHealth?.score === undefined) {
                    console.log('✅ Financial health score is properly null');
                } else {
                    console.log(`❌ Financial health score still exists: ${response.financialHealth?.score} - should be null`);
                }
                
                if (response.businessQuality?.score === null || response.businessQuality?.score === undefined) {
                    console.log('✅ Business quality score is properly null');
                } else {
                    console.log(`❌ Business quality score still exists: ${response.businessQuality?.score} - should be null`);
                }
                
                if (response.sector === null || response.sector === undefined) {
                    console.log('✅ Sector is properly null');
                } else {
                    console.log(`❌ Sector still exists: ${response.sector} - should be null without real data`);
                }
                
                if (response.marketCap === null || response.marketCap === undefined) {
                    console.log('✅ Market cap is properly null');
                } else {
                    console.log(`❌ Market cap still exists: ${response.marketCap} - should be null without real shares data`);
                }
                
                // Check missing data flag
                if (response.missingData?.has_missing_data === true) {
                    console.log('✅ Missing data flag is properly set to true');
                    console.log(`📋 Missing fields: ${response.missingData.missing_fields?.join(', ')}`);
                } else {
                    console.log(`❌ Missing data flag is wrong: ${response.missingData?.has_missing_data}`);
                }
                
                console.log('\n📋 Key Fields Summary:');
                console.log(`- Current Price: ${response.currentPrice} (should be real from MarketStack)`);
                console.log(`- Fair Value: ${response.fairValue} (should be null)`);
                console.log(`- Financial Health Score: ${response.financialHealth?.score} (should be null)`);
                console.log(`- Business Quality Score: ${response.businessQuality?.score} (should be null)`);
                console.log(`- Sector: ${response.sector} (should be null)`);
                console.log(`- Market Cap: ${response.marketCap} (should be null)`);
                
            } catch (error) {
                console.error('❌ Error parsing JSON:', error);
                console.log('Raw response:', data.substring(0, 500) + '...');
            }
        });
        
    }).on('error', (error) => {
        console.error('❌ Request error:', error);
    });
}

// Run the test
testGOOGLFreshAnalysis();