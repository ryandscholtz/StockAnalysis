/**
 * Test actual PDF upload functionality with a real file
 */

const fs = require('fs');
const FormData = require('form-data');
const https = require('https');
const http = require('http');
const url = require('url');

const API_BASE_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';

async function testActualPDFUpload() {
    console.log('🔍 Testing Actual PDF Upload Functionality');
    console.log('='.repeat(60));
    
    // Check if test PDF exists
    const testPdfPath = 'test-financial-statement.pdf';
    if (!fs.existsSync(testPdfPath)) {
        console.log('❌ Test PDF not found. Creating one...');
        // Create the test PDF first
        require('./create-test-pdf.js');
        
        // Wait a moment for file creation
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        if (!fs.existsSync(testPdfPath)) {
            console.log('❌ Failed to create test PDF');
            return;
        }
    }
    
    console.log(`📄 Using test PDF: ${testPdfPath}`);
    const fileStats = fs.statSync(testPdfPath);
    console.log(`📊 File size: ${(fileStats.size / 1024).toFixed(2)} KB`);
    
    try {
        // Create form data
        const form = new FormData();
        const fileBuffer = fs.readFileSync(testPdfPath);
        form.append('file', fileBuffer, {
            filename: 'test-financial-statement.pdf',
            contentType: 'application/pdf'
        });
        
        console.log('\n🚀 Uploading PDF to /api/upload-pdf?ticker=AAPL...');
        
        // Upload the PDF using native Node.js HTTP
        const timestamp = Date.now();
        const uploadUrl = `${API_BASE_URL}/api/upload-pdf?ticker=AAPL&v=${timestamp}&cb=${Math.random()}`;
        const parsedUrl = url.parse(uploadUrl);
        
        const options = {
            hostname: parsedUrl.hostname,
            port: parsedUrl.port || 443,
            path: parsedUrl.path,
            method: 'POST',
            headers: form.getHeaders()
        };
        
        const response = await new Promise((resolve, reject) => {
            const req = https.request(options, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    res.body = data;
                    resolve(res);
                });
            });
            
            req.on('error', reject);
            form.pipe(req);
        });
        
        console.log(`📡 Response Status: ${response.statusCode}`);
        console.log(`📡 Response Headers:`, response.headers);
        
        const responseText = response.body;
        console.log(`📡 Response Body: ${responseText}`);
        
        if (response.statusCode >= 200 && response.statusCode < 300) {
            try {
                const data = JSON.parse(responseText);
                console.log('\n✅ PDF Upload Successful!');
                console.log(`   Ticker: ${data.ticker}`);
                console.log(`   Filename: ${data.filename}`);
                console.log(`   Processing Summary: ${data.processing_summary}`);
                console.log(`   Updated Periods: ${data.updated_periods}`);
                console.log(`   Progress Updates: ${data.progress_updates?.length || 0}`);
                
                if (data.extracted_data) {
                    console.log('\n📊 Extracted Data Structure:');
                    console.log(JSON.stringify(data.extracted_data, null, 2));
                }
                
                // Test retrieving the data
                console.log('\n🔍 Testing data retrieval...');
                
                const retrieveOptions = {
                    hostname: 'dx0w31lbc1.execute-api.eu-west-1.amazonaws.com',
                    port: 443,
                    path: '/production/api/manual-data/AAPL',
                    method: 'GET'
                };
                
                const retrieveResponse = await new Promise((resolve, reject) => {
                    const req = https.request(retrieveOptions, (res) => {
                        let data = '';
                        res.on('data', (chunk) => data += chunk);
                        res.on('end', () => {
                            res.body = data;
                            resolve(res);
                        });
                    });
                    req.on('error', reject);
                    req.end();
                });
                
                const retrievedData = JSON.parse(retrieveResponse.body);
                console.log(`📊 Retrieved Data: ${JSON.stringify(retrievedData, null, 2)}`);
                
            } catch (parseError) {
                console.log('⚠️ Response is not JSON, but upload may have succeeded');
                console.log(`Raw response: ${responseText}`);
            }
        } else {
            console.log(`❌ PDF Upload Failed!`);
            console.log(`Status: ${response.statusCode}`);
            console.log(`Response: ${responseText}`);
        }
        
    } catch (error) {
        console.log(`❌ Error during PDF upload: ${error.message}`);
        console.log(`Stack trace: ${error.stack}`);
    }
    
    console.log('\n' + '='.repeat(60));
    console.log('🎯 PDF Upload Test Complete!');
}

// Run the test
testActualPDFUpload().catch(console.error);