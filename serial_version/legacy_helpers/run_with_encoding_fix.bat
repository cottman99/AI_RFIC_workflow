@echo off
REM Batch file to run Python with UTF-8 encoding
set PYTHONIOENCODING=utf-8
set SCRIPT_DIR=%~dp0
set SERIAL_ROOT=%SCRIPT_DIR%..
echo Running batch processor with UTF-8 encoding...
python "%SERIAL_ROOT%\batch_processor.py" --config "%SERIAL_ROOT%\batch_config.json"
echo.
echo Batch processing complete!
pause
