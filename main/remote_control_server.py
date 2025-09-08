#!/usr/bin/env python3
"""
SO-100 Remote Control Server
別のパソコンからSO-100を操作するためのWebSocketサーバー
"""

import asyncio
import json
import logging
import websockets
import torch
import time
import socket
import traceback
from typing import Dict, Any
import threading
import queue

# LeRobot imports
from lerobot.common.robot_devices.robots.manipulator import ManipulatorRobot


class SO100RemoteServer:
    """SO-100リモート制御サーバー"""
    
    def __init__(self, host='0.0.0.0', port=8765, com_port='COM5'):
        self.host = host
        self.port = port
        self.com_port = com_port  # COMポート設定を追加
        self.robot = None
        self.clients = set()
        self.command_queue = queue.Queue()
        self.status_data = {
            'connected': False,
            'positions': {},
            'target_positions': {},
            'emergency_stop': False
        }
        
        # ログ設定
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # 起動時にCOMポート情報を表示
        print(f"🔌 Using COM Port: {self.com_port}")
        
    def get_local_ip(self):
        """ローカルIPアドレスを取得"""
        try:
            # Google DNSに接続してローカルIPを取得（実際には接続しない）
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
        
    async def start_server(self):
        """WebSocketサーバーを開始"""
        local_ip = self.get_local_ip()
        
        print("=" * 60)
        print("🤖 SO-100 Remote Control Server Starting...")
        print("=" * 60)
        print(f"� COM Port: {self.com_port}")
        print(f"�📡 Server Address: {self.host}:{self.port}")
        print(f"🌐 Local Network IP: {local_ip}:{self.port}")
        print(f"📱 Client URL: ws://{local_ip}:{self.port}")
        print("=" * 60)
        print("🔒 No firewall configuration required!")
        print("📋 Copy the Client URL to your remote computer")
        print("=" * 60)
        
        self.logger.info(f"Starting SO-100 remote server on {self.host}:{self.port}")
        self.logger.info(f"Local IP: {local_ip}")
        
        # ロボット初期化を別スレッドで実行
        robot_thread = threading.Thread(target=self._init_robot, daemon=True)
        robot_thread.start()
        
        # コマンド処理スレッド開始
        command_thread = threading.Thread(target=self._process_commands, daemon=True)
        command_thread.start()
        
        # WebSocketサーバー開始
        self.logger.info("Starting WebSocket server...")
        self.logger.info(f"Binding to {self.host}:{self.port}")
        
        # シンプルなサーバー起動（互換性重視）
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                self.logger.info("✅ Server started successfully")
                self.logger.info(f"📡 Listening on {self.host}:{self.port}")
                self.logger.info(f"🌐 Local Network URL: ws://{local_ip}:{self.port}")
                print("✅ Server is running! Waiting for clients...")
                await asyncio.Future()  # 永続実行
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            print(f"❌ Server startup failed: {e}")
            raise
            
    def _check_com_port(self):
        """COMポートの可用性をチェック"""
        try:
            import serial.tools.list_ports
            
            # 利用可能なCOMポートを取得
            available_ports = [port.device for port in serial.tools.list_ports.comports()]
            print(f"🔍 Available COM ports: {available_ports}")
            
            if self.com_port in available_ports:
                print(f"✅ {self.com_port} is available")
                return True
            else:
                print(f"❌ {self.com_port} is not available")
                return False
                
        except ImportError:
            print("⚠️ pyserial not installed, cannot check COM ports")
            return True  # assume available
        except Exception as e:
            print(f"⚠️ Error checking COM ports: {e}")
            return True  # assume available
            
    def _init_robot(self):
        """ロボットを初期化"""
        try:
            self.logger.info(f"Initializing SO-100 robot on {self.com_port}...")
            print(f"🤖 Initializing robot on {self.com_port}...")
            
            # COMポートをチェック
            if not self._check_com_port():
                raise RuntimeError(f"COM port {self.com_port} is not available")
            
            # ロボット設定（SO-100専用設定クラスを使用）
            from lerobot.common.robot_devices.robots.configs import So100RobotConfig
            from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBusConfig
            
            # Feetechモーターバス設定
            follower_arms = {
                "main": FeetechMotorsBusConfig(
                    port=self.com_port,
                    motors={
                        "shoulder_pan": (1, "sts3215"),
                        "shoulder_lift": (2, "sts3215"),
                        "elbow_flex": (3, "sts3215"),
                        "wrist_flex": (4, "sts3215"),
                        "wrist_roll": (5, "sts3215"),
                        "gripper": (6, "sts3215"),
                    },
                ),
            }
            
            # SO-100ロボット設定
            config = So100RobotConfig(
                leader_arms={},  # リーダーアームは使用しない
                follower_arms=follower_arms,
                cameras={},
                max_relative_target=None
            )
            
            print(f"🔧 SO-100 config created")
            
            # ロボット初期化
            print("📡 Creating ManipulatorRobot instance...")
            self.robot = ManipulatorRobot(config)
            
            # 接続
            print("🔌 Connecting to robot...")
            self.robot.connect()
            print("✅ Robot connected successfully")
            self.status_data['connected'] = True
            
            # 初期位置を読み取り
            print("📊 Reading initial positions...")
            current_pos = self.robot._read_current_positions()
            self.robot.keyboard_controller.initialize_target_positions(current_pos)
            print("🎯 Target positions initialized")
            
            # モーター動作テスト - shoulder_panを少し動かす
            print("🔧 Testing motor movement (shoulder_pan)...")
            try:
                import time
                import numpy as np
                
                # 現在位置を保存
                original_pos = current_pos["main"].clone()
                print(f"📍 Original positions: {original_pos}")
                
                # shoulder_pan (インデックス0) を5度動かす
                test_pos = original_pos.clone()
                test_pos[0] += 5.0  # 5度プラス方向
                
                print(f"➡️ Moving shoulder_pan from {original_pos[0]:.1f}° to {test_pos[0]:.1f}°...")
                self.robot.follower_arms["main"].write("Goal_Position", test_pos.numpy().astype(np.float32))
                
                # 2秒待つ
                time.sleep(2.0)
                
                # 元の位置に戻す
                print(f"⬅️ Returning shoulder_pan to original position {original_pos[0]:.1f}°...")
                self.robot.follower_arms["main"].write("Goal_Position", original_pos.numpy().astype(np.float32))
                
                # 2秒待つ
                time.sleep(2.0)
                
                print("✅ Motor movement test completed - Robot is responding!")
                
            except Exception as e:
                print(f"⚠️ Motor movement test failed: {e}")
                print(f"📋 Motor test error: {traceback.format_exc()}")
            
            self.logger.info("Robot initialized successfully")
            print("✅ Robot initialization complete")
            
        except Exception as e:
            error_msg = f"Failed to initialize robot: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            print(f"🔍 Error details: {type(e).__name__}: {e}")
            self.status_data['connected'] = False
            
            # エラー内容をさらに詳細に記録
            import traceback
            traceback.print_exc()
            
    def _process_commands(self):
        """コマンドキューを処理"""
        while True:
            try:
                if not self.command_queue.empty():
                    command = self.command_queue.get()
                    self._execute_command(command)
                time.sleep(0.01)  # 10ms間隔
            except Exception as e:
                self.logger.error(f"Error processing command: {e}")
                
    def _execute_command(self, command: Dict[str, Any]):
        """コマンドを実行"""
        try:
            if not self.robot or not self.status_data['connected']:
                return
                
            cmd_type = command.get('type')
            
            if cmd_type == 'key_press':
                key = command.get('key')
                self._simulate_key_press(key)
                
            elif cmd_type == 'key_release':
                key = command.get('key')
                self._simulate_key_release(key)
                
            elif cmd_type == 'emergency_stop':
                self._emergency_stop()
                
            elif cmd_type == 'set_target':
                motor_idx = command.get('motor_idx')
                position = command.get('position')
                self._set_target_position(motor_idx, position)
                
            elif cmd_type == 'get_status':
                self._update_status()
                
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")
            
    def _simulate_key_press(self, key: str):
        """キー押下をシミュレート"""
        if key in self.robot.keyboard_controller.key_mapping:
            motor_idx, delta = self.robot.keyboard_controller.key_mapping[key]
            
            # 目標位置を更新
            if "main" in self.robot.keyboard_controller.target_positions:
                self.robot.keyboard_controller.target_positions["main"][motor_idx] += delta
                self.logger.info(f"Key '{key}' pressed - Motor {motor_idx} target updated")
                
    def _simulate_key_release(self, key: str):
        """キー離しをシミュレート"""
        self.logger.info(f"Key '{key}' released")
        
    def _emergency_stop(self):
        """緊急停止"""
        if self.robot:
            try:
                current_pos = self.robot.follower_arms["main"].read("Present_Position")
                current_pos = torch.from_numpy(current_pos)
                self.robot.keyboard_controller.target_positions["main"] = current_pos.clone()
                self.status_data['emergency_stop'] = True
                self.logger.info("Emergency stop executed")
            except Exception as e:
                self.logger.error(f"Emergency stop failed: {e}")
                
    def _set_target_position(self, motor_idx: int, position: float):
        """目標位置を直接設定"""
        if self.robot and "main" in self.robot.keyboard_controller.target_positions:
            self.robot.keyboard_controller.target_positions["main"][motor_idx] = position
            self.logger.info(f"Motor {motor_idx} target set to {position}")
            
    def _update_status(self):
        """ステータス情報を更新"""
        if self.robot and self.status_data['connected']:
            try:
                # 現在位置を読み取り
                current_pos = self.robot._read_current_positions()
                self.status_data['positions'] = {
                    name: pos.tolist() for name, pos in current_pos.items()
                }
                
                # 目標位置を取得
                if hasattr(self.robot.keyboard_controller, 'target_positions'):
                    self.status_data['target_positions'] = {
                        name: pos.tolist() 
                        for name, pos in self.robot.keyboard_controller.target_positions.items()
                    }
                    
            except Exception as e:
                self.logger.error(f"Failed to update status: {e}")
                
    async def handle_client(self, websocket, path=None):
        """クライアント接続を処理（websocketsライブラリ互換性対応）"""
        # pathパラメータは新しいバージョンでは使われない場合があるため、オプショナルにする
        self.clients.add(websocket)
        try:
            client_addr = websocket.remote_address
        except:
            client_addr = "unknown"
        
        self.logger.info(f"🔌 Client connection attempt from: {client_addr}")
        print(f"🔌 Client connected: {client_addr}")
        
        try:
            # ウェルカムメッセージ送信
            welcome_msg = {
                'type': 'welcome',
                'message': 'Connected to SO-100 Remote Server',
                'status': self.status_data
            }
            await websocket.send(json.dumps(welcome_msg))
            self.logger.info(f"✅ Welcome message sent to {client_addr}")
            
            # ステータス送信ループ開始
            status_task = asyncio.create_task(self._send_status_updates(websocket))
            
            # クライアントからのメッセージ処理
            async for message in websocket:
                try:
                    command = json.loads(message)
                    self.command_queue.put(command)
                    
                    # 確認応答
                    response = {
                        'type': 'ack',
                        'command': command.get('type'),
                        'timestamp': time.time()
                    }
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON from {client_addr}: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client disconnected: {client_addr}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            self.clients.discard(websocket)
            if 'status_task' in locals():
                status_task.cancel()
                
    async def _send_status_updates(self, websocket):
        """定期的にステータス更新を送信"""
        while True:
            try:
                self._update_status()
                
                status_msg = {
                    'type': 'status_update',
                    'data': self.status_data,
                    'timestamp': time.time()
                }
                
                await websocket.send(json.dumps(status_msg))
                await asyncio.sleep(0.1)  # 100ms間隔
                
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                self.logger.error(f"Error sending status update: {e}")
                break
                
    def run_robot_loop(self):
        """ロボット制御ループ"""
        while True:
            try:
                if self.robot and self.status_data['connected']:
                    # ロボットのテレオペレーションステップを実行
                    self.robot.keyboard_teleop_step(record_data=False)
                    
                time.sleep(0.05)  # 50ms間隔
                
            except Exception as e:
                self.logger.error(f"Error in robot loop: {e}")
                time.sleep(1)


def main():
    """メイン関数"""
    import argparse
    
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='SO-100 Remote Control Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host address (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8765, help='Server port (default: 8765)')
    parser.add_argument('--com-port', default='COM5', help='COM port for SO-100 robot (default: COM5)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 SO-100 Remote Control Server")
    print("=" * 60)
    print(f"🔌 COM Port: {args.com_port}")
    print(f"📡 Server: {args.host}:{args.port}")
    print("=" * 60)
    
    server = SO100RemoteServer(host=args.host, port=args.port, com_port=args.com_port)
    
    # ロボット制御ループを別スレッドで開始
    robot_loop_thread = threading.Thread(target=server.run_robot_loop, daemon=True)
    robot_loop_thread.start()
    
    # WebSocketサーバー開始
    try:
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Server error: {e}")


if __name__ == "__main__":
    main()
