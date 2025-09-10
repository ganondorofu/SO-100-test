#!/usr/bin/env python3
"""
SO-100 WebSocket Remote Control
LeRobotのcontrol_robot.pyをベースにしたWebSocketリモートコントロールシステム

使用方法:
# サーバー起動
python websocket_control_robot.py server --robot.type=so100 --com-port COM5

# クライアント起動  
python websocket_control_robot.py client --server-url ws://10.0.20.109:8765
"""

import asyncio
import json
import logging
import sys
import time
import threading
import queue
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import traceback

# WebSocket imports
import websockets
import websockets.exceptions

# LeRobot imports
from lerobot.common.robot_devices.robots.utils import make_robot_from_config
from lerobot.common.robot_devices.robots.configs import So100RobotConfig
from lerobot.common.robot_devices.motors.feetech import FeetechMotorsBusConfig
from lerobot.common.utils.utils import init_logging
from lerobot.configs import parser

# GUI imports
import tkinter as tk
from tkinter import ttk


@dataclass
class WebSocketServerConfig:
    """WebSocketサーバー設定"""
    host: str = "0.0.0.0"
    port: int = 8765
    com_port: str = "COM5"
    fps: int = 20
    display_data: bool = False


@dataclass  
class WebSocketClientConfig:
    """WebSocketクライアント設定"""
    server_url: str = "ws://10.0.20.109:8765"
    reconnect_interval: float = 5.0
    command_timeout: float = 1.0


class SO100WebSocketServer:
    """SO-100 WebSocketサーバー（LeRobotベース）"""
    
    def __init__(self, config: WebSocketServerConfig):
        self.config = config
        self.robot = None
        self.clients = set()
        self.command_queue = queue.Queue()
        
        # ロボット状態
        self.robot_connected = False
        self.current_positions = {}
        self.target_positions = {}
        self.emergency_stop = False
        
        # ログ設定
        init_logging()
        self.logger = logging.getLogger(__name__)
        
        # 制御ループ用
        self.control_thread = None
        self.running = False
        
        # シリアル通信用の排他制御
        self.serial_lock = threading.Lock()
        self.last_status_update = time.time()
        self.status_update_interval = 0.5  # 500ms間隔でステータス更新
        
    def get_local_ip(self):
        """ローカルIPアドレスを取得"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"
    
    def _create_robot_config(self):
        """SO-100ロボット設定を作成"""
        try:
            # Feetechモーターバス設定
            follower_arms = {
                "main": FeetechMotorsBusConfig(
                    port=self.config.com_port,
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
            robot_config = So100RobotConfig(
                leader_arms={},  # リーダーアームは使用しない
                follower_arms=follower_arms,
                cameras={},
                max_relative_target=None
            )
            
            return robot_config
            
        except Exception as e:
            self.logger.error(f"Failed to create robot config: {e}")
            raise
    
    def _init_robot(self):
        """ロボットを初期化"""
        try:
            self.logger.info(f"Initializing SO-100 robot on {self.config.com_port}...")
            print(f"🤖 Initializing robot on {self.config.com_port}...")
            
            # ロボット設定作成
            robot_config = self._create_robot_config()
            
            # ロボット作成（LeRobotの標準方法）
            self.robot = make_robot_from_config(robot_config)
            
            # 接続
            print("🔌 Connecting to robot...")
            self.robot.connect()
            print("✅ Robot connected successfully")
            
            # GUIを隠す（WebSocketモードではGUI不要）
            if hasattr(self.robot, 'gui'):
                self.robot.gui.hide()
            
            # 初期位置読み取りと目標位置初期化
            current_pos = self.robot._read_current_positions()
            self.robot.keyboard_controller.initialize_target_positions(current_pos)
            
            # 初期位置読み取り
            self._update_robot_status()
            self.robot_connected = True
            
            # モーター動作テスト
            self._test_motor_movement()
            
            self.logger.info("Robot initialization completed successfully")
            print("🎉 Robot ready for remote control!")
            
        except Exception as e:
            error_msg = f"Failed to initialize robot: {e}"
            self.logger.error(error_msg)
            print(f"❌ {error_msg}")
            self.robot_connected = False
            traceback.print_exc()
    
    def _test_motor_movement(self):
        """モーター動作テスト（排他制御付き）"""
        try:
            print("🔧 Testing motor movement (shoulder_pan)...")
            
            # シリアル通信の排他制御
            with self.serial_lock:
                # 現在位置を読み取り
                current_pos = self.robot._read_current_positions()
                original_pos = current_pos["main"].clone()
                
                # shoulder_panを5度動かす
                test_pos = original_pos.clone()
                test_pos[0] += 5.0
                
                print(f"➡️ Moving shoulder_pan from {original_pos[0]:.1f}° to {test_pos[0]:.1f}°...")
                self.robot.follower_arms["main"].write("Goal_Position", test_pos.numpy().astype('float32'))
            
            time.sleep(2.0)
            
            # シリアル通信の排他制御
            with self.serial_lock:
                # 元の位置に戻す
                print(f"⬅️ Returning to original position...")
                self.robot.follower_arms["main"].write("Goal_Position", original_pos.numpy().astype('float32'))
            
            time.sleep(2.0)
            print("✅ Motor movement test completed!")
            
        except Exception as e:
            print(f"⚠️ Motor movement test failed: {e}")
    
    def _update_robot_status(self):
        """ロボット状態を更新（頻度制限付き）"""
        current_time = time.time()
        
        # 頻度制限：前回更新から一定時間経過した場合のみ更新
        if current_time - self.last_status_update < self.status_update_interval:
            return
            
        if self.robot and self.robot_connected:
            try:
                # シリアル通信の排他制御
                with self.serial_lock:
                    # 現在位置を読み取り
                    current_pos = self.robot._read_current_positions()
                    self.current_positions = {
                        name: pos.tolist() for name, pos in current_pos.items()
                    }
                    
                    # 目標位置を取得
                    if hasattr(self.robot.keyboard_controller, 'target_positions'):
                        self.target_positions = {
                            name: pos.tolist() 
                            for name, pos in self.robot.keyboard_controller.target_positions.items()
                        }
                        
                # 最終更新時刻を記録
                self.last_status_update = current_time
                    
            except Exception as e:
                # シリアル通信エラーは頻繁に発生する可能性があるので、レベルを下げる
                if "Port is in use" in str(e):
                    # Port is in useエラーは詳細ログのみ
                    self.logger.debug(f"Serial port busy during status update: {e}")
                else:
                    self.logger.error(f"Failed to update robot status: {e}")
    
    def _process_commands(self):
        """コマンドキューを処理"""
        while self.running:
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
            if not self.robot or not self.robot_connected:
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
                import torch
                current_pos = self.robot.follower_arms["main"].read("Present_Position")
                current_pos = torch.from_numpy(current_pos)
                
                # 目標位置を現在位置に設定
                self.robot.keyboard_controller.target_positions["main"] = current_pos.clone()
                
                # 緊急停止状態を有効化
                self.robot.keyboard_controller.emergency_stop_active = True
                self.emergency_stop = True
                
                self.logger.info("Emergency stop executed")
                print("🚨 Emergency stop activated!")
                
            except Exception as e:
                self.logger.error(f"Emergency stop failed: {e}")
    
    def _control_loop(self):
        """ロボット制御ループ（ヘッドレスモード・排他制御付き）"""
        while self.running:
            try:
                if self.robot and self.robot_connected:
                    # シリアル通信の排他制御
                    with self.serial_lock:
                        # 直接制御ループを実行（Tkinter GUI無し）
                        # 現在位置読み取り
                        current_positions = self.robot._read_current_positions()
                        
                        # 目標位置計算
                        goal_positions = self.robot.keyboard_controller.calculate_goal_positions(current_positions)
                        
                        # 安全制限適用
                        goal_positions = self.robot._apply_safety_limits(goal_positions)
                        
                        # 目標位置送信
                        self.robot._send_goal_positions(goal_positions)
                    
                time.sleep(1.0 / self.config.fps)  # FPS制御
                
            except Exception as e:
                # シリアル通信エラーの詳細ログ
                if "Port is in use" in str(e):
                    self.logger.debug(f"Serial port busy during control: {e}")
                elif "main thread is not in main loop" not in str(e):
                    self.logger.error(f"Error in control loop: {e}")
                time.sleep(0.1)
    
    async def handle_client(self, websocket, path=None):
        """クライアント接続を処理"""
        self.clients.add(websocket)
        try:
            client_addr = websocket.remote_address
        except:
            client_addr = "unknown"
        
        self.logger.info(f"🔌 Client connected: {client_addr}")
        print(f"🔌 Client connected: {client_addr}")
        
        try:
            # ウェルカムメッセージ送信
            welcome_msg = {
                'type': 'welcome',
                'message': 'Connected to SO-100 WebSocket Server',
                'robot_connected': self.robot_connected,
                'emergency_stop': self.emergency_stop
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
                self._update_robot_status()
                
                status_msg = {
                    'type': 'status_update',
                    'robot_connected': self.robot_connected,
                    'current_positions': self.current_positions,
                    'target_positions': self.target_positions,
                    'emergency_stop': self.emergency_stop,
                    'timestamp': time.time()
                }
                
                await websocket.send(json.dumps(status_msg))
                await asyncio.sleep(0.1)  # 100ms間隔
                
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                self.logger.error(f"Error sending status update: {e}")
                break
    
    async def start_server(self):
        """WebSocketサーバーを開始"""
        local_ip = self.get_local_ip()
        
        print("=" * 60)
        print("🤖 SO-100 WebSocket Remote Control Server")
        print("=" * 60)
        print(f"🔌 COM Port: {self.config.com_port}")
        print(f"📡 Server: {self.config.host}:{self.config.port}")
        print(f"🌐 Local IP: {local_ip}:{self.config.port}")
        print(f"📱 Client URL: ws://{local_ip}:{self.config.port}")
        print("=" * 60)
        
        # ロボット初期化
        robot_thread = threading.Thread(target=self._init_robot, daemon=True)
        robot_thread.start()
        
        # コマンド処理スレッド開始
        self.running = True
        command_thread = threading.Thread(target=self._process_commands, daemon=True)
        command_thread.start()
        
        # 制御ループスレッド開始
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        
        # WebSocketサーバー開始
        try:
            async with websockets.serve(self.handle_client, self.config.host, self.config.port):
                self.logger.info(f"✅ Server started on {self.config.host}:{self.config.port}")
                print("✅ Server is running! Waiting for clients...")
                await asyncio.Future()  # 永続実行
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            print(f"❌ Server startup failed: {e}")
            raise
    
    def shutdown(self):
        """サーバーシャットダウン"""
        self.running = False
        if self.robot and self.robot.is_connected:
            self.robot.disconnect()


class SO100WebSocketClient:
    """SO-100 WebSocketクライアント（GUI付き）"""
    
    def __init__(self, config: WebSocketClientConfig):
        self.config = config
        self.websocket = None
        self.connected = False
        self.robot_connected = False
        self.emergency_stop = False
        
        # asyncioループ用
        self.loop = None
        
        # GUI初期化
        self.root = tk.Tk()
        self.root.title("SO-100 Remote Control Client")
        self.root.geometry("500x400")
        
        self._setup_gui()
        self._setup_key_bindings()
        
        # ログ設定
        init_logging()
        self.logger = logging.getLogger(__name__)
        
        # キー状態管理
        self.pressed_keys = set()
        
    def _setup_gui(self):
        """GUI設定"""
        # 接続状態表示
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=10, padx=10, fill='x')
        
        ttk.Label(status_frame, text="Connection Status:").pack(side='left')
        self.connection_label = ttk.Label(status_frame, text="Disconnected", foreground="red")
        self.connection_label.pack(side='left', padx=(10, 0))
        
        ttk.Label(status_frame, text="Robot Status:").pack(side='left', padx=(20, 0))
        self.robot_label = ttk.Label(status_frame, text="Unknown", foreground="gray")
        self.robot_label.pack(side='left', padx=(10, 0))
        
        # 接続ボタン
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=10)
        
        self.connect_button = ttk.Button(button_frame, text="Connect", command=self._connect_clicked)
        self.connect_button.pack(side='left', padx=5)
        
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self._disconnect_clicked, state='disabled')
        self.disconnect_button.pack(side='left', padx=5)
        
        self.emergency_button = ttk.Button(button_frame, text="Emergency Stop", command=self._emergency_stop, state='disabled')
        self.emergency_button.pack(side='left', padx=5)
        
        # キーボード操作説明
        instructions = """
キーボード操作説明:
W/S: 肩の上げ下げ (shoulder_lift)
A/D: 肩の左右回転 (shoulder_pan) - 反転済み
Q/E: 肘の曲げ伸ばし (elbow_flex)
R/F: 手首の前後 (wrist_flex)
Z/X: 手首の回転 (wrist_roll) - 反転済み
C/V: グリッパーの開閉 (gripper) - 反転済み

長押しで継続移動
ESC: 緊急停止
        """
        
        instructions_frame = ttk.LabelFrame(self.root, text="Controls", padding=10)
        instructions_frame.pack(pady=10, padx=10, fill='both', expand=True)
        
        instructions_label = ttk.Label(instructions_frame, text=instructions, justify='left')
        instructions_label.pack()
        
        # ステータス表示
        status_text_frame = ttk.LabelFrame(self.root, text="Robot Status", padding=10)
        status_text_frame.pack(pady=10, padx=10, fill='x')
        
        self.status_text = tk.Text(status_text_frame, height=6, width=60)
        scrollbar = ttk.Scrollbar(status_text_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _setup_key_bindings(self):
        """キーバインド設定"""
        self.root.bind('<KeyPress>', self._on_key_press)
        self.root.bind('<KeyRelease>', self._on_key_release)
        self.root.bind('<Escape>', self._on_escape)
        
        # フォーカス設定
        self.root.focus_set()
    
    def _connect_clicked(self):
        """接続ボタンクリック"""
        if not self.connected and self.loop:
            # asyncioループに接続タスクを追加
            asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
    
    def _disconnect_clicked(self):
        """切断ボタンクリック"""
        if self.connected and self.loop:
            # asyncioループに切断タスクを追加
            asyncio.run_coroutine_threadsafe(self._disconnect(), self.loop)
    
    def _emergency_stop(self):
        """緊急停止ボタン"""
        if self.connected and self.loop:
            # asyncioループに緊急停止タスクを追加
            command = {'type': 'emergency_stop'}
            asyncio.run_coroutine_threadsafe(self._send_command(command), self.loop)
    
    async def _connect(self):
        """WebSocketサーバーに接続"""
        try:
            self.connection_label.config(text="Connecting...", foreground="orange")
            self.connect_button.config(state='disabled')
            
            self.websocket = await websockets.connect(self.config.server_url)
            self.connected = True
            
            self.connection_label.config(text="Connected", foreground="green")
            self.connect_button.config(state='disabled')
            self.disconnect_button.config(state='normal')
            self.emergency_button.config(state='normal')
            
            # メッセージ受信ループ開始
            asyncio.create_task(self._receive_messages())
            
            self.logger.info(f"Connected to {self.config.server_url}")
            
        except Exception as e:
            self.connection_label.config(text="Connection Failed", foreground="red")
            self.connect_button.config(state='normal')
            self.logger.error(f"Connection failed: {e}")
    
    async def _disconnect(self):
        """WebSocket接続を切断"""
        try:
            self.connected = False
            if self.websocket:
                await self.websocket.close()
                self.websocket = None
            
            self.connection_label.config(text="Disconnected", foreground="red")
            self.robot_label.config(text="Unknown", foreground="gray")
            self.connect_button.config(state='normal')
            self.disconnect_button.config(state='disabled')
            self.emergency_button.config(state='disabled')
            
            self.logger.info("Disconnected from server")
            
        except Exception as e:
            self.logger.error(f"Disconnect error: {e}")
    
    async def _send_command(self, command: Dict[str, Any]):
        """コマンドを送信"""
        if self.connected and self.websocket:
            try:
                await self.websocket.send(json.dumps(command))
            except Exception as e:
                self.logger.error(f"Failed to send command: {e}")
    
    async def _receive_messages(self):
        """メッセージ受信ループ"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    self._handle_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON received: {message}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Server connection closed")
            await self._disconnect()
        except Exception as e:
            self.logger.error(f"Error receiving messages: {e}")
            await self._disconnect()
    
    def _handle_message(self, data: Dict[str, Any]):
        """受信メッセージを処理"""
        msg_type = data.get('type')
        
        if msg_type == 'welcome':
            self.robot_connected = data.get('robot_connected', False)
            self._update_robot_status()
            
        elif msg_type == 'status_update':
            self.robot_connected = data.get('robot_connected', False)
            self.emergency_stop = data.get('emergency_stop', False)
            self._update_robot_status()
            self._update_status_display(data)
    
    def _update_robot_status(self):
        """ロボット状態表示を更新"""
        if self.robot_connected:
            status_text = "Connected"
            color = "green"
        else:
            status_text = "Disconnected"
            color = "red"
            
        if self.emergency_stop:
            status_text += " (EMERGENCY STOP)"
            color = "orange"
            
        self.robot_label.config(text=status_text, foreground=color)
    
    def _update_status_display(self, data: Dict[str, Any]):
        """ステータス表示を更新"""
        try:
            positions = data.get('current_positions', {})
            targets = data.get('target_positions', {})
            
            if positions.get('main'):
                pos_text = f"Positions: {[f'{p:.1f}' for p in positions['main']]}\n"
                self.status_text.insert(tk.END, pos_text)
                
            # スクロールを最下部に
            self.status_text.see(tk.END)
            
            # テキストが長くなりすぎたら古い行を削除
            lines = self.status_text.get("1.0", tk.END).split('\n')
            if len(lines) > 20:
                self.status_text.delete("1.0", "2.0")
                
        except Exception as e:
            self.logger.error(f"Error updating status display: {e}")
    
    def _on_key_press(self, event):
        """キー押下処理"""
        if not self.connected or not self.robot_connected or not self.loop:
            return
            
        key = event.keysym.lower()
        
        if key not in self.pressed_keys:
            self.pressed_keys.add(key)
            command = {
                'type': 'key_press',
                'key': key
            }
            asyncio.run_coroutine_threadsafe(self._send_command(command), self.loop)
    
    def _on_key_release(self, event):
        """キー離し処理"""
        if not self.connected or not self.robot_connected or not self.loop:
            return
            
        key = event.keysym.lower()
        
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            command = {
                'type': 'key_release',
                'key': key
            }
            asyncio.run_coroutine_threadsafe(self._send_command(command), self.loop)
    
    def _on_escape(self, event):
        """ESCキー処理（緊急停止）"""
        self._emergency_stop()
    
    def run(self):
        """クライアント実行"""
        import threading
        
        # asyncioイベントループを別スレッドで実行
        def run_async_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # 定期的にTkinterを更新する関数
            def update_gui():
                try:
                    self.root.update()
                    self.loop.call_later(0.01, update_gui)  # 10ms間隔
                except tk.TclError:
                    # Tkinterが終了した場合
                    self.loop.stop()
                except Exception as e:
                    self.logger.error(f"GUI update error: {e}")
                    self.loop.call_later(0.1, update_gui)  # エラー時は100ms後に再試行
            
            # GUI更新開始
            self.loop.call_soon(update_gui)
            
            try:
                # イベントループ開始
                self.loop.run_forever()
            except Exception as e:
                self.logger.error(f"Event loop error: {e}")
            finally:
                self.loop.close()
        
        # asyncioスレッド開始
        async_thread = threading.Thread(target=run_async_loop, daemon=True)
        async_thread.start()
        
        # メインスレッドでTkinterを実行
        try:
            # asyncioループの開始を少し待つ
            import time
            time.sleep(0.1)
            
            print("🖥️ SO-100 Remote Control Client")
            print(f"📡 Server URL: {self.config.server_url}")
            print("🔗 Click 'Connect' button to start remote control")
            
            # Tkinterメインループ
            self.root.mainloop()
            
        except KeyboardInterrupt:
            print("Client shutting down...")
        finally:
            # クリーンアップ
            if self.loop and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.loop.stop)


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SO-100 WebSocket Remote Control')
    subparsers = parser.add_subparsers(dest='mode', help='Mode: server or client')
    
    # サーバーモード
    server_parser = subparsers.add_parser('server', help='Start WebSocket server')
    server_parser.add_argument('--host', default='0.0.0.0', help='Server host')
    server_parser.add_argument('--port', type=int, default=8765, help='Server port')
    server_parser.add_argument('--com-port', default='COM5', help='COM port for robot')
    server_parser.add_argument('--fps', type=int, default=20, help='Control loop FPS')
    server_parser.add_argument('--robot.type', dest='robot_type', default='so100', help='Robot type')
    
    # クライアントモード  
    client_parser = subparsers.add_parser('client', help='Start WebSocket client')
    client_parser.add_argument('--server-url', default='ws://10.0.20.109:8765', help='Server WebSocket URL')
    
    # ポジション記録モード
    position_parser = subparsers.add_parser('position', help='Start position recording client')
    position_parser.add_argument('--server-url', default='ws://localhost:8765', help='Server WebSocket URL')
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        return
    
    try:
        if args.mode == 'server':
            config = WebSocketServerConfig(
                host=args.host,
                port=args.port,
                com_port=args.com_port,
                fps=args.fps
            )
            server = SO100WebSocketServer(config)
            asyncio.run(server.start_server())
            
        elif args.mode == 'client':
            config = WebSocketClientConfig(
                server_url=args.server_url
            )
            client = SO100WebSocketClient(config)
            client.run()
            
        elif args.mode == 'position':
            config = WebSocketClientConfig(
                server_url=args.server_url
            )
            # ポジション記録用クライアント（基本的にはclientと同じ）
            client = SO100WebSocketClient(config)
            client.run()
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
