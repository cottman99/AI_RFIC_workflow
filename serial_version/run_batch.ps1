# PowerShell script to run batch processing with proper encoding
Write-Host "=== EM Simulation Batch Processor ===" -ForegroundColor Green

# Set encoding to UTF-8
[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[System.Console]::InputEncoding = [System.Text.Encoding]::UTF8

# Set Python encoding
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Check if config file exists
$configFile = "batch_config.json"
if (Test-Path $configFile) {
    Write-Host "Using configuration: $configFile" -ForegroundColor Yellow
    python -X utf8 batch_processor_ascii.py --config $configFile
} else {
    Write-Host "Configuration file not found, using defaults..." -ForegroundColor Yellow
    python -X utf8 batch_processor_ascii.py --json-dir "./json_layout" --workspace "./batch_results"
}

Write-Host "=== Batch processing complete ===" -ForegroundColor Green