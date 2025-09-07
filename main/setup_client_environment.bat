@echo off
echo ===================================================
echo   SO-100 Client Environment Setup
echo   リモートクライアント環境の自動構築
echo ===================================================
echo.

echo Creating remote client environment...
conda create -n so100-remote python=3.10 -y

echo.
echo Activating environment...
call conda activate so100-remote

echo.
echo Installing required packages...
pip install --upgrade websockets

echo.
echo Testing installation...
python -c "import websockets; print('✅ WebSocket support OK')"
python -c "import tkinter; print('✅ GUI support OK')"

echo.
echo ===================================================
echo   Setup completed successfully!
echo   Run 'start_client.bat' to start the client
echo ===================================================
pause
