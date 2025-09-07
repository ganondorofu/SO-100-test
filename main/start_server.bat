@echo off
echo ===================================================
echo   SO-100 Remote Control Server
echo   ローカルネットワーク用設定（ポート開放不要）
echo ===================================================
echo.

echo Activating LeRobot environment...
call conda activate lerobot

echo Installing/updating required packages...
pip install websockets

echo.
echo Starting server...
echo サーバー起動時に表示されるIPアドレスをメモしてください
echo.

python remote_control_server.py

pause
