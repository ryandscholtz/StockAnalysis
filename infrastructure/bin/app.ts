#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StockAnalysisStack } from '../lib/stock-analysis-stack';

const app = new cdk.App();

new StockAnalysisStack(app, 'StockAnalysisStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT || '295202642810', // Cerebrum AWS account
    region: process.env.CDK_DEFAULT_REGION || 'eu-west-1',
  },
  description: 'Stock Analysis Application - DynamoDB Table',
});

app.synth();

