conda activate lerobot

(lerobot) PS C:\FUCKIN_ONEDRIVE\SO-100> python -m lerobot.scripts.configure_motor --port COM6 --brand feetech --model sts3215 --baudrate 1000000 --ID 2

python -m lerobot.scripts.control_robot --robot.type=so100 --robot.cameras="{}" --control.type=teleoperate