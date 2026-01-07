#!/usr/bin/env node
/**
 * Auto-format frontend code with Prettier
 * Run this script to fix all formatting issues
 */

const { execSync } = require('child_process');
const path = require('path');

console.log('🎨 Auto-formatting frontend code with Prettier...');

try {
  // Change to frontend directory
  process.chdir(__dirname);
  
  // Run Prettier with --write to fix formatting
  const command = 'npx prettier --write "**/*.{js,jsx,ts,tsx,json,css,md}"';
  console.log(`Running: ${command}`);
  
  const output = execSync(command, { encoding: 'utf8' });
  
  if (output.trim()) {
    console.log('📝 Files formatted:');
    console.log(output);
  } else {
    console.log('✅ All files were already properly formatted!');
  }
  
  console.log('🎉 Formatting complete!');
  
} catch (error) {
  console.error('❌ Error running Prettier:');
  console.error(error.message);
  process.exit(1);
}