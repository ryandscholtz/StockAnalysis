#!/usr/bin/env pwsh

Write-Host "Testing PR Checks locally..." -ForegroundColor Green

$allPassed = $true

# Quick Tests - Backend
Write-Host "`n=== Quick Backend Tests ===" -ForegroundColor Yellow
Set-Location backend
$backendResult = python -m pytest test_basic.py test_simple_endpoint.py test_endpoints.py test_simple_batch.py --tb=short -q --disable-warnings
$backendExitCode = $LASTEXITCODE
Set-Location ..

if ($backendExitCode -eq 0) {
    Write-Host "✅ Quick backend tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Quick backend tests failed" -ForegroundColor Red
    $allPassed = $false
}

# Quick Tests - Frontend
Write-Host "`n=== Quick Frontend Tests ===" -ForegroundColor Yellow
Set-Location frontend
$frontendResult = npm test -- __tests__/basic.test.ts --passWithNoTests --watchAll=false
$frontendExitCode = $LASTEXITCODE

if ($frontendExitCode -eq 0) {
    Write-Host "✅ Quick frontend tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Quick frontend tests failed" -ForegroundColor Red
    $allPassed = $false
}

# Bundle Size Check
Write-Host "`n=== Bundle Size Check ===" -ForegroundColor Yellow
$buildResult = npm run build
$buildExitCode = $LASTEXITCODE

if ($buildExitCode -eq 0) {
    Write-Host "✅ Frontend build successful" -ForegroundColor Green
    
    # Bundle size analysis
    Write-Host "=== Bundle Size Analysis ===" -ForegroundColor Cyan
    
    if (Test-Path ".next/static") {
        $staticSize = (Get-ChildItem -Path ".next/static" -Recurse | Measure-Object -Property Length -Sum).Sum
        $staticSizeMB = [math]::Round($staticSize / 1MB, 2)
        Write-Host "Static assets size: $staticSizeMB MB" -ForegroundColor White
    }
    
    if (Test-Path ".next/server") {
        $serverSize = (Get-ChildItem -Path ".next/server" -Recurse -Exclude "*.cache*" | Measure-Object -Property Length -Sum).Sum
        $serverSizeMB = [math]::Round($serverSize / 1MB, 2)
        Write-Host "Server bundle size: $serverSizeMB MB" -ForegroundColor White
    }
    
    if (Test-Path ".next/static/chunks") {
        Write-Host "JavaScript chunks:" -ForegroundColor White
        Get-ChildItem -Path ".next/static/chunks" -Filter "*.js" | 
            Sort-Object Length -Descending | 
            Select-Object -First 5 | 
            ForEach-Object { 
                $sizeKB = [math]::Round($_.Length / 1KB, 1)
                Write-Host "  $sizeKB KB - $($_.Name)" -ForegroundColor Gray
            }
    }
    
    Write-Host "✅ Bundle size analysis completed" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend build failed" -ForegroundColor Red
    $allPassed = $false
}

Set-Location ..

# Code Formatting Check
Write-Host "`n=== Code Formatting Check ===" -ForegroundColor Yellow
Write-Host "Checking backend formatting..." -ForegroundColor White
Set-Location backend
try {
    $blackCheck = black --check app tests 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Backend formatting OK" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Backend formatting issues found" -ForegroundColor Yellow
        # Don't fail the build for formatting issues in PR checks
    }
} catch {
    Write-Host "⚠️  Black not installed - skipping backend formatting check" -ForegroundColor Yellow
}

Set-Location ../frontend
Write-Host "Checking frontend formatting..." -ForegroundColor White
try {
    $prettierCheck = npx prettier --check "**/*.{js,jsx,ts,tsx,json,css,md}" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Frontend formatting OK" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Frontend formatting issues found" -ForegroundColor Yellow
        # Don't fail the build for formatting issues in PR checks
    }
} catch {
    Write-Host "⚠️  Prettier not available - skipping frontend formatting check" -ForegroundColor Yellow
}

Set-Location ..

# Summary
Write-Host "`n=== PR Checks Summary ===" -ForegroundColor Cyan
if ($backendExitCode -eq 0) {
    Write-Host "Quick Backend Tests: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Quick Backend Tests: ❌ FAILED" -ForegroundColor Red
}

if ($frontendExitCode -eq 0) {
    Write-Host "Quick Frontend Tests: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Quick Frontend Tests: ❌ FAILED" -ForegroundColor Red
}

if ($buildExitCode -eq 0) {
    Write-Host "Bundle Size Check: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Bundle Size Check: ❌ FAILED" -ForegroundColor Red
}

Write-Host "Code Formatting: ⚠️  CHECKED (warnings only)" -ForegroundColor Yellow

if ($allPassed) {
    Write-Host "`n🎉 All PR checks would PASS!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n💥 Some PR checks would FAIL" -ForegroundColor Red
    exit 1
}