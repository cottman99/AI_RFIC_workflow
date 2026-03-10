@echo off
REM Windows-compatible batch runner for EM simulation batch processing
REM This script handles encoding issues on Chinese Windows systems

echo === EM Simulation Batch Processor ===
echo Configuring Windows environment...

REM Set UTF-8 encoding for all Python processes
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Set console code page to UTF-8
chcp 65001 >nul

REM Check if config file exists
if exist "batch_config.json" (
    echo Using configuration: batch_config.json
    python -X utf8 batch_processor_ascii.py --config "batch_config.json"
) else (
    echo Configuration file not found, using defaults...
    python -X utf8 batch_processor_ascii.py --json-dir "./json_layout" --workspace "./batch_results"
)

echo.
echo === Batch processing complete ===
pause