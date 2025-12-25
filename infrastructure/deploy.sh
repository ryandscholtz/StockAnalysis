#!/bin/bash
# Quick deployment script for DynamoDB table

set -e

echo "🚀 Deploying Stock Analysis DynamoDB Table..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Run 'aws configure' first."
    exit 1
fi

# Check if CDK is installed
if ! command -v cdk &> /dev/null; then
    echo "❌ CDK CLI not found. Install with: npm install -g aws-cdk"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Bootstrap CDK (if needed)
echo "🔧 Checking CDK bootstrap..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    echo "📚 Bootstrapping CDK (first time only)..."
    cdk bootstrap
else
    echo "✅ CDK already bootstrapped"
fi

# Get private AWS account ID if not set
if [ -z "$CDK_PRIVATE_ACCOUNT" ]; then
    echo "⚠️  CDK_PRIVATE_ACCOUNT not set. Using default private account (771250468817)..."
    export CDK_PRIVATE_ACCOUNT='771250468817'
    echo "Using private account: $CDK_PRIVATE_ACCOUNT"
else
    echo "Using private account: $CDK_PRIVATE_ACCOUNT"
fi

# Deploy
echo "🚀 Deploying stack..."
cdk deploy --require-approval never

echo "✅ Deployment complete!"
echo ""
echo "Table Name: stock-analyses"
echo "To verify: aws dynamodb describe-table --table-name stock-analyses"

