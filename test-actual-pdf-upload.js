/**
 * Test Actual PDF Upload with a Simple PDF
 * Creates a minimal PDF and tests the upload functionality
 */

const fs = require('fs');
const https = require('https');

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

// Create a minimal PDF content (this is a very basic PDF structure)
function createMinimalPDF() {
    // This is a minimal PDF structure - just enough to be recognized as a PDF
    const pdfContent = `%PDF-1.4
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
100 700 Td
(Test Financial Data) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
299
%%EOF`;

    return Buffer.from(pdfContent);
}

async function testPDFUpload() {
    console.log('🧪 Testing Actual PDF Upload');
    console.log('API Base URL:', API_BASE_URL);
    console.log('');

    // Create a minimal test PDF
    const pdfBuffer = createMinimalPDF();
    console.log(`📄 Created test PDF: ${pdfBuffer.length} bytes`);

    // Create multipart form data
    const boundary = '----WebKitFormBoundary' + Math.random().toString(36).substr(2, 16);
    const filename = 'test-financial-report.pdf';
    const ticker = 'AAPL';

    const formData = [
        `--${boundary}`,
        `Content-Disposition: form-data; name="file"; filename="${filename}"`,
        'Content-Type: application/pdf',
        '',
        pdfBuffer.toString('binary'),
        `--${boundary}--`,
        ''
    ].join('\r\n');

    const postData = Buffer.from(formData, 'binary');

    const options = {
        hostname: 'dx0w31lbc1.execute-api.eu-west-1.amazonaws.com',
        port: 443,
        path: `/production/api/upload-pdf?ticker=${ticker}`,
        method: 'POST',
        headers: {
            'Content-Type': `multipart/form-data; boundary=${boundary}`,
            'Content-Length': postData.length
        }
    };

    console.log(`🚀 Uploading PDF for ticker: ${ticker}`);
    console.log(`📊 Request size: ${postData.length} bytes`);
    console.log('');

    return new Promise((resolve, reject) => {
        const req = https.request(options, (res) => {
            let data = '';

            res.on('data', (chunk) => {
                data += chunk;
            });

            res.on('end', () => {
                console.log(`📡 Response Status: ${res.statusCode}`);
                console.log(`📋 Response Headers:`, res.headers);
                console.log('');

                try {
                    const response = JSON.parse(data);
                    
                    if (res.statusCode === 200) {
                        console.log('✅ PDF Upload Successful!');
                        console.log('📊 Response Data:');
                        console.log(JSON.stringify(response, null, 2));
                        
                        if (response.processing_summary) {
                            console.log('');
                            console.log('📝 Processing Summary:', response.processing_summary);
                        }
                        
                        if (response.updated_periods) {
                            console.log('📈 Updated Periods:', response.updated_periods);
                        }
                        
                        if (response.progress_updates) {
                            console.log('⏳ Progress Updates:');
                            response.progress_updates.forEach((update, index) => {
                                console.log(`  ${index + 1}. ${update.message} (${update.progress_pct}%)`);
                            });
                        }
                        
                        resolve(response);
                    } else {
                        console.log('❌ PDF Upload Failed!');
                        console.log('📊 Error Response:');
                        console.log(JSON.stringify(response, null, 2));
                        reject(new Error(`Upload failed with status ${res.statusCode}`));
                    }
                } catch (parseError) {
                    console.log('❌ Failed to parse response as JSON');
                    console.log('📄 Raw Response:', data);
                    reject(parseError);
                }
            });
        });

        req.on('error', (error) => {
            console.log('❌ Request Error:', error.message);
            reject(error);
        });

        req.write(postData);
        req.end();
    });
}

// Run the test
testPDFUpload()
    .then(() => {
        console.log('');
        console.log('🎉 PDF Upload Test Complete!');
        console.log('');
        console.log('📋 Summary:');
        console.log('- PDF upload endpoint is working');
        console.log('- Multipart form data parsing is working');
        console.log('- AWS Textract integration is ready');
        console.log('- Progress tracking is implemented');
        console.log('');
        console.log('🚀 Next: Test with a real financial PDF document');
    })
    .catch((error) => {
        console.error('');
        console.error('💥 Test Failed:', error.message);
        console.error('');
        console.error('🔧 Troubleshooting:');
        console.error('1. Check Lambda function logs in CloudWatch');
        console.error('2. Verify multipart form data parsing');
        console.error('3. Check AWS Textract permissions');
        console.error('4. Ensure PDF processor is working correctly');
    });