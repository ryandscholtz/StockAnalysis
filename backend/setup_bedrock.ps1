# AWS Bedrock Setup Script
Write-Host "AWS Bedrock Setup for Stock Analysis Tool" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check AWS CLI
Write-Host "Checking AWS CLI..." -ForegroundColor Yellow
$awsVersion = aws --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "AWS CLI not found. Install from: https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}
Write-Host "AWS CLI found" -ForegroundColor Green

# Check for AWS profiles
Write-Host ""
Write-Host "Checking AWS profiles..." -ForegroundColor Yellow
$profiles = @()
if (Test-Path "$env:USERPROFILE\.aws\credentials") {
    $credContent = Get-Content "$env:USERPROFILE\.aws\credentials"
    foreach ($line in $credContent) {
        if ($line -match "^\[(.+)\]$") {
            $profiles += $matches[1]
        }
    }
}

if ($profiles.Count -gt 0) {
    Write-Host "Found profiles: $($profiles -join ', ')" -ForegroundColor Green
    
    # Test each profile
    $workingProfile = $null
    $workingRegion = $null
    foreach ($profile in $profiles) {
        $identity = aws sts get-caller-identity --profile $profile 2>&1
        if ($LASTEXITCODE -eq 0) {
            $region = aws configure get region --profile $profile 2>&1
            if ($LASTEXITCODE -eq 0 -and $region) {
                $workingProfile = $profile
                $workingRegion = $region
                Write-Host "Using profile: $profile (region: $region)" -ForegroundColor Green
                break
            }
        }
    }
    
    if (-not $workingProfile) {
        Write-Host "No working profile found. Testing default..." -ForegroundColor Yellow
        $identity = aws sts get-caller-identity 2>&1
        if ($LASTEXITCODE -eq 0) {
            $region = aws configure get region 2>&1
            if ($LASTEXITCODE -eq 0 -and $region) {
                $workingRegion = $region
                Write-Host "Using default credentials (region: $region)" -ForegroundColor Green
            } else {
                $workingRegion = "us-east-1"
                Write-Host "No region configured, using default: us-east-1" -ForegroundColor Yellow
            }
        } else {
            Write-Host "AWS credentials not working. Run: aws configure" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "No profiles found. Testing default credentials..." -ForegroundColor Yellow
    $identity = aws sts get-caller-identity 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "AWS credentials not configured. Run: aws configure" -ForegroundColor Red
        exit 1
    }
    $region = aws configure get region 2>&1
    if ($LASTEXITCODE -eq 0 -and $region) {
        $workingRegion = $region
        Write-Host "Using default credentials (region: $region)" -ForegroundColor Green
    } else {
        $workingRegion = "us-east-1"
        Write-Host "No region configured, using default: us-east-1" -ForegroundColor Yellow
    }
}

$region = $workingRegion
$profile = $workingProfile

# Check Bedrock
Write-Host ""
Write-Host "Checking Bedrock model access..." -ForegroundColor Yellow
$modelId = "anthropic.claude-3-sonnet-20240229-v1:0"
$bedrockCmd = "aws bedrock list-foundation-models --region $region"
if ($profile) {
    $bedrockCmd += " --profile $profile"
}
$foundationModels = Invoke-Expression "$bedrockCmd --query `"modelSummaries[?modelId=='$modelId']`"" 2>&1
if ($LASTEXITCODE -eq 0 -and $foundationModels -and $foundationModels -ne "[]") {
    Write-Host "Model is available" -ForegroundColor Green
} else {
    Write-Host "Model access may need to be enabled in AWS Console" -ForegroundColor Yellow
}

# Update .env file
Write-Host ""
Write-Host "Updating .env file..." -ForegroundColor Yellow
$envPath = Join-Path $PSScriptRoot ".env"

$newLines = @()
if (Test-Path $envPath) {
    $lines = Get-Content $envPath
    $found = $false
    foreach ($line in $lines) {
        if ($line -match "^USE_AWS_BEDROCK=") {
            $newLines += "USE_AWS_BEDROCK=true"
            $found = $true
        } elseif ($line -match "^AWS_REGION=") {
            $newLines += "AWS_REGION=$region"
        } elseif ($line -match "^BEDROCK_MODEL_ID=") {
            $newLines += "BEDROCK_MODEL_ID=$modelId"
        } else {
            $newLines += $line
        }
    }
    if (-not $found) {
        $newLines += ""
        $newLines += "# AWS Bedrock Configuration"
        $newLines += "USE_AWS_BEDROCK=true"
        $newLines += "AWS_REGION=$region"
        $newLines += "BEDROCK_MODEL_ID=$modelId"
        if ($profile) {
            $newLines += "AWS_PROFILE=$profile"
        }
    } else {
        # Update existing AWS_PROFILE if profile was found
        $profileFound = $false
        for ($i = 0; $i -lt $newLines.Count; $i++) {
            if ($newLines[$i] -match "^AWS_PROFILE=") {
                if ($profile) {
                    $newLines[$i] = "AWS_PROFILE=$profile"
                }
                $profileFound = $true
                break
            }
        }
        if ($profile -and -not $profileFound) {
            # Add AWS_PROFILE after AWS_REGION
            for ($i = 0; $i -lt $newLines.Count; $i++) {
                if ($newLines[$i] -match "^AWS_REGION=") {
                    $newLines = $newLines[0..$i] + "AWS_PROFILE=$profile" + $newLines[($i+1)..($newLines.Count-1)]
                    break
                }
            }
        }
    }
    Set-Content -Path $envPath -Value ($newLines -join "`n")
} else {
    $content = "# AWS Bedrock Configuration for AI Business Type Detection`n"
    $content += "USE_AWS_BEDROCK=true`n"
    $content += "AWS_REGION=$region`n"
    $content += "BEDROCK_MODEL_ID=$modelId`n"
    if ($profile) {
        $content += "AWS_PROFILE=$profile`n"
    }
    $content += "`n# Alternative: OpenAI Configuration`n"
    $content += "# OPENAI_API_KEY=your-openai-api-key-here`n"
    Set-Content -Path $envPath -Value $content
}

Write-Host "Configuration updated in .env file" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Enable Bedrock model access in AWS Console if needed" -ForegroundColor White
Write-Host "2. Restart backend server" -ForegroundColor White
Write-Host "3. Test Auto-Assign button in Analysis Configuration" -ForegroundColor White
