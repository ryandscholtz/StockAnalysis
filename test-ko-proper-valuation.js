// Test script to verify KO (Coca-Cola) proper valuation
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testKOValuation() {
    try {
        console.log('🧪 Testing KO (Coca-Cola) proper fundamental analysis...');
        
        const response = await fetch(`${API_BASE_URL}/api/analyze/KO`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        const data = await response.json();
        
        console.log('\n📊 KO Analysis Results:');
        console.log('='.repeat(50));
        console.log(`Company: ${data.companyName}`);
        console.log(`Business Type: ${data.businessType}`);
        console.log(`Current Price: $${data.currentPrice?.toFixed(2) || 'N/A'}`);
        console.log(`Fair Value: $${data.fairValue?.toFixed(2) || 'N/A'}`);
        
        if (data.currentPrice && data.fairValue) {
            const marginOfSafety = ((data.fairValue - data.currentPrice) / data.currentPrice) * 100;
            const isUndervalued = marginOfSafety > 0;
            const statusText = isUndervalued ? 
                `${marginOfSafety.toFixed(1)}% Undervalued` : 
                `${Math.abs(marginOfSafety).toFixed(1)}% Overvalued`;
            
            console.log(`Valuation Status: ${statusText} ${isUndervalued ? '🟢' : '🔴'}`);
        }
        
        console.log(`Recommendation: ${data.recommendation}`);
        
        console.log('\n🔍 Valuation Method Breakdown:');
        console.log('-'.repeat(30));
        if (data.valuation) {
            console.log(`DCF Value: $${data.valuation.dcf?.toFixed(2) || 'N/A'} (Weight: ${data.analysisWeights?.dcf_weight ? (data.analysisWeights.dcf_weight * 100).toFixed(0) + '%' : 'N/A'})`);
            console.log(`EPV Value: $${data.valuation.earningsPower?.toFixed(2) || 'N/A'} (Weight: ${data.analysisWeights?.epv_weight ? (data.analysisWeights.epv_weight * 100).toFixed(0) + '%' : 'N/A'})`);
            console.log(`Asset Value: $${data.valuation.assetBased?.toFixed(2) || 'N/A'} (Weight: ${data.analysisWeights?.asset_weight ? (data.analysisWeights.asset_weight * 100).toFixed(0) + '%' : 'N/A'})`);
            console.log(`Weighted Average: $${data.valuation.weightedAverage?.toFixed(2) || 'N/A'}`);
        }
        
        console.log('\n📈 Data Source:');
        console.log('-'.repeat(20));
        if (data.dataSource) {
            console.log(`Price Source: ${data.dataSource.price_source}`);
            console.log(`Has Real Price: ${data.dataSource.has_real_price ? 'Yes' : 'No'}`);
            console.log(`Valuation Method: ${data.dataSource.valuation_method || 'N/A'}`);
        }
        
        // Validation checks
        console.log('\n✅ Validation Checks:');
        console.log('-'.repeat(25));
        
        const checks = [
            {
                name: 'Has Business Type',
                pass: !!data.businessType,
                value: data.businessType
            },
            {
                name: 'Has Real Current Price',
                pass: data.currentPrice && data.currentPrice > 0,
                value: data.currentPrice
            },
            {
                name: 'Has Fair Value',
                pass: data.fairValue && data.fairValue > 0,
                value: data.fairValue
            },
            {
                name: 'Fair Value ≠ 150 (old mock)',
                pass: data.fairValue !== 150,
                value: data.fairValue
            },
            {
                name: 'Has DCF Value',
                pass: data.valuation?.dcf && data.valuation.dcf > 0,
                value: data.valuation?.dcf
            },
            {
                name: 'Has EPV Value',
                pass: data.valuation?.earningsPower && data.valuation.earningsPower > 0,
                value: data.valuation?.earningsPower
            },
            {
                name: 'Has Asset Value',
                pass: data.valuation?.assetBased && data.valuation.assetBased > 0,
                value: data.valuation?.assetBased
            },
            {
                name: 'Has Analysis Weights',
                pass: data.analysisWeights && data.analysisWeights.dcf_weight,
                value: data.analysisWeights ? `DCF:${(data.analysisWeights.dcf_weight*100).toFixed(0)}% EPV:${(data.analysisWeights.epv_weight*100).toFixed(0)}% Asset:${(data.analysisWeights.asset_weight*100).toFixed(0)}%` : null
            },
            {
                name: 'Mature Business Type (Expected for KO)',
                pass: data.businessType === 'Mature',
                value: data.businessType
            }
        ];
        
        let passedChecks = 0;
        checks.forEach(check => {
            const status = check.pass ? '✅' : '❌';
            console.log(`${status} ${check.name}: ${check.value || 'N/A'}`);
            if (check.pass) passedChecks++;
        });
        
        console.log(`\n🎯 Overall Score: ${passedChecks}/${checks.length} checks passed`);
        
        if (passedChecks === checks.length) {
            console.log('🎉 SUCCESS: KO analysis is working correctly with proper fundamental analysis!');
        } else if (passedChecks >= checks.length * 0.8) {
            console.log('⚠️  MOSTLY WORKING: Most checks passed, minor issues detected.');
        } else {
            console.log('❌ ISSUES DETECTED: Several validation checks failed.');
        }
        
        return data;
        
    } catch (error) {
        console.error('❌ Error testing KO valuation:', error.message);
        throw error;
    }
}

// Run the test
testKOValuation()
    .then(() => {
        console.log('\n✨ Test completed successfully!');
    })
    .catch(error => {
        console.error('\n💥 Test failed:', error.message);
        process.exit(1);
    });