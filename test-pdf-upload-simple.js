/**
 * Simple test to upload a PDF and check if the fix worked
 */

const fs = require('fs');
const FormData = require('form-data');
const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

const API_BASE = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testSimplePDFUpload() {
    console.log('📄 Testing simple PDF upload...');
    
    try {
        // Create a simple test PDF content (this won't be a real PDF, just for testing the endpoint)
        const testContent = Buffer.from('%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF');
        
        // Create form data
        const form = new FormData();
        form.append('file', testContent, {
            filename: 'test-simple.pdf',
            contentType: 'application/pdf'
        });
        
        console.log('📤 Uploading test PDF...');
        
        const response = await fetch(`${API_BASE}/api/upload-pdf?ticker=TEST`, {
            method: 'POST',
            body: form,
            headers: form.getHeaders()
        });
        
        console.log(`Response status: ${response.status} ${response.statusText}`);
        
        const result = await response.json();
        console.log('Response body:');
        console.log(JSON.stringify(result, null, 2));
        
        if (response.status === 200) {
            console.log('✅ PDF upload endpoint is working!');
        } else {
            console.log('❌ PDF upload failed');
        }
        
    } catch (error) {
        console.error('❌ Test failed:', error);
    }
}

// Run the test
testSimplePDFUpload();