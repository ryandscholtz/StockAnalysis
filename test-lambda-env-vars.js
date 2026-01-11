/**
 * Test Lambda Environment Variables
 * Check if MarketStack API key is properly configured
 */

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testLambdaEnvironment() {
    console.log('🔍 Testing Lambda Environment Configuration');
    console.log('==========================================');
    
    try {
        // Create a test endpoint to check environment variables
        console.log('\n1️⃣ Testing Health Endpoint for Environment Info...');
        const healthResponse = await fetch(`${API_BASE_URL}/health`);
        const healthData = await healthResponse.json();
        
        console.log('✅ Health check:', healthData.status);
        console.log('📦 Version:', healthData.version);
        console.log('🔧 Features:', healthData.features);
        console.log('🕐 Deployed at:', healthData.deployed_at);
        
        // Test a search to see the data source
        console.log('\n2️⃣ Testing Search Data Source Detection...');
        const searchResponse = await fetch(`${API_BASE_URL}/api/search?q=AAPL`);
        const searchData = await searchResponse.json();
        
        console.log('📊 Data source:', searchData.data_source);
        console.log('🌐 API integration:', searchData.api_integration);
        
        // The Lambda function checks: os.getenv('MARKETSTACK_API_KEY') and os.getenv('MARKETSTACK_API_KEY') != 'demo_key_placeholder'
        // If it's using local_database, either:
        // 1. The environment variable is not set
        // 2. The environment variable equals 'demo_key_placeholder'
        // 3. The API call is failing
        
        if (searchData.data_source === 'local_database') {
            console.log('\n⚠️  ISSUE DETECTED: Using local database instead of MarketStack API');
            console.log('🔍 Possible causes:');
            console.log('   1. MARKETSTACK_API_KEY environment variable not set in Lambda');
            console.log('   2. API key equals "demo_key_placeholder"');
            console.log('   3. MarketStack API calls are failing');
            console.log('   4. API key is invalid or expired');
            
            // Test if we can make a direct API call to MarketStack
            console.log('\n3️⃣ Testing Direct MarketStack API Call...');
            const apiKey = 'b435b1cd06228185916b7b7afd790dc6';
            const testUrl = `http://api.marketstack.com/v1/tickers?access_key=${apiKey}&limit=1`;
            
            try {
                const directResponse = await fetch(testUrl);
                const directData = await directResponse.json();
                
                if (directResponse.ok && directData.data) {
                    console.log('✅ Direct MarketStack API call successful');
                    console.log('📊 API is working, issue is in Lambda configuration');
                    console.log('🔧 Need to set MARKETSTACK_API_KEY environment variable in Lambda');
                } else {
                    console.log('❌ Direct MarketStack API call failed');
                    console.log('📊 Response:', directData);
                    if (directData.error) {
                        console.log('🚨 Error:', directData.error.message);
                    }
                }
            } catch (error) {
                console.log('❌ Direct API test failed:', error.message);
            }
        } else {
            console.log('✅ MarketStack API is active and working correctly');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

// Run the test
testLambdaEnvironment();