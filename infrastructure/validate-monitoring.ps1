# PowerShell script to validate production monitoring setup

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [switch]$TestAlerts = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Validating monitoring setup for $Environment environment..." -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan

# Check AWS CLI configuration
try {
    $callerIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS CLI configured for account: $($callerIdentity.Account)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

$region = "eu-west-1"

# 1. Validate SNS Topics
Write-Host ""
Write-Host "📧 Checking SNS Topics..." -ForegroundColor Yellow

$expectedTopics = @(
    "stock-analysis-alerts-$Environment",
    "stock-analysis-critical-alerts-$Environment"
)

foreach ($topicName in $expectedTopics) {
    try {
        $topics = aws sns list-topics --region $region --output json | ConvertFrom-Json
        $topicExists = $topics.Topics | Where-Object { $_.TopicArn -like "*$topicName*" }
        
        if ($topicExists) {
            Write-Host "✅ SNS Topic found: $topicName" -ForegroundColor Green
            
            # Check subscriptions
            $subscriptions = aws sns list-subscriptions-by-topic --topic-arn $topicExists.TopicArn --region $region --output json | ConvertFrom-Json
            $subCount = $subscriptions.Subscriptions.Count
            Write-Host "   📬 Subscriptions: $subCount" -ForegroundColor White
            
            foreach ($sub in $subscriptions.Subscriptions) {
                Write-Host "   - $($sub.Protocol): $($sub.Endpoint)" -ForegroundColor Gray
            }
        } else {
            Write-Host "❌ SNS Topic not found: $topicName" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Error checking SNS topic $topicName`: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 2. Validate CloudWatch Alarms
Write-Host ""
Write-Host "⏰ Checking CloudWatch Alarms..." -ForegroundColor Yellow

$expectedAlarms = @(
    "stock-analysis-api-error-rate-$Environment",
    "stock-analysis-api-latency-$Environment",
    "stock-analysis-api-throttle-$Environment",
    "stock-analysis-lambda-error-rate-$Environment",
    "stock-analysis-lambda-duration-$Environment",
    "stock-analysis-lambda-throttle-$Environment",
    "stock-analysis-lambda-concurrent-executions-$Environment",
    "stock-analysis-dynamo-throttle-$Environment",
    "stock-analysis-dynamo-errors-$Environment",
    "stock-analysis-analysis-failure-rate-$Environment",
    "stock-analysis-data-quality-$Environment",
    "stock-analysis-system-health-$Environment"
)

$alarmCount = 0
foreach ($alarmName in $expectedAlarms) {
    try {
        $alarm = aws cloudwatch describe-alarms --alarm-names $alarmName --region $region --output json | ConvertFrom-Json
        
        if ($alarm.MetricAlarms.Count -gt 0 -or $alarm.CompositeAlarms.Count -gt 0) {
            $alarmCount++
            $alarmData = if ($alarm.MetricAlarms.Count -gt 0) { $alarm.MetricAlarms[0] } else { $alarm.CompositeAlarms[0] }
            $state = $alarmData.StateValue
            $stateColor = switch ($state) {
                "OK" { "Green" }
                "ALARM" { "Red" }
                "INSUFFICIENT_DATA" { "Yellow" }
                default { "Gray" }
            }
            Write-Host "✅ Alarm found: $alarmName [$state]" -ForegroundColor $stateColor
            
            # Check if alarm has actions
            $actionCount = $alarmData.AlarmActions.Count
            if ($actionCount -gt 0) {
                Write-Host "   📢 Actions configured: $actionCount" -ForegroundColor White
            } else {
                Write-Host "   ⚠️  No actions configured" -ForegroundColor Yellow
            }
        } else {
            Write-Host "❌ Alarm not found: $alarmName" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Error checking alarm $alarmName`: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "📊 Total alarms found: $alarmCount/$($expectedAlarms.Count)" -ForegroundColor Cyan

# 3. Validate CloudWatch Dashboard
Write-Host ""
Write-Host "📈 Checking CloudWatch Dashboard..." -ForegroundColor Yellow

$dashboardName = "stock-analysis-$Environment"
try {
    $dashboard = aws cloudwatch get-dashboard --dashboard-name $dashboardName --region $region --output json | ConvertFrom-Json
    
    if ($dashboard) {
        Write-Host "✅ Dashboard found: $dashboardName" -ForegroundColor Green
        
        # Parse dashboard body to count widgets
        $dashboardBody = $dashboard.DashboardBody | ConvertFrom-Json
        $widgetCount = $dashboardBody.widgets.Count
        Write-Host "   📊 Widgets: $widgetCount" -ForegroundColor White
        
        $dashboardUrl = "https://console.aws.amazon.com/cloudwatch/home?region=$region#dashboards:name=$dashboardName"
        Write-Host "   🔗 URL: $dashboardUrl" -ForegroundColor Gray
    } else {
        Write-Host "❌ Dashboard not found: $dashboardName" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error checking dashboard: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Check Lambda Functions (for Slack notifications)
Write-Host ""
Write-Host "⚡ Checking Lambda Functions..." -ForegroundColor Yellow

$slackFunctionName = "stock-analysis-slack-notifications-$Environment"
try {
    $function = aws lambda get-function --function-name $slackFunctionName --region $region --output json 2>$null | ConvertFrom-Json
    
    if ($function) {
        Write-Host "✅ Slack notification function found: $slackFunctionName" -ForegroundColor Green
        Write-Host "   📦 Runtime: $($function.Configuration.Runtime)" -ForegroundColor White
        Write-Host "   ⏱️  Timeout: $($function.Configuration.Timeout)s" -ForegroundColor White
        
        # Check environment variables
        if ($function.Configuration.Environment.Variables.SLACK_WEBHOOK_URL) {
            Write-Host "   🔗 Slack webhook configured" -ForegroundColor Green
        } else {
            Write-Host "   ⚠️  Slack webhook not configured" -ForegroundColor Yellow
        }
    } else {
        Write-Host "ℹ️  Slack notification function not found (optional)" -ForegroundColor Gray
    }
} catch {
    Write-Host "ℹ️  Slack notification function not found (optional)" -ForegroundColor Gray
}

# 5. Test Alerts (if requested)
if ($TestAlerts) {
    Write-Host ""
    Write-Host "🧪 Testing Alert Notifications..." -ForegroundColor Yellow
    
    # Get SNS topic ARNs
    $topics = aws sns list-topics --region $region --output json | ConvertFrom-Json
    $alertTopic = $topics.Topics | Where-Object { $_.TopicArn -like "*stock-analysis-alerts-$Environment*" }
    $criticalTopic = $topics.Topics | Where-Object { $_.TopicArn -like "*stock-analysis-critical-alerts-$Environment*" }
    
    if ($alertTopic) {
        Write-Host "📧 Sending test alert to general topic..." -ForegroundColor Yellow
        $testMessage = @{
            AlarmName = "TEST-ALERT"
            AlarmDescription = "This is a test alert from the monitoring validation script"
            NewStateValue = "ALARM"
            NewStateReason = "Testing alert notifications"
            StateChangeTime = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        } | ConvertTo-Json
        
        aws sns publish --topic-arn $alertTopic.TopicArn --message $testMessage --region $region
        Write-Host "✅ Test alert sent to general topic" -ForegroundColor Green
    }
    
    if ($criticalTopic) {
        Write-Host "🚨 Sending test alert to critical topic..." -ForegroundColor Yellow
        $testMessage = @{
            AlarmName = "TEST-CRITICAL-ALERT"
            AlarmDescription = "This is a test critical alert from the monitoring validation script"
            NewStateValue = "ALARM"
            NewStateReason = "Testing critical alert notifications"
            StateChangeTime = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        } | ConvertTo-Json
        
        aws sns publish --topic-arn $criticalTopic.TopicArn --message $testMessage --region $region
        Write-Host "✅ Test alert sent to critical topic" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "📬 Check your email and Slack for test notifications!" -ForegroundColor Cyan
}

# 6. Summary
Write-Host ""
Write-Host "📋 Validation Summary" -ForegroundColor Cyan
Write-Host "===================" -ForegroundColor Cyan

$validationResults = @{
    "SNS Topics" = $expectedTopics.Count
    "CloudWatch Alarms" = $alarmCount
    "Dashboard" = if ($dashboard) { 1 } else { 0 }
    "Slack Function" = if ($function) { 1 } else { 0 }
}

foreach ($item in $validationResults.GetEnumerator()) {
    $status = if ($item.Value -gt 0) { "✅" } else { "❌" }
    Write-Host "$status $($item.Key): $($item.Value)" -ForegroundColor White
}

Write-Host ""
if ($alarmCount -eq $expectedAlarms.Count) {
    Write-Host "🎉 All monitoring components are properly configured!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some monitoring components may need attention." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📚 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Review the incident response runbook: infrastructure/INCIDENT_RESPONSE_RUNBOOK.md" -ForegroundColor White
Write-Host "2. Set up on-call rotation and escalation procedures" -ForegroundColor White
Write-Host "3. Configure additional notification channels if needed" -ForegroundColor White
Write-Host "4. Schedule regular monitoring reviews and updates" -ForegroundColor White

if (-not $TestAlerts) {
    Write-Host ""
    Write-Host "💡 Tip: Run with -TestAlerts to send test notifications" -ForegroundColor Cyan
}