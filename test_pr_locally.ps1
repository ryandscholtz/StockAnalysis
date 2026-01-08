#!/usr/bin/env pwsh

Write-Host "Running PR tests locally..." -ForegroundColor Green

# Test backend
Write-Host "`nRunning backend tests..." -ForegroundColor Yellow
Set-Location backend
$backendResult = python -m pytest test_basic.py test_simple_endpoint.py test_endpoints.py test_simple_batch.py --tb=short -q --disable-warnings
$backendExitCode = $LASTEXITCODE
Set-Location ..

if ($backendExitCode -eq 0) {
    Write-Host "✅ Backend tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Backend tests failed" -ForegroundColor Red
}

# Test frontend build
Write-Host "`nRunning frontend build..." -ForegroundColor Yellow
Set-Location frontend
$buildResult = npm run build
$buildExitCode = $LASTEXITCODE

if ($buildExitCode -eq 0) {
    Write-Host "✅ Frontend build passed" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend build failed" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Test frontend basic tests
Write-Host "`nRunning frontend basic tests..." -ForegroundColor Yellow
$testResult = npm test -- __tests__/basic.test.ts --passWithNoTests
$testExitCode = $LASTEXITCODE

if ($testExitCode -eq 0) {
    Write-Host "✅ Frontend tests passed" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend tests failed" -ForegroundColor Red
}

# Bundle size analysis
Write-Host "`nAnalyzing bundle size..." -ForegroundColor Yellow
Write-Host "=== Bundle Size Analysis ===" -ForegroundColor Cyan

# Get static assets size (actual bundle)
if (Test-Path ".next/static") {
    $staticSize = (Get-ChildItem -Path ".next/static" -Recurse | Measure-Object -Property Length -Sum).Sum
    $staticSizeMB = [math]::Round($staticSize / 1MB, 2)
    Write-Host "Static assets size: $staticSizeMB MB" -ForegroundColor White
} else {
    Write-Host "Static assets: Not found" -ForegroundColor Yellow
    $staticSizeMB = 0
}

# Get server bundle size (excluding cache)
$serverSize = 0
if (Test-Path ".next/server") {
    $serverSize = (Get-ChildItem -Path ".next/server" -Recurse -Exclude "*.cache*" | Measure-Object -Property Length -Sum).Sum
    $serverSizeMB = [math]::Round($serverSize / 1MB, 2)
    Write-Host "Server bundle size: $serverSizeMB MB" -ForegroundColor White
} else {
    $serverSizeMB = 0
}

# Calculate actual production bundle size (excluding cache)
$productionSize = $staticSize + $serverSize
$productionSizeMB = [math]::Round($productionSize / 1MB, 2)
Write-Host "Production bundle size: $productionSizeMB MB" -ForegroundColor Cyan

# Analyze JavaScript bundles
if (Test-Path ".next/static/chunks") {
    Write-Host "JavaScript chunks:" -ForegroundColor White
    Get-ChildItem -Path ".next/static/chunks" -Filter "*.js" | 
        Sort-Object Length -Descending | 
        Select-Object -First 10 | 
        ForEach-Object { 
            $sizeKB = [math]::Round($_.Length / 1KB, 1)
            Write-Host "  $sizeKB KB - $($_.Name)" -ForegroundColor Gray
        }
}

# Check for large files (>500KB) in production files only
Write-Host "Large files (>500KB):" -ForegroundColor White
$largeFiles = Get-ChildItem -Path ".next/static" -Filter "*.js" -Recurse | Where-Object { $_.Length -gt 500KB }
if ($largeFiles) {
    $largeFiles | ForEach-Object {
        $sizeKB = [math]::Round($_.Length / 1KB, 1)
        Write-Host "  $sizeKB KB - $($_.Name)" -ForegroundColor Red
    }
} else {
    Write-Host "  No large files found" -ForegroundColor Green
}

# Bundle size check (warn if production bundle over 5MB)
if ($productionSizeMB -gt 5) {
    Write-Host "⚠️  Production bundle size is large (>5MB)" -ForegroundColor Yellow
    $bundleSizeCheck = 1
} else {
    Write-Host "✅ Production bundle size is acceptable" -ForegroundColor Green
    $bundleSizeCheck = 0
}

Set-Location ..

# Summary
Write-Host "`n=== PR Test Summary ===" -ForegroundColor Cyan
if ($backendExitCode -eq 0) {
    Write-Host "Backend Tests: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Backend Tests: ❌ FAILED" -ForegroundColor Red
}

if ($buildExitCode -eq 0) {
    Write-Host "Frontend Build: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Frontend Build: ❌ FAILED" -ForegroundColor Red
}

if ($testExitCode -eq 0) {
    Write-Host "Frontend Tests: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Frontend Tests: ❌ FAILED" -ForegroundColor Red
}

if ($bundleSizeCheck -eq 0) {
    Write-Host "Bundle Size: ✅ PASSED" -ForegroundColor Green
} else {
    Write-Host "Bundle Size: ⚠️  WARNING" -ForegroundColor Yellow
}

if ($backendExitCode -eq 0 -and $buildExitCode -eq 0 -and $testExitCode -eq 0 -and $bundleSizeCheck -eq 0) {
    Write-Host "`n🎉 All PR tests would PASS in CI!" -ForegroundColor Green
    exit 0
} elseif ($backendExitCode -eq 0 -and $buildExitCode -eq 0 -and $testExitCode -eq 0) {
    Write-Host "`n⚠️  PR tests would pass but with bundle size warning" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "`n💥 Some PR tests would FAIL in CI" -ForegroundColor Red
    exit 1
}