import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatchActions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface StockAnalysisInfrastructureStackProps extends cdk.StackProps {
  environment: 'development' | 'staging' | 'production';
  domainName?: string;
  alertEmail?: string;
  slackWebhookUrl?: string;
}

export class StockAnalysisInfrastructureStack extends cdk.Stack {
  public readonly api: apigateway.RestApi;
  public readonly table: dynamodb.Table;
  public readonly apiFunction: lambda.Function;
  public readonly alertTopic: sns.Topic;
  public readonly criticalAlertTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: StockAnalysisInfrastructureStackProps) {
    super(scope, id, props);

    const { environment, alertEmail, slackWebhookUrl } = props;

    // DynamoDB Table for stock analyses
    this.table = new dynamodb.Table(this, 'StockAnalysesTable', {
      tableName: `stock-analyses-${environment}`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: environment === 'production',
      encryption: dynamodb.TableEncryption.AWS_MANAGED,
      removalPolicy: environment === 'production' 
        ? cdk.RemovalPolicy.RETAIN 
        : cdk.RemovalPolicy.DESTROY,
    });

    // Add Global Secondary Indexes
    this.table.addGlobalSecondaryIndex({
      indexName: 'ExchangeDateIndex',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
    });

    this.table.addGlobalSecondaryIndex({
      indexName: 'RecommendationDateIndex',
      partitionKey: { name: 'GSI2PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI2SK', type: dynamodb.AttributeType.STRING },
    });

    this.table.addGlobalSecondaryIndex({
      indexName: 'SectorQualityIndex',
      partitionKey: { name: 'GSI3PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI3SK', type: dynamodb.AttributeType.STRING },
    });

    // Secrets Manager for sensitive configuration
    const apiSecrets = new secretsmanager.Secret(this, 'ApiSecrets', {
      secretName: `stock-analysis-secrets-${environment}`,
      description: 'Sensitive configuration for Stock Analysis API',
      generateSecretString: {
        secretStringTemplate: JSON.stringify({
          jwt_secret: '',
          encryption_key: '',
          external_api_keys: {}
        }),
        generateStringKey: 'jwt_secret',
        excludeCharacters: '"@/\\'
      }
    });

    // Lambda execution role with proper permissions
    const lambdaRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole'),
        iam.ManagedPolicy.fromAwsManagedPolicyName('AWSXRayDaemonWriteAccess')
      ],
      inlinePolicies: {
        DynamoDBAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'dynamodb:GetItem',
                'dynamodb:PutItem',
                'dynamodb:UpdateItem',
                'dynamodb:DeleteItem',
                'dynamodb:Query',
                'dynamodb:Scan'
              ],
              resources: [
                this.table.tableArn,
                `${this.table.tableArn}/index/*`
              ]
            })
          ]
        }),
        SecretsManagerAccess: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'secretsmanager:GetSecretValue'
              ],
              resources: [apiSecrets.secretArn]
            })
          ]
        }),
        CloudWatchMetrics: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'cloudwatch:PutMetricData'
              ],
              resources: ['*']
            })
          ]
        })
      }
    });

    // Lambda function for the API
    this.apiFunction = new lambda.Function(this, 'ApiFunction', {
      functionName: `stock-analysis-api-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'simple_lambda_handler.lambda_handler',
      code: lambda.Code.fromAsset('../backend/dist'), // Assumes packaged code
      role: lambdaRole,
      timeout: cdk.Duration.seconds(900), // 15 minutes for complex analysis
      memorySize: environment === 'production' ? 3008 : 1024, // Max memory for production
      
      // Environment variables
      environment: {
        ENVIRONMENT: environment,
        TABLE_NAME: this.table.tableName,
        SECRETS_ARN: apiSecrets.secretArn,
        LOG_LEVEL: environment === 'production' ? 'INFO' : 'DEBUG',
        STRUCTURED_LOGGING: 'true'
      },
      
      // Enable X-Ray tracing
      tracing: lambda.Tracing.ACTIVE,
      
      // Log retention
      logRetention: environment === 'production' 
        ? logs.RetentionDays.ONE_MONTH 
        : logs.RetentionDays.ONE_WEEK
    });

    // API Gateway with rate limiting and explicit CORS
    this.api = new apigateway.RestApi(this, 'StockAnalysisApi', {
      restApiName: `Stock Analysis API - ${environment}`,
      description: `Serverless stock analysis API for ${environment}`,
      
      // CORS configuration
      defaultCorsPreflightOptions: {
        allowOrigins: [
          'http://localhost:3000',
          'http://localhost:3001', 
          'http://127.0.0.1:3000',
          'https://stockanalysis.cerebrum.com'
        ],
        allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowHeaders: [
          'Content-Type', 
          'X-Amz-Date', 
          'Authorization', 
          'X-Api-Key', 
          'X-Correlation-Id',
          'X-Requested-With'
        ],
        allowCredentials: false,
        maxAge: cdk.Duration.seconds(86400)
      },
      
      // API Gateway logging
      deployOptions: {
        stageName: environment,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: environment !== 'production',
        metricsEnabled: true,
      }
    });

    // Lambda integration with CORS
    const lambdaIntegration = new apigateway.LambdaIntegration(this.apiFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' },
      integrationResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': "'*'",
          'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Requested-With'",
          'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'"
        }
      }]
    });

    // API Gateway routes
    const apiResource = this.api.root.addResource('api');
    
    // Health check endpoint with explicit CORS
    const healthResource = this.api.root.addResource('health');
    healthResource.addMethod('GET', lambdaIntegration, {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Methods': true
        }
      }]
    });
    
    // Documentation endpoint
    const docsResource = this.api.root.addResource('docs');
    docsResource.addMethod('GET', lambdaIntegration, {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Methods': true
        }
      }]
    });
    
    // OpenAPI specification endpoint
    const openapiResource = this.api.root.addResource('openapi.json');
    openapiResource.addMethod('GET', lambdaIntegration, {
      methodResponses: [{
        statusCode: '200',
        responseParameters: {
          'method.response.header.Access-Control-Allow-Origin': true,
          'method.response.header.Access-Control-Allow-Headers': true,
          'method.response.header.Access-Control-Allow-Methods': true
        }
      }]
    });
    
    // Main API routes (proxy all to Lambda)
    apiResource.addProxy({
      defaultIntegration: lambdaIntegration,
      anyMethod: true
    });
    
    // Add root proxy to catch all other routes for FastAPI
    this.api.root.addProxy({
      defaultIntegration: lambdaIntegration,
      anyMethod: true
    });

    // Usage plan for rate limiting
    const usagePlan = this.api.addUsagePlan('DefaultUsagePlan', {
      name: `stock-analysis-usage-plan-${environment}`,
      throttle: {
        rateLimit: environment === 'production' ? 1000 : 100,
        burstLimit: environment === 'production' ? 2000 : 200
      },
      quota: {
        limit: environment === 'production' ? 100000 : 10000,
        period: apigateway.Period.DAY
      }
    });

    usagePlan.addApiStage({
      stage: this.api.deploymentStage
    });

    // CloudWatch Dashboard for monitoring
    const dashboard = new cloudwatch.Dashboard(this, 'MonitoringDashboard', {
      dashboardName: `stock-analysis-${environment}`
    });

    // SNS Topics for Alerts (production only)
    if (environment === 'production') {
      // General alerts topic
      this.alertTopic = new sns.Topic(this, 'AlertTopic', {
        topicName: `stock-analysis-alerts-${environment}`,
        displayName: 'Stock Analysis Alerts'
      });

      // Critical alerts topic
      this.criticalAlertTopic = new sns.Topic(this, 'CriticalAlertTopic', {
        topicName: `stock-analysis-critical-alerts-${environment}`,
        displayName: 'Stock Analysis Critical Alerts'
      });

      // Email subscriptions if provided
      if (alertEmail) {
        this.alertTopic.addSubscription(
          new snsSubscriptions.EmailSubscription(alertEmail)
        );
        this.criticalAlertTopic.addSubscription(
          new snsSubscriptions.EmailSubscription(alertEmail)
        );
      }

      // Slack webhook subscription if provided
      if (slackWebhookUrl) {
        // Create Lambda function for Slack notifications
        const slackNotificationFunction = new lambda.Function(this, 'SlackNotificationFunction', {
          functionName: `stock-analysis-slack-notifications-${environment}`,
          runtime: lambda.Runtime.PYTHON_3_11,
          handler: 'index.lambda_handler',
          code: lambda.Code.fromInline(`
import json
import urllib3
import os

def lambda_handler(event, context):
    webhook_url = os.environ['SLACK_WEBHOOK_URL']
    
    for record in event['Records']:
        message = json.loads(record['Sns']['Message'])
        
        # Determine color based on alarm state
        color = 'danger' if message.get('NewStateValue') == 'ALARM' else 'good'
        
        # Create Slack message
        slack_message = {
            'attachments': [{
                'color': color,
                'title': f"🚨 {message.get('AlarmName', 'Unknown Alarm')}",
                'text': message.get('AlarmDescription', 'No description'),
                'fields': [
                    {
                        'title': 'State',
                        'value': message.get('NewStateValue', 'Unknown'),
                        'short': True
                    },
                    {
                        'title': 'Reason',
                        'value': message.get('NewStateReason', 'No reason provided'),
                        'short': True
                    },
                    {
                        'title': 'Timestamp',
                        'value': message.get('StateChangeTime', 'Unknown'),
                        'short': True
                    }
                ]
            }]
        }
        
        # Send to Slack
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(slack_message),
            headers={'Content-Type': 'application/json'}
        )
        
        print(f"Slack notification sent: {response.status}")
    
    return {'statusCode': 200}
          `),
          environment: {
            'SLACK_WEBHOOK_URL': slackWebhookUrl
          },
          timeout: cdk.Duration.seconds(30)
        });

        // Subscribe Lambda to SNS topics
        this.alertTopic.addSubscription(
          new snsSubscriptions.LambdaSubscription(slackNotificationFunction)
        );
        this.criticalAlertTopic.addSubscription(
          new snsSubscriptions.LambdaSubscription(slackNotificationFunction)
        );
      }
    } else {
      // Create dummy topics for non-production environments
      this.alertTopic = new sns.Topic(this, 'AlertTopic', {
        topicName: `stock-analysis-alerts-${environment}`
      });
      this.criticalAlertTopic = new sns.Topic(this, 'CriticalAlertTopic', {
        topicName: `stock-analysis-critical-alerts-${environment}`
      });
    }

    // API Gateway metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'API Gateway Requests',
        left: [
          this.api.metricCount(),
          this.api.metricLatency(),
          this.api.metricClientError(),
          this.api.metricServerError()
        ]
      })
    );

    // Lambda metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Function Metrics',
        left: [
          this.apiFunction.metricInvocations(),
          this.apiFunction.metricDuration(),
          this.apiFunction.metricErrors(),
          this.apiFunction.metricThrottles()
        ]
      })
    );

    // DynamoDB metrics
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'DynamoDB Metrics',
        left: [
          this.table.metricConsumedReadCapacityUnits(),
          this.table.metricConsumedWriteCapacityUnits(),
          this.table.metricThrottledRequests()
        ]
      })
    );

    // CloudWatch Alarms for critical metrics (production only)
    if (environment === 'production') {
      // API Gateway Alarms
      const apiErrorRateAlarm = new cloudwatch.Alarm(this, 'ApiErrorRateAlarm', {
        alarmName: `stock-analysis-api-error-rate-${environment}`,
        metric: this.api.metricServerError({
          statistic: 'Sum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 10,
        evaluationPeriods: 2,
        alarmDescription: 'API Gateway server error rate is too high',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      apiErrorRateAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      const apiLatencyAlarm = new cloudwatch.Alarm(this, 'ApiLatencyAlarm', {
        alarmName: `stock-analysis-api-latency-${environment}`,
        metric: this.api.metricLatency({
          statistic: 'Average',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 5000, // 5 seconds
        evaluationPeriods: 3,
        alarmDescription: 'API Gateway latency is too high',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      apiLatencyAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      const apiThrottleAlarm = new cloudwatch.Alarm(this, 'ApiThrottleAlarm', {
        alarmName: `stock-analysis-api-throttle-${environment}`,
        metric: new cloudwatch.Metric({
          namespace: 'AWS/ApiGateway',
          metricName: 'ThrottledRequests',
          dimensionsMap: {
            'ApiName': this.api.restApiName
          },
          statistic: 'Sum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 50,
        evaluationPeriods: 2,
        alarmDescription: 'API Gateway throttling requests',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      apiThrottleAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.criticalAlertTopic));

      // Lambda Function Alarms
      const lambdaErrorRateAlarm = new cloudwatch.Alarm(this, 'LambdaErrorRateAlarm', {
        alarmName: `stock-analysis-lambda-error-rate-${environment}`,
        metric: this.apiFunction.metricErrors({
          statistic: 'Sum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 5,
        evaluationPeriods: 2,
        alarmDescription: 'Lambda function error rate is too high',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      lambdaErrorRateAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      const lambdaDurationAlarm = new cloudwatch.Alarm(this, 'LambdaDurationAlarm', {
        alarmName: `stock-analysis-lambda-duration-${environment}`,
        metric: this.apiFunction.metricDuration({
          statistic: 'Average',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 25000, // 25 seconds
        evaluationPeriods: 3,
        alarmDescription: 'Lambda function duration is too high',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      lambdaDurationAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      const lambdaThrottleAlarm = new cloudwatch.Alarm(this, 'LambdaThrottleAlarm', {
        alarmName: `stock-analysis-lambda-throttle-${environment}`,
        metric: this.apiFunction.metricThrottles({
          statistic: 'Sum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 1,
        evaluationPeriods: 1,
        alarmDescription: 'Lambda function is being throttled',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      lambdaThrottleAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.criticalAlertTopic));

      const lambdaConcurrentExecutionsAlarm = new cloudwatch.Alarm(this, 'LambdaConcurrentExecutionsAlarm', {
        alarmName: `stock-analysis-lambda-concurrent-executions-${environment}`,
        metric: new cloudwatch.Metric({
          namespace: 'AWS/Lambda',
          metricName: 'ConcurrentExecutions',
          dimensionsMap: {
            'FunctionName': this.apiFunction.functionName
          },
          statistic: 'Maximum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 800, // 80% of default concurrent execution limit
        evaluationPeriods: 2,
        alarmDescription: 'Lambda concurrent executions approaching limit',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      lambdaConcurrentExecutionsAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      // DynamoDB Alarms
      const dynamoThrottleAlarm = new cloudwatch.Alarm(this, 'DynamoThrottleAlarm', {
        alarmName: `stock-analysis-dynamo-throttle-${environment}`,
        metric: this.table.metricThrottledRequests({
          statistic: 'Sum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 1,
        evaluationPeriods: 1,
        alarmDescription: 'DynamoDB requests are being throttled',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      dynamoThrottleAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.criticalAlertTopic));

      const dynamoErrorsAlarm = new cloudwatch.Alarm(this, 'DynamoErrorsAlarm', {
        alarmName: `stock-analysis-dynamo-errors-${environment}`,
        metric: new cloudwatch.Metric({
          namespace: 'AWS/DynamoDB',
          metricName: 'SystemErrors',
          dimensionsMap: {
            'TableName': this.table.tableName
          },
          statistic: 'Sum',
          period: cdk.Duration.minutes(5)
        }),
        threshold: 5,
        evaluationPeriods: 2,
        alarmDescription: 'DynamoDB system errors detected',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      dynamoErrorsAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      // Custom Business Logic Alarms
      const analysisFailureRateAlarm = new cloudwatch.Alarm(this, 'AnalysisFailureRateAlarm', {
        alarmName: `stock-analysis-failure-rate-${environment}`,
        metric: new cloudwatch.Metric({
          namespace: 'StockAnalysis/Business',
          metricName: 'AnalysisFailures',
          statistic: 'Sum',
          period: cdk.Duration.minutes(10)
        }),
        threshold: 10,
        evaluationPeriods: 2,
        alarmDescription: 'High rate of stock analysis failures',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      analysisFailureRateAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      const dataQualityAlarm = new cloudwatch.Alarm(this, 'DataQualityAlarm', {
        alarmName: `stock-analysis-data-quality-${environment}`,
        metric: new cloudwatch.Metric({
          namespace: 'StockAnalysis/DataQuality',
          metricName: 'LowQualityDataPercentage',
          statistic: 'Average',
          period: cdk.Duration.minutes(15)
        }),
        threshold: 20, // 20% of data is low quality
        evaluationPeriods: 2,
        alarmDescription: 'High percentage of low-quality data detected',
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING
      });
      dataQualityAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.alertTopic));

      // Composite Alarm for System Health
      const systemHealthAlarm = new cloudwatch.CompositeAlarm(this, 'SystemHealthAlarm', {
        compositeAlarmName: `stock-analysis-system-health-${environment}`,
        alarmDescription: 'Overall system health indicator',
        alarmRule: cloudwatch.AlarmRule.anyOf(
          cloudwatch.AlarmRule.fromAlarm(apiErrorRateAlarm, cloudwatch.AlarmState.ALARM),
          cloudwatch.AlarmRule.fromAlarm(lambdaErrorRateAlarm, cloudwatch.AlarmState.ALARM),
          cloudwatch.AlarmRule.fromAlarm(dynamoThrottleAlarm, cloudwatch.AlarmState.ALARM),
          cloudwatch.AlarmRule.fromAlarm(lambdaThrottleAlarm, cloudwatch.AlarmState.ALARM)
        )
      });
      systemHealthAlarm.addAlarmAction(new cloudwatchActions.SnsAction(this.criticalAlertTopic));
    }

    // Outputs
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: this.api.url,
      description: 'Stock Analysis API URL'
    });

    new cdk.CfnOutput(this, 'TableName', {
      value: this.table.tableName,
      description: 'DynamoDB table name'
    });

    new cdk.CfnOutput(this, 'SecretsArn', {
      value: apiSecrets.secretArn,
      description: 'Secrets Manager ARN'
    });

    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${dashboard.dashboardName}`,
      description: 'CloudWatch Dashboard URL'
    });

    if (environment === 'production') {
      new cdk.CfnOutput(this, 'AlertTopicArn', {
        value: this.alertTopic.topicArn,
        description: 'SNS Topic ARN for general alerts'
      });

      new cdk.CfnOutput(this, 'CriticalAlertTopicArn', {
        value: this.criticalAlertTopic.topicArn,
        description: 'SNS Topic ARN for critical alerts'
      });
    }
  }
}