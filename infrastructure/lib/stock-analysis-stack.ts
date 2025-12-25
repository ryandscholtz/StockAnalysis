import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export class StockAnalysisStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB Table for Stock Analyses
    const stockAnalysesTable = new dynamodb.Table(this, 'StockAnalysesTable', {
      tableName: 'stock-analyses',
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST, // On-demand pricing
      removalPolicy: cdk.RemovalPolicy.RETAIN, // Retain table on stack deletion
      pointInTimeRecovery: true, // Enable PITR for backups
      
      // Encryption at rest
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
    });

    // GSI1: Exchange-Date Index
    // Query pattern: Get all stocks for an exchange on a specific date
    stockAnalysesTable.addGlobalSecondaryIndex({
      indexName: 'GSI1-ExchangeDate',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
    });

    // GSI2: Recommendation-Date Index
    // Query pattern: Get all BUY/HOLD/AVOID recommendations for a date
    stockAnalysesTable.addGlobalSecondaryIndex({
      indexName: 'GSI2-RecommendationDate',
      partitionKey: { name: 'GSI2PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI2SK', type: dynamodb.AttributeType.STRING },
    });

    // GSI3: Sector-Quality Index
    // Query pattern: Find high-quality stocks in a sector
    stockAnalysesTable.addGlobalSecondaryIndex({
      indexName: 'GSI3-SectorQuality',
      partitionKey: { name: 'GSI3PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI3SK', type: dynamodb.AttributeType.STRING },
    });

    // Outputs
    new cdk.CfnOutput(this, 'TableName', {
      value: stockAnalysesTable.tableName,
      description: 'DynamoDB Table Name',
      exportName: 'StockAnalysesTableName',
    });

    new cdk.CfnOutput(this, 'TableArn', {
      value: stockAnalysesTable.tableArn,
      description: 'DynamoDB Table ARN',
    });

    new cdk.CfnOutput(this, 'Region', {
      value: this.region,
      description: 'AWS Region',
    });
  }
}

