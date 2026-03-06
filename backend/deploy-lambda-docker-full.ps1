# Full container deployment: build image, create Image-type Lambda, wire API Gateway.
# Run from backend/ directory. Requires Docker installed and running.

param(
    [string]$Profile = "Cerebrum",
    [string]$Region = "eu-west-1",
    [string]$RepositoryName = "stock-analysis-api",
    [string]$NewFunctionName = "stock-analysis-api-container",
    [string]$ExistingFunctionName = "stock-analysis-api-production",
    [string]$ApiId = "dx0w31lbc1",
    [string]$StageName = "production"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Stock Analysis API - Container deployment ===" -ForegroundColor Green
Write-Host ""

# 1. Require Docker (try PATH, then common Docker Desktop locations)
Write-Host "Checking for Docker..." -ForegroundColor Cyan
$dockerExe = $null
if (Get-Command docker -ErrorAction SilentlyContinue) {
    $dockerExe = "docker"
}
if (-not $dockerExe) {
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin\docker.exe",
        "$env:LOCALAPPDATA\Docker\wsl\docker.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { $dockerExe = $p; break }
    }
}
if (-not $dockerExe) {
    Write-Host "Docker is not available." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Docker Desktop for Windows:" -ForegroundColor Yellow
    Write-Host "  https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor White
    Write-Host "After installing, start Docker Desktop and run this script again." -ForegroundColor Yellow
    exit 1
}
& $dockerExe info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker is not running or not responsive." -ForegroundColor Red
    Write-Host "Start Docker Desktop and run this script again." -ForegroundColor Yellow
    exit 1
}
# Ensure Docker Desktop bin is on PATH so docker-credential-desktop is found
if ($dockerExe -like "*\*") {
    $dockerBin = Split-Path -Parent $dockerExe
    if ($env:Path -notlike "*$dockerBin*") { $env:Path = "$dockerBin;$env:Path" }
}
Write-Host "Docker is available." -ForegroundColor Green
Write-Host ""

# 2. AWS account and ECR
Write-Host "Getting AWS account ID..." -ForegroundColor Cyan
$accountId = aws sts get-caller-identity --profile $Profile --region $Region --query Account --output text
if (-not $accountId) {
    Write-Host "Failed to get AWS account ID. Check profile '$Profile' and region '$Region'." -ForegroundColor Red
    exit 1
}
Write-Host "Account ID: $accountId" -ForegroundColor Green

$ecrUri = "$accountId.dkr.ecr.$Region.amazonaws.com/$RepositoryName"
$imageTag = "latest"
$imageUri = "$ecrUri`:$imageTag"
Write-Host "ECR URI: $ecrUri" -ForegroundColor Cyan
Write-Host ""

# 3. ECR repository
Write-Host "Ensuring ECR repository exists..." -ForegroundColor Cyan
$repoExists = aws ecr describe-repositories --repository-names $RepositoryName --profile $Profile --region $Region 2>$null
if (-not $repoExists) {
    aws ecr create-repository `
        --repository-name $RepositoryName `
        --profile $Profile `
        --region $Region `
        --image-scanning-configuration scanOnPush=true `
        --image-tag-mutability MUTABLE | Out-Null
    Write-Host "Repository created." -ForegroundColor Green
} else {
    Write-Host "Repository exists." -ForegroundColor Green
}

# 4. ECR login
Write-Host "Logging in to ECR..." -ForegroundColor Cyan
aws ecr get-login-password --profile $Profile --region $Region | & $dockerExe login --username AWS --password-stdin ($ecrUri -replace '/.*','') 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ECR login failed." -ForegroundColor Red
    exit 1
}
Write-Host "Logged in." -ForegroundColor Green
Write-Host ""

# 5. Build and push image
Write-Host "Building Docker image (this can take several minutes)..." -ForegroundColor Cyan
& $dockerExe build --platform linux/amd64 --provenance=false --sbom=false -f Dockerfile.lambda -t "${RepositoryName}:$imageTag" .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed." -ForegroundColor Red
    exit 1
}
Write-Host "Image built." -ForegroundColor Green

Write-Host "Tagging for ECR..." -ForegroundColor Cyan
& $dockerExe tag "${RepositoryName}:$imageTag" $imageUri
Write-Host "Pushing to ECR..." -ForegroundColor Cyan
& $dockerExe push $imageUri
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker push failed." -ForegroundColor Red
    exit 1
}
Write-Host "Image pushed." -ForegroundColor Green
Write-Host ""

# 6. Get existing Lambda config (role, timeout, memory, env)
Write-Host "Reading existing Lambda config..." -ForegroundColor Cyan
$config = aws lambda get-function --function-name $ExistingFunctionName --profile $Profile --region $Region --output json 2>$null | ConvertFrom-Json
if (-not $config) {
    Write-Host "Could not get config for $ExistingFunctionName. Using defaults." -ForegroundColor Yellow
    $roleArn = "arn:aws:iam::${accountId}:role/StockAnalysisInfrastructu-LambdaExecutionRoleD5C260-kW9wvngtVo2R"
    $timeout = 900
    $memorySize = 3008
    $envVars = 'Variables={ENVIRONMENT=production,MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6}'
} else {
    $roleArn = $config.Configuration.Role
    $timeout = $config.Configuration.Timeout
    $memorySize = $config.Configuration.MemorySize
    $envObj = $config.Configuration.Environment
    if ($envObj -and $envObj.Variables) {
        $vars = $envObj.Variables | Get-Member -MemberType NoteProperty | ForEach-Object { "$($_.Name)=$($envObj.Variables.($_.Name))" }
        $envVars = 'Variables={' + ($vars -join ',') + '}'
    } else {
        $envVars = 'Variables={ENVIRONMENT=production,MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6}'
    }
}
Write-Host "Role: $roleArn" -ForegroundColor Gray
Write-Host ""

# 7. Create new Lambda (PackageType Image) if it doesn't exist
$newFuncExists = $null
try {
    $newFuncExists = aws lambda get-function --function-name $NewFunctionName --profile $Profile --region $Region 2>$null
} catch { }
if (-not $newFuncExists) {
    Write-Host "Creating Lambda function (Image): $NewFunctionName ..." -ForegroundColor Cyan
    aws lambda create-function `
        --function-name $NewFunctionName `
        --package-type Image `
        --code ImageUri=$imageUri `
        --role $roleArn `
        --timeout $timeout `
        --memory-size $memorySize `
        --environment $envVars `
        --profile $Profile `
        --region $Region | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Create function failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "Function created." -ForegroundColor Green
} else {
    Write-Host "Updating Lambda function code: $NewFunctionName ..." -ForegroundColor Cyan
    aws lambda update-function-code `
        --function-name $NewFunctionName `
        --image-uri $imageUri `
        --profile $Profile `
        --region $Region | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Update function code failed." -ForegroundColor Red
        exit 1
    }
    Write-Host "Function code updated." -ForegroundColor Green
}

Write-Host "Waiting for Lambda to be active..." -ForegroundColor Gray
Start-Sleep -Seconds 15
Write-Host ""

# 8. Allow API Gateway to invoke the new Lambda (idempotent: skip if already exists)
$apiArn = "arn:aws:execute-api:${Region}:${accountId}:${ApiId}/*"
Write-Host "Adding API Gateway invoke permission..." -ForegroundColor Cyan
try {
    $addPermResult = aws lambda add-permission `
        --function-name $NewFunctionName `
        --statement-id "apigateway-invoke-$ApiId" `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --source-arn $apiArn `
        --profile $Profile `
        --region $Region 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Permission may already exist (continuing)." -ForegroundColor Gray
    }
} catch {
    Write-Host "Permission step skipped (likely already exists): $($_.Exception.Message)" -ForegroundColor Gray
}
Write-Host ""

# 9. Update API Gateway integrations to use the new Lambda
$newLambdaArn = "arn:aws:lambda:${Region}:${accountId}:function:${NewFunctionName}"
$newIntegrationUri = "arn:aws:apigateway:${Region}:lambda:path/2015-03-31/functions/${newLambdaArn}/invocations"

Write-Host "Updating API Gateway integrations to $NewFunctionName ..." -ForegroundColor Cyan
$resources = aws apigateway get-resources --rest-api-id $ApiId --profile $Profile --region $Region --output json | ConvertFrom-Json
foreach ($res in $resources.items) {
    $rid = $res.id
    $path = $res.path
    if (-not $res.resourceMethods) { continue }
    $methods = $res.resourceMethods | Get-Member -MemberType NoteProperty | Select-Object -ExpandProperty Name
    foreach ($method in $methods) {
        if ($method -eq "OPTIONS") { continue }
        try {
            $int = aws apigateway get-integration --rest-api-id $ApiId --resource-id $rid --http-method $method --profile $Profile --region $Region --output json 2>$null | ConvertFrom-Json
            $isLambda = $int -and $int.type -eq 'AWS_PROXY' -and $int.uri -like '*lambda*invocations'
            if ($isLambda -and $int.uri -notlike "*$NewFunctionName*") {
                aws apigateway put-integration `
                        --rest-api-id $ApiId `
                        --resource-id $rid `
                        --http-method $method `
                        --type AWS_PROXY `
                        --integration-http-method POST `
                        --uri $newIntegrationUri `
                        --profile $Profile `
                        --region $Region | Out-Null
                Write-Host "  $method $path -> $NewFunctionName" -ForegroundColor Gray
            }
        } catch {
            Write-Host "  Skip $method $path : $($_.Exception.Message)" -ForegroundColor Gray
        }
    }
}
Write-Host "Integrations updated." -ForegroundColor Green
Write-Host ""

# 10. Deploy API stage
Write-Host "Deploying API stage '$StageName'..." -ForegroundColor Cyan
aws apigateway create-deployment `
    --rest-api-id $ApiId `
    --stage-name $StageName `
    --description "Container Lambda deployment" `
    --profile $Profile `
    --region $Region | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Deployment failed." -ForegroundColor Red
    exit 1
}
Write-Host "Stage deployed." -ForegroundColor Green
Write-Host ""

# 11. Test
$apiUrl = "https://${ApiId}.execute-api.${Region}.amazonaws.com/${StageName}/health"
Write-Host "Testing: $apiUrl" -ForegroundColor Cyan
Start-Sleep -Seconds 5
try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 60
    Write-Host "[SUCCESS] Health check passed." -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 2 -Compress) -ForegroundColor Cyan
} catch {
    Write-Host "[WARNING] Health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Cold start may take 10-30 seconds. Try again or check logs." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "API: https://${ApiId}.execute-api.${Region}.amazonaws.com/${StageName}/" -ForegroundColor Cyan
Write-Host "Explore: https://${ApiId}.execute-api.${Region}.amazonaws.com/${StageName}/api/explore/markets" -ForegroundColor Cyan
Write-Host "Lambda: $NewFunctionName (container image)" -ForegroundColor Cyan
