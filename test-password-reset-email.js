// Test Password Reset Email with Real User
const AWS = require('aws-sdk');

AWS.config.update({
  region: 'eu-west-1',
  profile: 'Cerebrum'
});

const cognito = new AWS.CognitoIdentityServiceProvider();

const CLIENT_ID = '3mio6147kamjot07p7p27iqdg3';

// Use a verified email address
const TEST_EMAIL = 'ryandscholtz@gmail.com'; // This is verified in SES

async function testPasswordReset() {
  console.log('🧪 Testing Password Reset Email...\n');
  
  console.log('Configuration:');
  console.log('  Client ID:', CLIENT_ID);
  console.log('  Test Email:', TEST_EMAIL);
  console.log('  Region: eu-west-1\n');

  try {
    console.log('Initiating forgot password for:', TEST_EMAIL);
    
    const params = {
      ClientId: CLIENT_ID,
      Username: TEST_EMAIL
    };

    const result = await cognito.forgotPassword(params).promise();
    
    console.log('\n✅ SUCCESS! Password reset initiated');
    console.log('\n📧 Email Details:');
    console.log('  Destination:', result.CodeDeliveryDetails.Destination);
    console.log('  Delivery Medium:', result.CodeDeliveryDetails.DeliveryMedium);
    console.log('  Attribute:', result.CodeDeliveryDetails.AttributeName);
    
    console.log('\n📬 Check your email inbox for:');
    console.log('  From: Stock Analysis <noreply@cerebrum-aec.com>');
    console.log('  Subject: Your verification code');
    console.log('  Content: 6-digit verification code');
    
    console.log('\n⚠️  IMPORTANT NOTES:');
    console.log('  - Check spam/junk folder if not in inbox');
    console.log('  - Email may take 1-2 minutes to arrive');
    console.log('  - SES is in sandbox mode - only verified addresses work');
    console.log('  - Verified addresses: ryandscholtz@gmail.com, admin@cerebrum-aec.com');
    
    console.log('\n🌐 Use the code at:');
    console.log('  https://d3dzzi09nwx2bk.cloudfront.net/auth/reset-password');
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    
    if (error.code === 'UserNotFoundException') {
      console.log('\n⚠️  User does not exist in Cognito');
      console.log('You need to sign up first at:');
      console.log('  https://d3dzzi09nwx2bk.cloudfront.net/auth/signup');
    } else if (error.code === 'LimitExceededException') {
      console.log('\n⚠️  Too many requests - wait a few minutes and try again');
    } else {
      console.log('\nFull error:', error);
    }
  }
}

testPasswordReset();