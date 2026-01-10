// Test script to check search API company names
const https = require('https');

function testSearchAPI() {
    const url = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/search?q=amazon';
    
    console.log('🔍 Testing Search API company names...');
    console.log(`📡 Calling: ${url}`);
    
    https.get(url, (res) => {
        let data = '';
        
        res.on('data', (chunk) => {
            data += chunk;
        });
        
        res.on('end', () => {
            try {
                const response = JSON.parse(data);
                console.log('\n✅ Search API Response received:');
                console.log(`📊 Total results: ${response.results?.length || 0}`);
                
                if (response.results && response.results.length > 0) {
                    console.log('\n🏢 Search Results Check:');
                    response.results.forEach((item, index) => {
                        const isCorrect = item.companyName && 
                                        !item.companyName.includes('Corporation') && 
                                        item.companyName !== `${item.ticker} Corporation`;
                        
                        console.log(`${index + 1}. ${item.ticker}: "${item.companyName}" ${isCorrect ? '✅' : '❌'}`);
                        
                        // Special check for AMZN (Amazon)
                        if (item.ticker === 'AMZN') {
                            const isAMZNCorrect = item.companyName === 'Amazon.com Inc.';
                            console.log(`   📦 AMZN Check: ${isAMZNCorrect ? '✅ Correct!' : '❌ Still wrong!'}`);
                        }
                    });
                } else {
                    console.log('❌ No search results found');
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
testSearchAPI();