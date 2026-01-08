# PowerShell script to switch LLM providers
# Usage: .\switch_llm_provider.ps1 llama
#        .\switch_llm_provider.ps1 anthropic
#        .\switch_llm_provider.ps1 openai

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("llama", "anthropic", "openai")]
    [string]$Provider
)

$envFile = ".env"

if (-not (Test-Path $envFile)) {
    Write-Host "Creating .env file..." -ForegroundColor Yellow
    New-Item -ItemType File -Path $envFile | Out-Null
}

# Read existing .env file
$content = Get-Content $envFile -ErrorAction SilentlyContinue
$newContent = @()

# Track if we've updated LLM_PROVIDER
$providerUpdated = $false
$llamaConfigAdded = $false
$anthropicConfigAdded = $false
$openaiConfigAdded = $false

foreach ($line in $content) {
    if ($line -match "^LLM_PROVIDER=") {
        $newContent += "LLM_PROVIDER=$Provider"
        $providerUpdated = $true
    }
    elseif ($line -match "^LLAMA_API_URL=") {
        $llamaConfigAdded = $true
        $newContent += $line
    }
    elseif ($line -match "^LLAMA_MODEL=") {
        $llamaConfigAdded = $true
        $newContent += $line
    }
    elseif ($line -match "^ANTHROPIC_API_KEY=") {
        $anthropicConfigAdded = $true
        $newContent += $line
    }
    elseif ($line -match "^OPENAI_API_KEY=") {
        $openaiConfigAdded = $true
        $newContent += $line
    }
    else {
        $newContent += $line
    }
}

# Add LLM_PROVIDER if it wasn't found
if (-not $providerUpdated) {
    $newContent += "LLM_PROVIDER=$Provider"
}

# Add provider-specific config if needed
if ($Provider -eq "llama") {
    if (-not $llamaConfigAdded) {
        $newContent += ""
        $newContent += "# Llama/Ollama Configuration"
        $newContent += "LLAMA_API_URL=http://localhost:11434"
        $newContent += "LLAMA_MODEL=llava:7b"
    }
}
elseif ($Provider -eq "anthropic") {
    if (-not $anthropicConfigAdded) {
        $newContent += ""
        $newContent += "# Anthropic Configuration"
        $newContent += "# ANTHROPIC_API_KEY=your_key_here"
    }
}
elseif ($Provider -eq "openai") {
    if (-not $openaiConfigAdded) {
        $newContent += ""
        $newContent += "# OpenAI Configuration"
        $newContent += "# OPENAI_API_KEY=your_key_here"
    }
}

# Write updated content
$newContent | Set-Content $envFile -Encoding UTF8

Write-Host "`n✓ Switched LLM provider to: $Provider" -ForegroundColor Green
Write-Host "`nCurrent configuration:" -ForegroundColor Cyan
Get-Content $envFile | Select-String -Pattern "LLM_PROVIDER|LLAMA_|ANTHROPIC_|OPENAI_" | ForEach-Object {
    Write-Host "  $_" -ForegroundColor Gray
}
Write-Host "`nNote: Restart your backend server for changes to take effect." -ForegroundColor Yellow

