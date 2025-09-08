#!/usr/bin/env python3
"""
SO-100ロボット初期化テスト
WebSocketを使わずに直接ロボットの初期化をテストします。
"""

import argparse
import time
import sys
import traceback
from pathlib import Path

# LeRobotパス設定
lerobot_path = Path(__file__).parent / "lerobot"
if lerobot_path.exists():
    sys.path.insert(0, str(lerobot_path.parent))

def test_serial_ports():
    """利用可能なCOMポートをテスト"""
    print("=" * 50)
    print("🔍 Testing available COM ports...")
    
    try:
        import serial.tools.list_ports
        
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("❌ No COM ports found")
            return []
            
        print(f"✅ Found {len(ports)} COM ports:")
        for port in ports:
            print(f"  - {port.device}: {port.description}")
            
        return [port.device for port in ports]
        
    except ImportError:
        print("❌ pyserial not installed")
        return []
    except Exception as e:
        print(f"❌ Error checking COM ports: {e}")
        return []

def test_robot_initialization(com_port):
    """ロボット初期化をテスト"""
    print("=" * 50)
    print(f"🤖 Testing robot initialization on {com_port}...")
    
    try:
        # LeRobotインポート
        print("📦 Importing LeRobot...")
        from lerobot.common.robot_devices.robots.manipulator import ManipulatorRobot
        print("✅ LeRobot imported successfully")
        
        # ロボット設定
        print("⚙️ Creating robot configuration...")
        robot_cfg = {
            'robot_type': 'so100',
            'calibration': {
                'calib_dir': './calibration',
                'motors': {
                    'shoulder_pan': {},
                    'shoulder_lift': {},
                    'elbow_flex': {},
                    'wrist_flex': {},
                    'wrist_roll': {},
                    'gripper': {}
                }
            },
            'motors': {
                'shoulder_pan': {
                    'type': 'sts3215',
                    'port': com_port,
                    'id': 1,
                    'max_velocity': 50,
                    'max_torque': 100
                },
                'shoulder_lift': {
                    'type': 'sts3215',
                    'port': com_port,
                    'id': 2,
                    'max_velocity': 50,
                    'max_torque': 100
                },
                'elbow_flex': {
                    'type': 'sts3215',
                    'port': com_port,
                    'id': 3,
                    'max_velocity': 50,
                    'max_torque': 100
                },
                'wrist_flex': {
                    'type': 'sts3215',
                    'port': com_port,
                    'id': 4,
                    'max_velocity': 50,
                    'max_torque': 100
                },
                'wrist_roll': {
                    'type': 'sts3215',
                    'port': com_port,
                    'id': 5,
                    'max_velocity': 50,
                    'max_torque': 100
                },
                'gripper': {
                    'type': 'sts3215',
                    'port': com_port,
                    'id': 6,
                    'max_velocity': 50,
                    'max_torque': 100
                }
            }
        }
        print("✅ Robot configuration created")
        
        # ロボットインスタンス作成
        print("🏗️ Creating ManipulatorRobot instance...")
        robot = ManipulatorRobot(robot_cfg)
        print("✅ ManipulatorRobot instance created")
        
        # 接続テスト
        print("🔗 Testing robot connection...")
        robot.connect()
        print("✅ Robot connected successfully")
        
        # 位置読み取りテスト
        print("📊 Testing position reading...")
        positions = robot.get_joint_positions()
        print(f"✅ Current positions: {positions}")
        
        # トルクステータス確認
        print("💪 Testing torque status...")
        robot.set_torque_enabled(True)
        print("✅ Torque enabled")
        
        # クリーンアップ
        print("🧹 Cleaning up...")
        robot.disconnect()
        print("✅ Robot disconnected successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure LeRobot is properly installed")
        return False
    except Exception as e:
        print(f"❌ Robot initialization failed: {e}")
        print(f"📋 Full error: {traceback.format_exc()}")
        return False

def main():
    parser = argparse.ArgumentParser(description="SO-100 Robot Initialization Test")
    parser.add_argument("--com-port", default="COM3", help="COM port for robot communication")
    parser.add_argument("--skip-serial-test", action="store_true", help="Skip serial port testing")
    
    args = parser.parse_args()
    
    print("🔬 SO-100 Robot Initialization Test")
    print("=" * 50)
    
    # COMポートテスト
    if not args.skip_serial_test:
        available_ports = test_serial_ports()
        if available_ports and args.com_port not in available_ports:
            print(f"⚠️ Warning: {args.com_port} not in available ports: {available_ports}")
            print("❓ Do you want to continue anyway? (y/n)")
            response = input().lower()
            if response != 'y':
                print("🛑 Test cancelled")
                return
    
    # ロボット初期化テスト
    success = test_robot_initialization(args.com_port)
    
    print("=" * 50)
    if success:
        print("🎉 Robot initialization test PASSED")
        print(f"✅ Robot on {args.com_port} is working correctly")
    else:
        print("💥 Robot initialization test FAILED")
        print(f"❌ Robot on {args.com_port} failed to initialize")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check if SO-100 is powered on")
        print("2. Verify USB cable connection")
        print("3. Confirm correct COM port")
        print("4. Check if drivers are installed")
        print("5. Try a different COM port")

if __name__ == "__main__":
    main()
