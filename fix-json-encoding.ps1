# Fix JSON Encoding Issues (Remove BOM)
Write-Host "Fixing JSON encoding issues..." -ForegroundColor Cyan

# Find all JSON files
$jsonFiles = Get-ChildItem -Path . -Recurse -Include "*.json" -Exclude "node_modules" | Where-Object { $_.FullName -notmatch "node_modules" }

Write-Host "Found $($jsonFiles.Count) JSON files to check..." -ForegroundColor Yellow

foreach ($file in $jsonFiles) {
    Write-Host "Checking: $($file.FullName)" -ForegroundColor White
    
    # Read file as bytes to detect BOM
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    
    # Check for UTF-8 BOM (EF BB BF)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        Write-Host "  Found BOM - Removing..." -ForegroundColor Red
        
        # Remove BOM and save
        $content = [System.IO.File]::ReadAllText($file.FullName, [System.Text.Encoding]::UTF8)
        [System.IO.File]::WriteAllText($file.FullName, $content, [System.Text.UTF8Encoding]::new($false))
        
        Write-Host "  Fixed!" -ForegroundColor Green
    } else {
        # Also check if file starts with invisible characters
        $content = [System.IO.File]::ReadAllText($file.FullName)
        if ($content.StartsWith([char]0xFEFF)) {
            Write-Host "  Found Unicode BOM - Removing..." -ForegroundColor Red
            $content = $content.TrimStart([char]0xFEFF)
            [System.IO.File]::WriteAllText($file.FullName, $content, [System.Text.UTF8Encoding]::new($false))
            Write-Host "  Fixed!" -ForegroundColor Green
        } else {
            Write-Host "  OK" -ForegroundColor Green
        }
    }
}

Write-Host ""
Write-Host "JSON encoding fix complete!" -ForegroundColor Cyan
Write-Host "All JSON files should now be properly encoded without BOM." -ForegroundColor Green