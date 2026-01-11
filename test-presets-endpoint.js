const https = require('https');

function testPresets() {
    return new Promise((resolve, reject) => {
        const url = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analysis-presets';
        
        https.get(url, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const response = JSON.parse(data);
                    console.log('=== Analysis Presets Test ===');
                    console.log('Status:', res.statusCode);
                    console.log('Business Types:', response.business_types);
                    console.log('\nPresets:');
                    
                    for (const [key, value] of Object.entries(response.presets)) {
                        console.log(`  ${key}:`, value);
                    }
                    
                    console.log('\nValidation:');
                    console.log('✅ Has business_types:', !!response.business_types);
                    console.log('✅ Has presets:', !!response.presets);
                    console.log('✅ Business types count:', response.business_types?.length || 0);
                    console.log('✅ Presets count:', Object.keys(response.presets || {}).length);
                    
                    resolve(response);
                } catch (error) {
                    console.error('Error parsing response:', error);
                    reject(error);
                }
            });
        }).on('error', (error) => {
            console.error('Error fetching presets:', error);
            reject(error);
        });
    });
}

testPresets();