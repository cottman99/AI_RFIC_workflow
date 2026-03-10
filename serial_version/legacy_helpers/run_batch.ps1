# PowerShell script to run batch processing with proper encoding
Write-Host "=== EM Simulation Batch Processor ===" -ForegroundColor Green

# Set encoding to UTF-8
[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[System.Console]::InputEncoding = [System.Text.Encoding]::UTF8

# Set Python encoding
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$serialRoot = Resolve-Path (Join-Path $scriptDir "..")

# Check if config file exists
$configFile = Join-Path $serialRoot "batch_config.json"
$asciiProcessor = Join-Path $scriptDir "batch_processor_ascii.py"
if (Test-Path $configFile) {
    Write-Host "Using configuration: $configFile" -ForegroundColor Yellow
    python -X utf8 $asciiProcessor --config $configFile
} else {
    Write-Host "Configuration file not found, using defaults..." -ForegroundColor Yellow
    python -X utf8 $asciiProcessor --json-dir (Join-Path $serialRoot "json_layout") --workspace (Join-Path $serialRoot "batch_results")
}

Write-Host "=== Batch processing complete ===" -ForegroundColor Green
