@echo off
echo ===================================================
echo   SO-100 Remote Control Server
echo   ローカルネットワーク用設定（ポート開放不要）
echo ===================================================
echo.

echo Activating LeRobot environment...
call conda activate lerobot

echo Installing/updating required packages...
pip install --upgrade websockets

echo.
echo Starting server...
echo サーバー起動時に表示されるIPアドレスをメモしてください
echo.
echo オプション指定例:
echo - COMポート変更: python remote_control_server.py --com-port COM6
echo - ローカルのみ: python remote_control_server.py --host 127.0.0.1
echo - 全ネットワーク: python remote_control_server.py --host 0.0.0.0
echo.

python remote_control_server.py

pause
