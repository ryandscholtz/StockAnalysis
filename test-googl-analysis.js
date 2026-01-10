// Test script to check GOOGL analysis endpoint
const https = require('https');

function testGOOGLAnalysis() {
    const url = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/GOOGL';
    
    console.log('🔍 Testing GOOGL Analysis API...');
    console.log(`📡 Calling: ${url}`);
    
    https.get(url, (res) => {
        let data = '';
        
        res.on('data', (chunk) => {
            data += chunk;
        });
        
        res.on('end', () => {
            try {
                const response = JSON.parse(data);
                console.log('\n✅ GOOGL Analysis Response:');
                console.log(`📊 Ticker: ${response.ticker}`);
                console.log(`🏢 Company: ${response.companyName}`);
                console.log(`💰 Current Price: ${response.currentPrice}`);
                console.log(`📈 Fair Value: ${response.fairValue}`);
                console.log(`📊 Margin of Safety: ${response.marginOfSafety}%`);
                console.log(`🎯 Recommendation: ${response.recommendation}`);
                
                // Check if this looks like fake/default data
                console.log('\n🔍 Data Quality Check:');
                if (response.fairValue === null || response.fairValue === undefined) {
                    console.log('✅ Fair value is properly null (no fake data)');
                } else if (response.fairValue > 0) {
                    console.log(`❌ Fair value exists: $${response.fairValue} - check if this is legitimate or cached fake data`);
                }
                
                if (response.currentPrice === null || response.currentPrice === undefined) {
                    console.log('✅ Current price is properly null (no fake data)');
                } else if (response.currentPrice > 0) {
                    console.log(`✅ Current price exists: $${response.currentPrice} - likely real MarketStack data`);
                }
                
                // Check cache info
                if (response.cacheInfo) {
                    console.log(`\n📋 Cache Info:`);
                    console.log(`- Cached: ${response.cacheInfo.cached}`);
                    console.log(`- Fresh: ${response.cacheInfo.fresh_data}`);
                    console.log(`- Age: ${response.cacheInfo.age_minutes} minutes`);
                    console.log(`- Stale: ${response.cacheInfo.is_stale}`);
                }
                
                // Check data source
                if (response.dataSource) {
                    console.log(`\n📡 Data Source:`);
                    console.log(`- Price source: ${response.dataSource.price_source}`);
                    console.log(`- Has real price: ${response.dataSource.has_real_price}`);
                    console.log(`- API available: ${response.dataSource.api_available}`);
                }
                
                console.log('\n📋 Full Response:');
                console.log(JSON.stringify(response, null, 2));
                
            } catch (error) {
                console.error('❌ Error parsing JSON:', error);
                console.log('Raw response:', data);
            }
        });
        
    }).on('error', (error) => {
        console.error('❌ Request error:', error);
    });
}

// Run the test
testGOOGLAnalysis();