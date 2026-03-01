# Grant Gateway Lambda Permission to Invoke Other Lambdas
$ErrorActionPreference = "Stop"
$env:AWS_PROFILE = "Cerebrum"
$env:AWS_DEFAULT_REGION = "eu-west-1"

$gatewayLambda = "stock-analysis-gateway"
$roleArn = "arn:aws:iam::295202642810:role/StockAnalysisInfrastructu-LambdaExecutionRoleD5C260-kW9wvngtVo2R"
$accountId = "295202642810"
$region = "eu-west-1"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Granting Lambda Invoke Permissions" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# List of Lambda functions that the gateway needs to invoke
$targetLambdas = @(
    "stock-analysis-auth",
    "stock-analysis-analyzer",
    "stock-analysis-pdf-processor",
    "stock-analysis-stock-data"
)

# Create IAM policy document
$policyDocument = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Action = "lambda:InvokeFunction"
            Resource = @()
        }
    )
} 

# Add each Lambda ARN to the policy
foreach ($lambda in $targetLambdas) {
    $arn = "arn:aws:lambda:${region}:${accountId}:function:${lambda}"
    $policyDocument.Statement[0].Resource += $arn
}

# Convert to JSON and save properly
$policyJsonString = $policyDocument | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText("lambda-invoke-policy.json", $policyJsonString)

Write-Host "Policy Document:" -ForegroundColor Yellow
Write-Host $policyJsonString -ForegroundColor Gray
Write-Host ""

# Extract role name from ARN
$roleName = $roleArn -replace '.*role/', ''

Write-Host "Attaching inline policy to role: $roleName" -ForegroundColor Yellow

# Put inline policy on the role
aws iam put-role-policy `
    --role-name $roleName `
    --policy-name "LambdaInvokePolicy" `
    --policy-document file://lambda-invoke-policy.json

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
Write-Host "The gateway Lambda can now invoke:" -ForegroundColor Cyan
foreach ($lambda in $targetLambdas) {
    Write-Host "  - $lambda" -ForegroundColor White
}

# Clean up
Remove-Item lambda-invoke-policy.json -ErrorAction SilentlyContinue
