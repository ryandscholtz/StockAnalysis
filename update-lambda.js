const AWS = require('aws-sdk');
const fs = require('fs');

// Configure AWS
const lambda = new AWS.Lambda({
    region: 'us-east-1'
});

const functionName = 'stock-analysis-api-production';
const zipFilePath = 'backend/dist.zip';

async function updateLambdaFunction() {
    try {
        console.log('Reading zip file...');
        const zipBuffer = fs.readFileSync(zipFilePath);
        
        console.log(`Updating Lambda function: ${functionName}`);
        console.log(`Zip file size: ${zipBuffer.length} bytes`);
        
        const params = {
            FunctionName: functionName,
            ZipFile: zipBuffer
        };
        
        const result = await lambda.updateFunctionCode(params).promise();
        
        console.log('✅ Lambda function updated successfully!');
        console.log('Function ARN:', result.FunctionArn);
        console.log('Last Modified:', result.LastModified);
        console.log('Code Size:', result.CodeSize);
        
    } catch (error) {
        console.error('❌ Error updating Lambda function:', error.message);
        if (error.code) {
            console.error('Error Code:', error.code);
        }
        process.exit(1);
    }
}

updateLambdaFunction();