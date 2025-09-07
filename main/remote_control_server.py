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
from typing import Dict, Any
import threading
import queue

# LeRobot imports
from lerobot.common.robot_devices.robots.manipulator import ManipulatorRobot


class SO100RemoteServer:
    """SO-100リモート制御サーバー"""
    
    def __init__(self, host='0.0.0.0', port=8765):
        self.host = host
        self.port = port
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
        
    async def start_server(self):
        """WebSocketサーバーを開始"""
        self.logger.info(f"Starting SO-100 remote server on {self.host}:{self.port}")
        
        # ロボット初期化を別スレッドで実行
        robot_thread = threading.Thread(target=self._init_robot, daemon=True)
        robot_thread.start()
        
        # コマンド処理スレッド開始
        command_thread = threading.Thread(target=self._process_commands, daemon=True)
        command_thread.start()
        
        # WebSocketサーバー開始
        async with websockets.serve(self.handle_client, self.host, self.port):
            self.logger.info("Server started successfully")
            await asyncio.Future()  # 永続実行
            
    def _init_robot(self):
        """ロボットを初期化"""
        try:
            self.logger.info("Initializing SO-100 robot...")
            
            # ロボット設定
            config = {
                'robot_type': 'so100',
                'max_relative_target': None,
                'calibration_dir': '.cache',
                'gripper_open_degree': 45
            }
            
            # ロボット初期化
            self.robot = ManipulatorRobot(
                robot_type=config['robot_type'],
                max_relative_target=config['max_relative_target'],
                calibration_dir=config['calibration_dir'],
                gripper_open_degree=config['gripper_open_degree']
            )
            
            # 接続
            self.robot.connect()
            self.status_data['connected'] = True
            
            # 初期位置を読み取り
            current_pos = self.robot._read_current_positions()
            self.robot.keyboard_controller.initialize_target_positions(current_pos)
            
            self.logger.info("Robot initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize robot: {e}")
            self.status_data['connected'] = False
            
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
                
    async def handle_client(self, websocket, path):
        """クライアント接続を処理"""
        self.clients.add(websocket)
        client_addr = websocket.remote_address
        self.logger.info(f"Client connected: {client_addr}")
        
        try:
            # ウェルカムメッセージ送信
            welcome_msg = {
                'type': 'welcome',
                'message': 'Connected to SO-100 Remote Server',
                'status': self.status_data
            }
            await websocket.send(json.dumps(welcome_msg))
            
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
    server = SO100RemoteServer(host='0.0.0.0', port=8765)
    
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
