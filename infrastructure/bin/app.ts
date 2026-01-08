#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { StockAnalysisStack } from '../lib/stock-analysis-stack';
import { StockAnalysisInfrastructureStack } from '../lib/stock-analysis-infrastructure-stack';

const app = new cdk.App();

// Get environment from context or environment variable
const environment = app.node.tryGetContext('environment') || process.env.ENVIRONMENT || 'development';
const account = process.env.CDK_DEFAULT_ACCOUNT || '295202642810'; // Cerebrum AWS account
const region = process.env.CDK_DEFAULT_REGION || 'eu-west-1';

// Environment-specific configuration
const envConfig = {
  development: {
    domainName: undefined,
    description: 'Stock Analysis Application - Development Environment'
  },
  staging: {
    domainName: undefined,
    description: 'Stock Analysis Application - Staging Environment'
  },
  production: {
    domainName: process.env.DOMAIN_NAME,
    description: 'Stock Analysis Application - Production Environment'
  }
};

const config = envConfig[environment as keyof typeof envConfig] || envConfig.development;

if (environment === 'production' || environment === 'staging') {
  // Use comprehensive infrastructure stack for production and staging
  new StockAnalysisInfrastructureStack(app, `StockAnalysisInfrastructure-${environment}`, {
    environment: environment as 'development' | 'staging' | 'production',
    domainName: config.domainName,
    alertEmail: process.env.ALERT_EMAIL,
    slackWebhookUrl: process.env.SLACK_WEBHOOK_URL,
    env: {
      account,
      region,
    },
    description: config.description,
    tags: {
      Environment: environment,
      Project: 'StockAnalysis',
      ManagedBy: 'CDK'
    }
  });
} else {
  // Use simple DynamoDB-only stack for development
  new StockAnalysisStack(app, 'StockAnalysisStack', {
    env: {
      account,
      region,
    },
    description: 'Stock Analysis Application - DynamoDB Table (Development)',
    tags: {
      Environment: environment,
      Project: 'StockAnalysis',
      ManagedBy: 'CDK'
    }
  });
}

app.synth();

