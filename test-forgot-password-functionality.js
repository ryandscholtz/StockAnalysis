// Test script to verify forgot password functionality
// Run this in the browser console on the deployed app

async function testForgotPasswordFlow() {
  console.log('🧪 Testing Forgot Password Functionality');
  
  // Test 1: Check if forgot password page loads
  console.log('\n1. Testing forgot password page access...');
  try {
    const response = await fetch('https://d3dzzi09nwx2bk.cloudfront.net/auth/forgot-password');
    if (response.ok) {
      console.log('✅ Forgot password page is accessible');
    } else {
      console.log('❌ Forgot password page failed to load:', response.status);
    }
  } catch (error) {
    console.log('❌ Error accessing forgot password page:', error);
  }
  
  // Test 2: Check if reset password page loads
  console.log('\n2. Testing reset password page access...');
  try {
    const response = await fetch('https://d3dzzi09nwx2bk.cloudfront.net/auth/reset-password');
    if (response.ok) {
      console.log('✅ Reset password page is accessible');
    } else {
      console.log('❌ Reset password page failed to load:', response.status);
    }
  } catch (error) {
    console.log('❌ Error accessing reset password page:', error);
  }
  
  // Test 3: Check if the link from signin page works
  console.log('\n3. Testing forgot password link from signin page...');
  try {
    const signinResponse = await fetch('https://d3dzzi09nwx2bk.cloudfront.net/auth/signin');
    const signinHtml = await signinResponse.text();
    
    if (signinHtml.includes('/auth/forgot-password')) {
      console.log('✅ Forgot password link found in signin page');
    } else {
      console.log('❌ Forgot password link not found in signin page');
    }
  } catch (error) {
    console.log('❌ Error checking signin page:', error);
  }
  
  // Test 4: Verify pages contain expected content
  console.log('\n4. Testing page content...');
  try {
    const forgotResponse = await fetch('https://d3dzzi09nwx2bk.cloudfront.net/auth/forgot-password');
    const forgotHtml = await forgotResponse.text();
    
    if (forgotHtml.includes('Forgot Password') && forgotHtml.includes('email')) {
      console.log('✅ Forgot password page contains expected content');
    } else {
      console.log('❌ Forgot password page missing expected content');
    }
    
    const resetResponse = await fetch('https://d3dzzi09nwx2bk.cloudfront.net/auth/reset-password');
    const resetHtml = await resetResponse.text();
    
    if (resetHtml.includes('Reset Your Password') && resetHtml.includes('verification code')) {
      console.log('✅ Reset password page contains expected content');
    } else {
      console.log('❌ Reset password page missing expected content');
    }
  } catch (error) {
    console.log('❌ Error checking page content:', error);
  }
  
  console.log('\n🎯 Test Summary:');
  console.log('- Forgot password page: https://d3dzzi09nwx2bk.cloudfront.net/auth/forgot-password');
  console.log('- Reset password page: https://d3dzzi09nwx2bk.cloudfront.net/auth/reset-password');
  console.log('- Link from signin page should work');
  console.log('\n💡 To test the full flow:');
  console.log('1. Go to signin page');
  console.log('2. Click "Forgot your password?" link');
  console.log('3. Enter your email address');
  console.log('4. Check your email for the reset code');
  console.log('5. Use the reset password page to set a new password');
}

// Run the test
testForgotPasswordFlow();