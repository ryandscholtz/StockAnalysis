#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StockAnalysisInfrastructureStack } from '../lib/stock-analysis-infrastructure-stack';

const app = new cdk.App();

// Get environment from context or default to development
const environment = app.node.tryGetContext('environment') || 'development';
const domainName = app.node.tryGetContext('domainName');

// Create stack with environment-specific configuration
new StockAnalysisInfrastructureStack(app, `StockAnalysisInfrastructureStack-${environment}`, {
  environment: environment as 'development' | 'staging' | 'production',
  domainName: domainName,
  
  // Stack-level configuration
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  
  // Tags for resource management
  tags: {
    Project: 'StockAnalysis',
    Environment: environment,
    ManagedBy: 'CDK'
  },
  
  // Stack description
  description: `Stock Analysis Infrastructure Stack for ${environment} environment`
});

// Add metadata
app.node.setContext('@aws-cdk/core:enableStackNameDuplicates', true);
app.node.setContext('@aws-cdk/aws-lambda:recognizeLayerVersion', true);
app.node.setContext('@aws-cdk/aws-cloudfront:defaultSecurityPolicyTLSv1.2_2021', true);