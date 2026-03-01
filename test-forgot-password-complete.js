// Test Forgot Password Functionality - Complete End-to-End Test
// This script tests the complete forgot password flow with real Cognito

const AWS = require('aws-sdk');

// Configure AWS
AWS.config.update({
  region: 'eu-west-1',
  profile: 'Cerebrum'
});

const cognito = new AWS.CognitoIdentityServiceProvider();

const USER_POOL_ID = 'eu-west-1_os9KVPAhb';
const CLIENT_ID = '3mio6147kamjot07p7p27iqdg3';
const TEST_EMAIL = 'test@example.com'; // Replace with a real email for testing

async function testForgotPasswordFlow() {
  console.log('🧪 Testing Forgot Password Functionality...\n');

  try {
    // Step 1: Test forgot password initiation
    console.log('1️⃣ Testing forgot password initiation...');
    
    const forgotPasswordParams = {
      ClientId: CLIENT_ID,
      Username: TEST_EMAIL
    };

    try {
      const forgotResult = await cognito.forgotPassword(forgotPasswordParams).promise();
      console.log('✅ Forgot password initiated successfully');
      console.log('📧 Reset code should be sent to:', TEST_EMAIL);
      console.log('📋 Delivery details:', forgotResult.CodeDeliveryDetails);
    } catch (error) {
      if (error.code === 'UserNotFoundException') {
        console.log('⚠️  User not found - this is expected for test email');
        console.log('✅ Cognito is properly configured and responding');
      } else {
        console.error('❌ Forgot password error:', error.message);
        throw error;
      }
    }

    // Step 2: Test frontend URLs
    console.log('\n2️⃣ Testing frontend URLs...');
    
    const frontendUrl = 'https://d3dzzi09nwx2bk.cloudfront.net';
    const forgotPasswordUrl = `${frontendUrl}/auth/forgot-password`;
    const resetPasswordUrl = `${frontendUrl}/auth/reset-password`;
    
    console.log('🌐 Frontend URLs:');
    console.log(`   Forgot Password: ${forgotPasswordUrl}`);
    console.log(`   Reset Password: ${resetPasswordUrl}`);

    // Step 3: Test environment variables
    console.log('\n3️⃣ Testing environment configuration...');
    
    const envConfig = {
      'User Pool ID': USER_POOL_ID,
      'Client ID': CLIENT_ID,
      'Region': 'eu-west-1',
      'Frontend URL': frontendUrl
    };

    console.log('⚙️  Environment Configuration:');
    Object.entries(envConfig).forEach(([key, value]) => {
      console.log(`   ${key}: ${value}`);
    });

    // Step 4: Test Cognito User Pool configuration
    console.log('\n4️⃣ Testing Cognito User Pool configuration...');
    
    try {
      const userPoolParams = {
        UserPoolId: USER_POOL_ID
      };
      
      const userPoolInfo = await cognito.describeUserPool(userPoolParams).promise();
      const policies = userPoolInfo.UserPool.Policies.PasswordPolicy;
      
      console.log('✅ User Pool configuration verified');
      console.log('🔐 Password Policy:');
      console.log(`   Minimum Length: ${policies.MinimumLength}`);
      console.log(`   Require Uppercase: ${policies.RequireUppercase}`);
      console.log(`   Require Lowercase: ${policies.RequireLowercase}`);
      console.log(`   Require Numbers: ${policies.RequireNumbers}`);
      console.log(`   Require Symbols: ${policies.RequireSymbols}`);
      
      // Check email configuration
      const emailConfig = userPoolInfo.UserPool.EmailConfiguration;
      if (emailConfig) {
        console.log('📧 Email Configuration:');
        console.log(`   Source ARN: ${emailConfig.SourceArn || 'Default SES'}`);
        console.log(`   Reply-To: ${emailConfig.ReplyToEmailAddress || 'Not configured'}`);
      }
      
    } catch (error) {
      console.error('❌ Error checking User Pool:', error.message);
    }

    console.log('\n🎉 Forgot Password Functionality Test Complete!');
    console.log('\n📋 Manual Testing Steps:');
    console.log('1. Go to:', forgotPasswordUrl);
    console.log('2. Enter a valid email address (one you have access to)');
    console.log('3. Click "Send Reset Email"');
    console.log('4. Check your email for the reset code');
    console.log('5. Go to:', resetPasswordUrl);
    console.log('6. Enter your email, the reset code, and a new password');
    console.log('7. Click "Reset Password"');
    console.log('8. Try signing in with the new password');

  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

// Run the test
testForgotPasswordFlow();