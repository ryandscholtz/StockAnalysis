/**
 * Test script for enhanced Lambda endpoints
 * Tests all available endpoints to ensure they're working correctly
 */

const BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testEndpoint(endpoint, method = 'GET', expectedStatus = 200) {
    try {
        console.log(`\n🧪 Testing ${method} ${endpoint}`);
        
        const response = await fetch(`${BASE_URL}${endpoint}`, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (response.status === expectedStatus) {
            console.log(`✅ SUCCESS: ${response.status} ${response.statusText}`);
            if (endpoint.includes('/analyze/')) {
                // Show key analysis data
                console.log(`   📊 Analysis for ${data.ticker}: ${data.recommendation} (Fair Value: $${data.fair_value}, Current: $${data.current_price})`);
                console.log(`   💰 Margin of Safety: ${data.margin_of_safety_pct}%`);
                console.log(`   🏥 Financial Health: ${data.financial_health?.score}/10`);
                console.log(`   🏢 Business Quality: ${data.business_quality?.score}/10`);
            } else if (endpoint.includes('/watchlist')) {
                if (data.items) {
                    console.log(`   📋 Watchlist items: ${data.items.length}`);
                } else if (data.ticker) {
                    console.log(`   📈 ${data.ticker}: ${data.company_name} - $${data.current_price}`);
                } else if (data.live_prices) {
                    console.log(`   💹 Live prices for ${Object.keys(data.live_prices).length} tickers`);
                }
            } else if (endpoint.includes('/manual-data/')) {
                console.log(`   📊 Financial data for ${data.ticker}: ${data.company_name}`);
                console.log(`   💰 Revenue: $${(data.financial_data?.income_statement?.revenue / 1e9).toFixed(1)}B`);
            } else if (endpoint.includes('/version')) {
                console.log(`   🔖 Version: ${data.version} (${data.api_name})`);
            } else if (endpoint.includes('/health')) {
                console.log(`   ❤️ Status: ${data.status} (${data.message})`);
            }
        } else {
            console.log(`❌ FAILED: Expected ${expectedStatus}, got ${response.status}`);
            console.log(`   Error: ${data.error || data.message || 'Unknown error'}`);
        }
        
        return { success: response.status === expectedStatus, data };
    } catch (error) {
        console.log(`💥 ERROR: ${error.message}`);
        return { success: false, error: error.message };
    }
}

async function runAllTests() {
    console.log('🚀 Testing Enhanced Lambda Function Endpoints');
    console.log('=' * 50);
    
    const tests = [
        // Health and version endpoints
        { endpoint: '/health', expectedStatus: 200 },
        { endpoint: '/api/version', expectedStatus: 200 },
        
        // Watchlist endpoints
        { endpoint: '/api/watchlist', expectedStatus: 200 },
        { endpoint: '/api/watchlist/AAPL', expectedStatus: 200 },
        { endpoint: '/api/watchlist/GOOGL', expectedStatus: 200 },
        { endpoint: '/api/watchlist/live-prices', expectedStatus: 200 },
        
        // Manual data endpoints
        { endpoint: '/api/manual-data/AAPL', expectedStatus: 200 },
        { endpoint: '/api/manual-data/GOOGL', expectedStatus: 200 },
        
        // Analysis endpoints (NEW!)
        { endpoint: '/api/analyze/AAPL', expectedStatus: 200 },
        { endpoint: '/api/analyze/GOOGL', expectedStatus: 200 },
        { endpoint: '/api/analyze/GOOGL?stream=true', expectedStatus: 200 },
        
        // Test unsupported ticker
        { endpoint: '/api/analyze/INVALID', expectedStatus: 404 },
        
        // PDF upload (should return 501)
        { endpoint: '/api/upload-pdf', method: 'POST', expectedStatus: 501 },
        
        // 404 test
        { endpoint: '/api/nonexistent', expectedStatus: 404 }
    ];
    
    let passed = 0;
    let failed = 0;
    
    for (const test of tests) {
        const result = await testEndpoint(test.endpoint, test.method, test.expectedStatus);
        if (result.success) {
            passed++;
        } else {
            failed++;
        }
        
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    console.log('\n' + '=' * 50);
    console.log(`📊 Test Results: ${passed} passed, ${failed} failed`);
    
    if (failed === 0) {
        console.log('🎉 All tests passed! Enhanced Lambda function is working correctly.');
        console.log('\n✨ Key Features Now Available:');
        console.log('   • Watchlist management (GET endpoints)');
        console.log('   • Financial data retrieval');
        console.log('   • Stock analysis with detailed metrics');
        console.log('   • Streaming analysis support');
        console.log('   • Comprehensive error handling');
    } else {
        console.log('⚠️ Some tests failed. Please check the errors above.');
    }
}

// Run the tests
runAllTests().catch(console.error);