# PowerShell script to deploy Stock Analysis Infrastructure
param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment = "development",
    
    [Parameter(Mandatory=$false)]
    [string]$DomainName = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$Destroy = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

Write-Host "Stock Analysis Infrastructure Deployment" -ForegroundColor Green
Write-Host "Environment: $Environment" -ForegroundColor Yellow

# Check if AWS CLI is installed
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI is not installed or not in PATH"
    exit 1
}

# Check if CDK is installed
if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CDK is not installed. Install with: npm install -g aws-cdk"
    exit 1
}

# Check AWS credentials
try {
    $awsIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "AWS Account: $($awsIdentity.Account)" -ForegroundColor Cyan
    Write-Host "AWS User/Role: $($awsIdentity.Arn)" -ForegroundColor Cyan
} catch {
    Write-Error "AWS credentials not configured. Run 'aws configure' first."
    exit 1
}

# Set CDK environment variables
$env:CDK_DEFAULT_ACCOUNT = $awsIdentity.Account
$env:CDK_DEFAULT_REGION = if ($env:AWS_DEFAULT_REGION) { $env:AWS_DEFAULT_REGION } else { "us-east-1" }

Write-Host "CDK Account: $env:CDK_DEFAULT_ACCOUNT" -ForegroundColor Cyan
Write-Host "CDK Region: $env:CDK_DEFAULT_REGION" -ForegroundColor Cyan

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to install dependencies"
    exit 1
}

# Bootstrap CDK (if needed)
Write-Host "Checking CDK bootstrap..." -ForegroundColor Yellow
$bootstrapCheck = cdk bootstrap --show-template 2>&1
if ($bootstrapCheck -match "not bootstrapped") {
    Write-Host "Bootstrapping CDK..." -ForegroundColor Yellow
    cdk bootstrap
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to bootstrap CDK"
        exit 1
    }
}

# Build the CDK app
Write-Host "Building CDK app..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to build CDK app"
    exit 1
}

# Prepare context parameters
$contextParams = @("--context", "environment=$Environment")
if ($DomainName) {
    $contextParams += @("--context", "domainName=$DomainName")
}

if ($Destroy) {
    # Destroy the stack
    Write-Host "Destroying infrastructure for environment: $Environment" -ForegroundColor Red
    Write-Host "This will delete all resources. Are you sure? (y/N)" -ForegroundColor Red
    $confirmation = Read-Host
    
    if ($confirmation -eq "y" -or $confirmation -eq "Y") {
        cdk destroy @contextParams --force
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Infrastructure destroyed successfully" -ForegroundColor Green
        } else {
            Write-Error "Failed to destroy infrastructure"
            exit 1
        }
    } else {
        Write-Host "Destruction cancelled" -ForegroundColor Yellow
    }
} elseif ($DryRun) {
    # Show what would be deployed
    Write-Host "Showing deployment plan (dry run)..." -ForegroundColor Yellow
    cdk diff @contextParams
} else {
    # Deploy the stack
    Write-Host "Deploying infrastructure for environment: $Environment" -ForegroundColor Yellow
    
    # Show diff first
    Write-Host "Showing changes to be deployed..." -ForegroundColor Cyan
    cdk diff @contextParams
    
    Write-Host "Proceed with deployment? (Y/n)" -ForegroundColor Yellow
    $confirmation = Read-Host
    
    if ($confirmation -eq "" -or $confirmation -eq "y" -or $confirmation -eq "Y") {
        cdk deploy @contextParams --require-approval never
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Infrastructure deployed successfully!" -ForegroundColor Green
            
            # Show outputs
            Write-Host "Stack Outputs:" -ForegroundColor Cyan
            cdk list @contextParams --long
        } else {
            Write-Error "Failed to deploy infrastructure"
            exit 1
        }
    } else {
        Write-Host "Deployment cancelled" -ForegroundColor Yellow
    }
}

Write-Host "Done!" -ForegroundColor Green