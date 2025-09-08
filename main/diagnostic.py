#!/usr/bin/env python3
"""
LeRobotインストール状況確認スクリプト
"""

import sys
import os
import importlib
from pathlib import Path

def check_python_environment():
    """Python環境の確認"""
    print("🐍 Python Environment Check")
    print("=" * 40)
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")  # 最初の3つだけ表示
    print()

def check_lerobot_installation():
    """LeRobotインストール状況の確認"""
    print("🤖 LeRobot Installation Check")
    print("=" * 40)
    
    # LeRobotディレクトリの確認
    lerobot_dir = Path("./lerobot")
    if lerobot_dir.exists():
        print(f"✅ LeRobot directory found: {lerobot_dir.absolute()}")
    else:
        print("❌ LeRobot directory not found")
        return False
    
    # LeRobotモジュールのインポートテスト
    try:
        import lerobot
        print(f"✅ LeRobot module imported: {lerobot.__file__}")
        print(f"✅ LeRobot version: {getattr(lerobot, '__version__', 'unknown')}")
    except ImportError as e:
        print(f"❌ LeRobot import failed: {e}")
        return False
    
    # ManipulatorRobotクラスのインポートテスト
    try:
        from lerobot.common.robot_devices.robots.manipulator import ManipulatorRobot
        print(f"✅ ManipulatorRobot class imported successfully")
    except ImportError as e:
        print(f"❌ ManipulatorRobot import failed: {e}")
        return False
    
    print()
    return True

def check_required_packages():
    """必要パッケージの確認"""
    print("📦 Required Packages Check")
    print("=" * 40)
    
    required_packages = [
        'serial',
        'numpy',
        'torch',
        'websockets',
        'asyncio',
        'tkinter'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'tkinter':
                import tkinter
                print(f"✅ {package} - OK")
            elif package == 'serial':
                import serial
                print(f"✅ {package} - OK (version: {getattr(serial, '__version__', 'unknown')})")
            elif package == 'asyncio':
                import asyncio
                print(f"✅ {package} - OK (built-in)")
            else:
                module = importlib.import_module(package)
                version = getattr(module, '__version__', 'unknown')
                print(f"✅ {package} - OK (version: {version})")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    print()
    
    if missing_packages:
        print("🔧 To install missing packages:")
        for package in missing_packages:
            if package == 'serial':
                print(f"  pip install pyserial")
            else:
                print(f"  pip install {package}")
        print()
    
    return len(missing_packages) == 0

def check_com_ports():
    """COMポートの確認"""
    print("🔌 COM Ports Check")
    print("=" * 40)
    
    try:
        import serial.tools.list_ports
        
        ports = list(serial.tools.list_ports.comports())
        if not ports:
            print("❌ No COM ports found")
        else:
            print(f"✅ Found {len(ports)} COM ports:")
            for port in ports:
                print(f"  📍 {port.device}: {port.description}")
                if 'USB' in port.description.upper() or 'SERIAL' in port.description.upper():
                    print(f"     💡 This might be your SO-100!")
    except ImportError:
        print("❌ pyserial not installed - cannot check COM ports")
    except Exception as e:
        print(f"❌ Error checking COM ports: {e}")
    
    print()

def check_workspace_structure():
    """ワークスペース構造の確認"""
    print("📁 Workspace Structure Check")
    print("=" * 40)
    
    important_files = [
        "./lerobot/__init__.py",
        "./lerobot/common/robot_devices/robots/manipulator.py",
        "./remote_control_server.py",
        "./remote_control_client.py",
        "./manipulator.py"
    ]
    
    for file_path in important_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
    
    print()

def main():
    """診断スクリプトのメイン関数"""
    print("🔍 SO-100 System Diagnostic")
    print("=" * 50)
    print()
    
    all_checks_passed = True
    
    # 各種チェック実行
    check_python_environment()
    
    if not check_lerobot_installation():
        all_checks_passed = False
    
    if not check_required_packages():
        all_checks_passed = False
    
    check_com_ports()
    check_workspace_structure()
    
    # 総合判定
    print("📋 Diagnostic Summary")
    print("=" * 40)
    
    if all_checks_passed:
        print("🎉 All checks PASSED!")
        print("✅ Your system appears to be ready for SO-100 operation")
        print()
        print("💡 Next steps:")
        print("1. Test robot initialization: python test_robot_init.py")
        print("2. Start remote server: python remote_control_server.py")
    else:
        print("⚠️ Some issues found!")
        print("❌ Please fix the issues above before proceeding")
        print()
        print("🔧 Common solutions:")
        print("1. Install missing packages: pip install -r requirements.txt")
        print("2. Check LeRobot installation")
        print("3. Verify SO-100 hardware connection")

if __name__ == "__main__":
    main()
