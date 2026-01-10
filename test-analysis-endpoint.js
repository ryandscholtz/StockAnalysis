// Test the analysis endpoint to see if MarketStack integration is working
const https = require('https');

const API_URL = 'https://9ye8wru6s5.execute-api.us-east-1.amazonaws.com/production/api/analyze/AAPL';

console.log('=== TESTING ANALYSIS ENDPOINT WITH MARKETSTACK ===');
console.log('URL:', API_URL);

const req = https.request(API_URL, { method: 'GET' }, (res) => {
  console.log(`Status Code: ${res.statusCode}`);
  
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });
  
  res.on('end', () => {
    try {
      const parsed = JSON.parse(data);
      console.log('\n=== ANALYSIS RESPONSE ===');
      
      console.log(`Ticker: ${parsed.ticker}`);
      console.log(`Current Price: $${parsed.currentPrice}`);
      console.log(`Fair Value: $${parsed.fairValue}`);
      
      if (parsed.dataSource) {
        console.log('\n=== DATA SOURCE INFO ===');
        console.log(`Price Source: ${parsed.dataSource.price_source}`);
        console.log(`Has Real Price: ${parsed.dataSource.has_real_price}`);
        console.log(`API Available: ${parsed.dataSource.api_available}`);
      }
      
      // Check if we got real data vs mock
      if (parsed.currentPrice !== 150.00) {
        console.log('✅ Got REAL price data from MarketStack!');
      } else {
        console.log('⚠️ Using mock/fallback price data');
      }
      
    } catch (error) {
      console.log('❌ Failed to parse JSON response:', error.message);
      console.log('Raw response:', data.substring(0, 500));
    }
  });
});

req.on('error', (error) => {
  console.error('❌ Request error:', error.message);
});

req.end();