// Test script to check if company names are fixed in the API
const https = require('https');

function testAPI() {
    const url = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist';
    
    console.log('🔍 Testing API company names...');
    console.log(`📡 Calling: ${url}`);
    
    https.get(url, (res) => {
        let data = '';
        
        res.on('data', (chunk) => {
            data += chunk;
        });
        
        res.on('end', () => {
            try {
                const response = JSON.parse(data);
                console.log('\n✅ API Response received:');
                console.log(`📊 Total items: ${response.total || 0}`);
                
                if (response.items && response.items.length > 0) {
                    console.log('\n🏢 Company Names Check:');
                    response.items.forEach((item, index) => {
                        const isCorrect = item.company_name && 
                                        !item.company_name.includes('Corporation') && 
                                        item.company_name !== `${item.ticker} Corporation`;
                        
                        console.log(`${index + 1}. ${item.ticker}: "${item.company_name}" ${isCorrect ? '✅' : '❌'}`);
                        
                        // Special check for KO (Coca-Cola)
                        if (item.ticker === 'KO') {
                            const isKOCorrect = item.company_name === 'The Coca-Cola Company';
                            console.log(`   🥤 KO Check: ${isKOCorrect ? '✅ Correct!' : '❌ Still wrong!'}`);
                        }
                        
                        // Special check for AMZN (Amazon)
                        if (item.ticker === 'AMZN') {
                            const isAMZNCorrect = item.company_name === 'Amazon.com Inc.';
                            console.log(`   📦 AMZN Check: ${isAMZNCorrect ? '✅ Correct!' : '❌ Still wrong!'}`);
                        }
                    });
                } else {
                    console.log('❌ No items found in watchlist');
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
testAPI();