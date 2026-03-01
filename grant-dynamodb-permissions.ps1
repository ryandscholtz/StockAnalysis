# Grant DynamoDB Permissions to Lambda Execution Role
$ErrorActionPreference = "Stop"
$env:AWS_PROFILE = "Cerebrum"
$env:AWS_DEFAULT_REGION = "eu-west-1"

$roleArn = "arn:aws:iam::295202642810:role/StockAnalysisInfrastructu-LambdaExecutionRoleD5C260-kW9wvngtVo2R"
$accountId = "295202642810"
$region = "eu-west-1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Granting DynamoDB Permissions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create IAM policy document for DynamoDB access
$policyDocument = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Action = @(
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            )
            Resource = @(
                "arn:aws:dynamodb:${region}:${accountId}:table/stock-analysis-watchlist",
                "arn:aws:dynamodb:${region}:${accountId}:table/stock-analysis-watchlist/*",
                "arn:aws:dynamodb:${region}:${accountId}:table/stock-analyses",
                "arn:aws:dynamodb:${region}:${accountId}:table/stock-analyses/*"
            )
        }
    )
}

# Convert to JSON and save
$policyJsonString = $policyDocument | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText("dynamodb-policy.json", $policyJsonString)

Write-Host "Policy Document:" -ForegroundColor Yellow
Write-Host $policyJsonString -ForegroundColor Gray
Write-Host ""

# Extract role name from ARN
$roleName = $roleArn -replace '.*role/', ''

Write-Host "Attaching inline policy to role: $roleName" -ForegroundColor Yellow

# Put inline policy on the role
aws iam put-role-policy `
    --role-name $roleName `
    --policy-name "DynamoDBAccessPolicy" `
    --policy-document file://dynamodb-policy.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Policy attached successfully!" -ForegroundColor Green
} else {
    Write-Host "  Failed to attach policy!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Permissions Granted!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Lambda functions can now access DynamoDB tables:" -ForegroundColor Cyan
Write-Host "  - stock-analysis-watchlist" -ForegroundColor White
Write-Host "  - stock-analyses" -ForegroundColor White

# Clean up
Remove-Item dynamodb-policy.json -ErrorAction SilentlyContinue
