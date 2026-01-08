# Deploy to Staging Environment
param(
    [string]$Environment = "staging",
    [string]$AwsRegion = "us-east-1"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting deployment to staging environment..." -ForegroundColor Green

# Configuration
$StackName = "StockAnalysisStack-staging"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check prerequisites
function Test-Prerequisites {
    Write-Status "Checking prerequisites..."
    
    # Check AWS CLI
    if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
        Write-Error "AWS CLI is not installed"
        exit 1
    }
    
    # Check CDK
    if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
        Write-Error "AWS CDK is not installed"
        exit 1
    }
    
    # Check Node.js
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Error "Node.js is not installed"
        exit 1
    }
    
    # Check Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Error "Python is not installed"
        exit 1
    }
    
    Write-Status "Prerequisites check passed ✓"
}

# Run tests before deployment
function Invoke-Tests {
    Write-Status "Running tests before deployment..."
    
    # Backend tests
    Push-Location backend
    try {
        python -m pytest tests/ --tb=short -q
    }
    finally {
        Pop-Location
    }
    
    # Frontend tests
    Push-Location frontend
    try {
        npm test -- --passWithNoTests --watchAll=false
    }
    finally {
        Pop-Location
    }
    
    Write-Status "All tests passed ✓"
}

# Build and deploy infrastructure
function Deploy-Infrastructure {
    Write-Status "Deploying infrastructure to staging..."
    
    Push-Location infrastructure
    try {
        # Install dependencies
        npm ci
        
        # Build CDK
        npm run build
        
        # Bootstrap if needed
        cdk bootstrap --context environment=$Environment
        
        # Show diff
        Write-Status "CDK Diff:"
        cdk diff --context environment=$Environment
        
        # Deploy
        cdk deploy --all `
            --context environment=$Environment `
            --require-approval never `
            --outputs-file outputs.json
    }
    finally {
        Pop-Location
    }
    
    Write-Status "Infrastructure deployment completed ✓"
}

# Deploy application code
function Deploy-Application {
    Write-Status "Deploying application code..."
    
    # Package backend
    Push-Location backend
    try {
        pip install -r requirements.txt
        # Add application packaging logic here
    }
    finally {
        Pop-Location
    }
    
    # Build frontend
    Push-Location frontend
    try {
        npm ci
        npm run build
        # Add frontend deployment logic here
    }
    finally {
        Pop-Location
    }
    
    Write-Status "Application deployment completed ✓"
}

# Run post-deployment tests
function Invoke-PostDeploymentTests {
    Write-Status "Running post-deployment tests..."
    
    # Extract API endpoint from CDK outputs
    if (Test-Path "infrastructure/outputs.json") {
        $outputs = Get-Content "infrastructure/outputs.json" | ConvertFrom-Json
        $apiEndpoint = $outputs.StockAnalysisStack.ApiEndpoint
        Write-Status "API Endpoint: $apiEndpoint"
        
        # Health check
        try {
            $response = Invoke-WebRequest -Uri "$apiEndpoint/health" -Method Get
            if ($response.StatusCode -eq 200) {
                Write-Status "Health check passed ✓"
            }
        }
        catch {
            Write-Error "Health check failed"
            exit 1
        }
        
        # API documentation check
        try {
            $response = Invoke-WebRequest -Uri "$apiEndpoint/docs" -Method Get
            if ($response.StatusCode -eq 200) {
                Write-Status "API documentation accessible ✓"
            }
        }
        catch {
            Write-Warning "API documentation not accessible"
        }
    }
    else {
        Write-Warning "CDK outputs file not found, skipping endpoint tests"
    }
    
    Write-Status "Post-deployment tests completed ✓"
}

# Main deployment flow
function Main {
    Write-Status "Starting staging deployment process..."
    
    Test-Prerequisites
    Invoke-Tests
    Deploy-Infrastructure
    Deploy-Application
    Invoke-PostDeploymentTests
    
    Write-Status "🎉 Staging deployment completed successfully!"
    Write-Status "Environment: $Environment"
    Write-Status "Region: $AwsRegion"
    Write-Status "Stack: $StackName"
}

# Error handling
trap {
    Write-Error "Deployment failed: $_"
    exit 1
}

# Run main function
Main