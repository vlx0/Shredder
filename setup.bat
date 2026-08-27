@echo off
cd /d "%~dp0"
python -m pip install -q -r requirements.txt
echo.
echo Shredder ready. Launching...
start "" pythonw "%~dp0run_shredder.pyw"
