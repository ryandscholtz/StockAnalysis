/**
 * Test company name search functionality
 */

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testCompanyNameSearch() {
    console.log('🔍 Testing Company Name Search...\n');
    
    const testQueries = [
        // Current working searches
        { query: 'APPLE', expected: 'AAPL', description: 'Apple Inc.' },
        { query: 'MICROSOFT', expected: 'MSFT', description: 'Microsoft Corporation' },
        { query: 'TESLA', expected: 'TSLA', description: 'Tesla Inc.' },
        { query: 'AMAZON', expected: 'AMZN', description: 'Amazon.com Inc.' },
        { query: 'NVIDIA', expected: 'NVDA', description: 'NVIDIA Corporation' },
        { query: 'ORACLE', expected: 'ORCL', description: 'Oracle Corporation' },
        
        // Partial company names
        { query: 'ALPHABET', expected: 'GOOGL', description: 'Alphabet Inc.' },
        { query: 'META', expected: 'META', description: 'Meta Platforms' },
        { query: 'NETFLIX', expected: 'NFLX', description: 'Netflix Inc.' },
        
        // International companies
        { query: 'SHOPIFY', expected: 'SHOP.TO', description: 'Shopify Inc. (Canada)' },
        { query: 'COMMONWEALTH', expected: 'CBA.AX', description: 'Commonwealth Bank (Australia)' },
        { query: 'ROYAL BANK', expected: 'RY.TO', description: 'Royal Bank of Canada' },
        
        // Missing companies that should be added
        { query: 'BELL EQUIPMENT', expected: null, description: 'Bell Equipment (South African)' },
        { query: 'CATERPILLAR', expected: null, description: 'Caterpillar Inc.' },
        { query: 'JOHN DEERE', expected: null, description: 'Deere & Company' },
        { query: 'BOEING', expected: null, description: 'The Boeing Company' },
        { query: 'GENERAL ELECTRIC', expected: null, description: 'General Electric' },
        { query: 'IBM', expected: 'IBM', description: 'International Business Machines' },
    ];
    
    try {
        for (const test of testQueries) {
            console.log(`🔍 Testing: "${test.query}" (${test.description})`);
            
            const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(test.query)}`);
            
            if (!response.ok) {
                console.log(`❌ Search failed: ${response.status}`);
                console.log('');
                continue;
            }
            
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                const topResult = data.results[0];
                console.log(`✅ Found: ${topResult.ticker} - ${topResult.name}`);
                console.log(`📊 Exchange: ${topResult.exchange} (${topResult.country})`);
                console.log(`📊 Match type: ${topResult.match_type} (${topResult.relevance_score}% relevance)`);
                
                if (test.expected && topResult.ticker === test.expected) {
                    console.log('🎯 Correct match found!');
                } else if (test.expected) {
                    console.log(`⚠️ Expected ${test.expected}, got ${topResult.ticker}`);
                } else {
                    console.log('ℹ️ Company found (not in expected list)');
                }
            } else {
                console.log('❌ No results found');
                if (test.expected) {
                    console.log(`⚠️ Expected to find ${test.expected}`);
                } else {
                    console.log('ℹ️ Company not in database (as expected)');
                }
            }
            
            console.log('');
        }
        
        // Test specific missing companies
        console.log('🔍 Testing specific missing companies...\n');
        
        const missingCompanies = [
            'BELL EQUIPMENT',
            'CATERPILLAR', 
            'JOHN DEERE',
            'BOEING',
            'GENERAL ELECTRIC',
            'LOCKHEED MARTIN',
            'RAYTHEON',
            'HONEYWELL',
            'SIEMENS',
            'ABB'
        ];
        
        let foundCount = 0;
        let missingCount = 0;
        
        for (const company of missingCompanies) {
            const response = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(company)}`);
            if (response.ok) {
                const data = await response.json();
                if (data.results && data.results.length > 0) {
                    console.log(`✅ ${company}: Found ${data.results[0].ticker} - ${data.results[0].name}`);
                    foundCount++;
                } else {
                    console.log(`❌ ${company}: Not found`);
                    missingCount++;
                }
            }
        }
        
        console.log(`\\n📊 Summary: ${foundCount} found, ${missingCount} missing`);
        
        if (missingCount > 0) {
            console.log('\\n💡 Recommendations:');
            console.log('1. Add more industrial/equipment companies to the database');
            console.log('2. Include major aerospace and defense companies');
            console.log('3. Add more international companies from emerging markets');
            console.log('4. Consider integrating with real MarketStack API for comprehensive coverage');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error.message);
    }
}

testCompanyNameSearch();