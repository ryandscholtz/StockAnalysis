#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StockAnalysisStack } from '../lib/stock-analysis-stack';

const app = new cdk.App();

new StockAnalysisStack(app, 'StockAnalysisStack', {
  env: {
    account: process.env.CDK_PRIVATE_ACCOUNT || '771250468817', // Private AWS account
    region: process.env.CDK_DEFAULT_REGION || 'us-east-1',
  },
  description: 'Stock Analysis Application - DynamoDB Table',
});

app.synth();

