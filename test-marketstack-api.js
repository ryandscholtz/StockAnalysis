// Test the enhanced MarketStack API integration
const https = require('https');

const API_URL = 'https://9ye8wru6s5.execute-api.us-east-1.amazonaws.com/production/api/watchlist/live-prices';

console.log('=== TESTING ENHANCED MARKETSTACK API ===');
console.log('Testing live prices endpoint with MarketStack integration...');
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
      console.log('\n=== API RESPONSE ===');
      console.log(JSON.stringify(parsed, null, 2));
      
      if (parsed.live_prices) {
        console.log('\n=== PRICE ANALYSIS ===');
        const prices = parsed.live_prices;
        
        Object.keys(prices).forEach(ticker => {
          const priceData = prices[ticker];
          console.log(`${ticker}:`);
          console.log(`  Price: $${priceData.price}`);
          console.log(`  Source: ${priceData.source || 'Unknown'}`);
          console.log(`  Success: ${priceData.success}`);
          if (priceData.timestamp) {
            console.log(`  Timestamp: ${priceData.timestamp}`);
          }
          if (priceData.error) {
            console.log(`  Error: ${priceData.error}`);
          }
          if (priceData.comment) {
            console.log(`  Comment: ${priceData.comment}`);
          }
          console.log('');
        });
      }
      
      if (parsed.api_info) {
        console.log('=== API INFO ===');
        console.log(`Source: ${parsed.api_info.source}`);
        console.log(`Has API Key: ${parsed.api_info.has_api_key}`);
        console.log(`Tickers Requested: ${parsed.api_info.tickers_requested}`);
        console.log(`Tickers with Real Data: ${parsed.api_info.tickers_with_real_data}`);
      }
      
    } catch (error) {
      console.log('❌ Failed to parse JSON response:', error.message);
      console.log('Raw response:', data);
    }
  });
});

req.on('error', (error) => {
  console.error('❌ Request error:', error.message);
});

req.end();