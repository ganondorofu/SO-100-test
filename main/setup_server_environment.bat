@echo off
echo ===================================================
echo   SO-100 Server Environment Setup
echo   LeRobot + WebSocket環境の自動構築
echo ===================================================
echo.

echo Creating LeRobot environment...
$env:Path = "C:\Users\20\Anaconda3\Scripts;" + $env:Path
conda create -n lerobot python=3.10 -y

echo.
echo Activating environment...
call conda activate lerobot

echo.
echo Installing LeRobot with robot support...
pip install lerobot[robot]

echo.
echo Installing WebSocket support...
pip install websockets

echo.
echo Testing installation...
python -c "import lerobot; print(f'✅ LeRobot version: {lerobot.__version__}')"
python -c "from lerobot.common.robot_devices.robots.so100 import SO100Robot; print('✅ SO-100 support OK')"
python -c "import websockets; print('✅ WebSocket support OK')"

echo.
echo ===================================================
echo   Setup completed successfully!
echo   Run 'start_server.bat' to start the server
echo ===================================================
pause
