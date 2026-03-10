@echo off
REM Batch file to run Python with UTF-8 encoding
set PYTHONIOENCODING=utf-8
echo Running batch processor with UTF-8 encoding...
python batch_processor.py --config batch_config.json
echo.
echo Batch processing complete!
pause