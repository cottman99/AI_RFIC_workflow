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

set SCRIPT_DIR=%~dp0
set SERIAL_ROOT=%SCRIPT_DIR%..
set CONFIG_FILE=%SERIAL_ROOT%\batch_config.json

REM Check if config file exists
if exist "%CONFIG_FILE%" (
    echo Using configuration: %CONFIG_FILE%
    python -X utf8 "%SCRIPT_DIR%batch_processor_ascii.py" --config "%CONFIG_FILE%"
) else (
    echo Configuration file not found, using defaults...
    python -X utf8 "%SCRIPT_DIR%batch_processor_ascii.py" --json-dir "%SERIAL_ROOT%\json_layout" --workspace "%SERIAL_ROOT%\batch_results"
)

echo.
echo === Batch processing complete ===
pause
