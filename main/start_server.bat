@echo off
echo ========================================
echo SO-100 Remote Control Server
echo ========================================
echo.

echo Installing required packages...
pip install websockets

echo.
echo Starting SO-100 Remote Control Server...
echo Server will be available at: ws://[YOUR-IP]:8765
echo.
echo Press Ctrl+C to stop the server
echo ========================================
echo.

python remote_control_server.py

pause
