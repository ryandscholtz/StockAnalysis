// Debug script to check KO business type classification
const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function debugKOBusinessType() {
    try {
        console.log('🔍 Debugging KO business type classification...');
        
        const response = await fetch(`${API_BASE_URL}/api/analyze/KO`);
        const data = await response.json();
        
        console.log('\n📊 Raw Response Data:');
        console.log('Business Type:', data.businessType);
        console.log('Analysis Weights:', data.analysisWeights);
        
        // Expected for KO (Mature business type):
        // DCF: 50%, EPV: 35%, Asset: 15%
        
        console.log('\n🎯 Expected vs Actual:');
        console.log('Expected Business Type: Mature');
        console.log('Actual Business Type:', data.businessType);
        
        console.log('\nExpected Weights: DCF 50%, EPV 35%, Asset 15%');
        console.log('Actual Weights:', 
            `DCF ${data.analysisWeights?.dcf_weight ? (data.analysisWeights.dcf_weight * 100).toFixed(0) + '%' : 'N/A'}, ` +
            `EPV ${data.analysisWeights?.epv_weight ? (data.analysisWeights.epv_weight * 100).toFixed(0) + '%' : 'N/A'}, ` +
            `Asset ${data.analysisWeights?.asset_weight ? (data.analysisWeights.asset_weight * 100).toFixed(0) + '%' : 'N/A'}`
        );
        
        // Check if weights match any known preset
        const weights = data.analysisWeights;
        if (weights) {
            const dcf = Math.round(weights.dcf_weight * 100);
            const epv = Math.round(weights.epv_weight * 100);
            const asset = Math.round(weights.asset_weight * 100);
            
            console.log('\n🔍 Weight Pattern Analysis:');
            if (dcf === 50 && epv === 35 && asset === 15) {
                console.log('✅ Matches Mature/Technology/Healthcare/Retail preset');
            } else if (dcf === 55 && epv === 25 && asset === 20) {
                console.log('✅ Matches High Growth preset');
            } else if (dcf === 25 && epv === 50 && asset === 25) {
                console.log('✅ Matches Bank/Cyclical preset');
            } else if (dcf === 50 && epv === 30 && asset === 20) {
                console.log('❓ Matches Default preset (50/30/20) - this suggests KO mapping failed');
            } else {
                console.log('❓ Unknown weight pattern');
            }
        }
        
        console.log('\n📝 Diagnosis:');
        if (data.businessType === 'Technology' && 
            data.analysisWeights?.dcf_weight === 0.5 && 
            data.analysisWeights?.epv_weight === 0.3 && 
            data.analysisWeights?.asset_weight === 0.2) {
            console.log('❌ ISSUE: Using default weights (50/30/20) instead of KO-specific Mature weights (50/35/15)');
            console.log('   This suggests the business type mapping is not working correctly.');
        } else if (data.businessType === 'Mature') {
            console.log('✅ Business type is correct');
        } else {
            console.log('❓ Unexpected business type or weights');
        }
        
    } catch (error) {
        console.error('❌ Error debugging KO business type:', error.message);
    }
}

debugKOBusinessType();