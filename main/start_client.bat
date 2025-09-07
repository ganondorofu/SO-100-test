@echo off
echo ========================================
echo SO-100 Remote Control Client
echo ========================================
echo.

echo Installing required packages...
pip install websockets

echo.
echo Starting SO-100 Remote Control Client...
echo GUI will open shortly...
echo ========================================
echo.

python remote_control_client.py

pause
