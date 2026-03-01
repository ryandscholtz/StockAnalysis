// Test API Health Endpoint
const https = require('https');

const apiUrl = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health';

console.log('Testing API endpoint:', apiUrl);
console.log('');

https.get(apiUrl, (res) => {
    let data = '';
    
    console.log('Status Code:', res.statusCode);
    console.log('Headers:', JSON.stringify(res.headers, null, 2));
    console.log('');
    
    res.on('data', (chunk) => {
        data += chunk;
    });
    
    res.on('end', () => {
        console.log('Response Body:');
        try {
            const json = JSON.parse(data);
            console.log(JSON.stringify(json, null, 2));
        } catch (e) {
            console.log(data);
        }
    });
}).on('error', (err) => {
    console.error('Error:', err.message);
});
