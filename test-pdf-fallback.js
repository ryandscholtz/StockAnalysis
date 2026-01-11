/**
 * Test script to verify PDF-to-image fallback functionality
 */

const fs = require('fs');
const FormData = require('form-data');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testPDFFallback() {
    console.log('🔄 Testing PDF-to-image fallback functionality...');
    
    try {
        // Create a more complex test PDF that might trigger Textract issues
        const testContent = Buffer.from(`%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Amazon Financial Report 2024) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000074 00000 n 
0000000120 00000 n 
0000000179 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
273
%%EOF`);
        
        // Create form data
        const form = new FormData();
        form.append('file', testContent, {
            filename: 'amazon-test-report.pdf',
            contentType: 'application/pdf'
        });
        
        console.log('📤 Uploading test PDF for AMZN...');
        
        const response = await fetch(`${API_BASE}/api/upload-pdf?ticker=AMZN`, {
            method: 'POST',
            body: form,
            headers: form.getHeaders()
        });
        
        console.log(`Response status: ${response.status} ${response.statusText}`);
        
        const result = await response.json();
        console.log('Response body:');
        console.log(JSON.stringify(result, null, 2));
        
        // Check the extraction method
        if (result.success && result.extracted_data && result.extracted_data.extraction_metadata) {
            const method = result.extracted_data.extraction_metadata.extraction_method;
            console.log(`\n📊 Extraction method: ${method}`);
            
            if (method === 'text_extraction_empty') {
                console.log('✅ PDF processed successfully but no text extracted (expected for simple test PDF)');
            } else if (method === 'ai_powered_textract') {
                console.log('✅ Direct Textract processing worked');
            } else if (method === 'processing_exception') {
                console.log('❌ Processing failed with exception');
            } else {
                console.log(`ℹ️ Unexpected extraction method: ${method}`);
            }
        }
        
        // Now check if the data was saved
        console.log('\n🔍 Checking if data was saved to database...');
        const dataResponse = await fetch(`${API_BASE}/api/manual-data/AMZN`);
        const dataResult = await dataResponse.json();
        
        console.log('Database data:');
        console.log(JSON.stringify(dataResult, null, 2));
        
        if (dataResult.data_source === 'pdf_extracted') {
            console.log('✅ Data was saved to database with PDF extraction source');
        } else {
            console.log('❌ Data was not saved or has different source');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run the test
testPDFFallback();