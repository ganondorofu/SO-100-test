@echo off
echo ===================================================
echo   SO-100 Remote Control Client  
echo   ローカルネットワーク接続用
echo ===================================================
echo.

echo Activating remote client environment...
call conda activate so100-remote

echo Installing/updating required packages...
pip install --upgrade websockets

echo.
echo Starting client...
echo サーバーから表示されたClient URLを入力してください
echo ===================================================
echo.

python remote_control_client.py

pause
