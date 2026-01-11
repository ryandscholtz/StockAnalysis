const https = require('https');
const fs = require('fs');
const path = require('path');

function testPDFUpload() {
    return new Promise((resolve, reject) => {
        // Create a simple test PDF content (mock)
        const testPDFContent = Buffer.from('%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000074 00000 n \n0000000120 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n179\n%%EOF');
        
        // Create multipart form data
        const boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW';
        const formData = [
            `--${boundary}`,
            'Content-Disposition: form-data; name="file"; filename="test-financial-statement.pdf"',
            'Content-Type: application/pdf',
            '',
            testPDFContent.toString('binary'),
            `--${boundary}--`
        ].join('\r\n');
        
        const postData = Buffer.from(formData, 'binary');
        
        const options = {
            hostname: 'dx0w31lbc1.execute-api.eu-west-1.amazonaws.com',
            port: 443,
            path: '/production/api/upload-pdf?ticker=GOOGL',
            method: 'POST',
            headers: {
                'Content-Type': `multipart/form-data; boundary=${boundary}`,
                'Content-Length': postData.length
            }
        };
        
        const req = https.request(options, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    console.log('=== PDF Upload Test ===');
                    console.log('Status:', res.statusCode);
                    console.log('Headers:', res.headers);
                    
                    if (res.statusCode === 200) {
                        const response = JSON.parse(data);
                        console.log('✅ PDF Upload Success!');
                        console.log('Response:', JSON.stringify(response, null, 2));
                        resolve(response);
                    } else {
                        console.log('❌ PDF Upload Failed');
                        console.log('Response:', data);
                        reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                    }
                } catch (error) {
                    console.error('Error parsing response:', error);
                    console.log('Raw response:', data);
                    reject(error);
                }
            });
        });
        
        req.on('error', (error) => {
            console.error('Request error:', error);
            reject(error);
        });
        
        req.write(postData);
        req.end();
    });
}

testPDFUpload().catch(console.error);