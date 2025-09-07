#!/usr/bin/env python3
"""
SO-100 Remote Control Client
別のパソコンからSO-100を操作するためのクライアント
"""

import asyncio
import json
import tkinter as tk
from tkinter import ttk, messagebox
import websockets
import threading
import time
import logging
import queue
from typing import Optional, Dict, Any


class SO100RemoteClient:
    """SO-100リモート制御クライアント"""
    
    def __init__(self):
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connected = False
        self.server_url = "ws://localhost:8765"  # デフォルト
        self.status_data = {}
        
        # コマンドキュー
        self.command_queue = queue.Queue()
        
        # ログ設定
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # GUI初期化
        self.setup_gui()
        
        # キーマッピング（サーバーと同じ）
        self.key_mapping = {
            # WASD keys
            'w': 'shoulder_lift_up',
            's': 'shoulder_lift_down', 
            'a': 'shoulder_pan_right',  # 反転: left -> right
            'd': 'shoulder_pan_left',   # 反転: right -> left
            
            # QE keys for elbow
            'q': 'elbow_flex_up',
            'e': 'elbow_flex_down',
            
            # RF keys for wrist flex
            'r': 'wrist_flex_up',
            'f': 'wrist_flex_down',
            
            # ZX keys for wrist roll
            'z': 'wrist_roll_right',    # 反転: left -> right
            'x': 'wrist_roll_left',     # 反転: right -> left
            
            # CV keys for gripper
            'c': 'gripper_close',       # 反転: open -> close
            'v': 'gripper_open',        # 反転: close -> open
        }
        
        self.pressed_keys = set()
        
    def setup_gui(self):
        """GUI セットアップ"""
        self.root = tk.Tk()
        self.root.title("SO-100 Remote Control Client")
        self.root.geometry("800x600")
        
        # 接続フレーム
        connection_frame = ttk.Frame(self.root)
        connection_frame.pack(pady=10, padx=10, fill='x')
        
        ttk.Label(connection_frame, text="Server URL:").pack(side='left')
        self.url_entry = ttk.Entry(connection_frame, width=30)
        self.url_entry.insert(0, "ws://192.168.1.100:8765")  # 例のIP
        self.url_entry.pack(side='left', padx=5)
        
        self.connect_button = ttk.Button(
            connection_frame, 
            text="Connect", 
            command=self.toggle_connection
        )
        self.connect_button.pack(side='left', padx=5)
        
        self.status_label = ttk.Label(connection_frame, text="Disconnected", foreground="red")
        self.status_label.pack(side='left', padx=10)
        
        # 制御フレーム
        control_frame = ttk.LabelFrame(self.root, text="Remote Control")
        control_frame.pack(pady=10, padx=10, fill='both', expand=True)
        
        # キーボード制御説明
        instructions = """
キーボード制御 (一部キー反転済み):
WASD: shoulder_pan/lift (A/D反転)
QE: elbow_flex  
RF: wrist_flex
ZX: wrist_roll (反転)
CV: gripper (反転)
ESC: Emergency Stop
        """
        
        ttk.Label(control_frame, text=instructions, justify='left').pack(pady=10)
        
        # 緊急停止ボタン
        emergency_frame = ttk.Frame(control_frame)
        emergency_frame.pack(pady=10)
        
        self.emergency_button = ttk.Button(
            emergency_frame,
            text="🚨 EMERGENCY STOP 🚨",
            command=self.emergency_stop,
            style='Emergency.TButton'
        )
        self.emergency_button.pack()
        
        # ステータス表示
        status_frame = ttk.LabelFrame(self.root, text="Robot Status")
        status_frame.pack(pady=10, padx=10, fill='x')
        
        # ステータステキスト
        self.status_text = tk.Text(status_frame, height=8, width=80)
        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # キーバインド
        self.root.bind('<KeyPress>', self.on_key_press)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.bind('<Escape>', lambda e: self.emergency_stop())
        
        # フォーカス設定
        self.root.focus_set()
        
        # 緊急停止ボタンのスタイル
        style = ttk.Style()
        style.configure('Emergency.TButton', foreground='red', font=('Arial', 12, 'bold'))
        
    def toggle_connection(self):
        """接続/切断を切り替え"""
        if self.connected:
            self.disconnect()
        else:
            # 接続ボタンが無効になっている場合は何もしない
            if self.connect_button.cget("state") == "disabled":
                return
            self.connect()
            
    def connect(self):
        """サーバーに接続"""
        server_url = self.url_entry.get().strip()
        
        # URL形式チェック
        if not server_url.startswith('ws://'):
            messagebox.showerror("URL Error", "Server URL must start with 'ws://'")
            return
            
        # URLが空でないかチェック
        if not server_url or server_url == 'ws://':
            messagebox.showerror("URL Error", "Please enter a valid server URL")
            return
            
        self.server_url = server_url
        
        # 接続中表示
        self.status_label.config(text="Connecting...", foreground="orange")
        self.connect_button.config(text="Connecting...", state="disabled")
        
        # WebSocket接続を別スレッドで開始
        thread = threading.Thread(target=self.run_websocket_client, daemon=True)
        thread.start()
        
    def disconnect(self):
        """サーバーから切断"""
        self.connected = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())
            
    async def websocket_client(self):
        """WebSocketクライアントメインループ"""
        error_message = None
        try:
            # タイムアウト設定（古いwebsocketsライブラリ対応）
            try:
                # 新しいバージョン用
                async with websockets.connect(
                    self.server_url, 
                    timeout=10,
                    ping_interval=20,
                    ping_timeout=10
                ) as websocket:
                    await self._handle_connection(websocket)
            except TypeError:
                # 古いバージョン用（timeoutパラメータなし）
                async with websockets.connect(self.server_url) as websocket:
                    await self._handle_connection(websocket)
                        
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Connection closed")
            error_message = "Connection was closed by server"
        except websockets.exceptions.InvalidURI:
            error_message = "Invalid server URL format"
            self.logger.error(f"Invalid URI: {self.server_url}")
        except ConnectionRefusedError:
            error_message = "Server is not running or refusing connections"
            self.logger.error("Connection refused")
        except OSError as e:
            if "timed out" in str(e).lower():
                error_message = "Connection timed out. Check server IP and network connection."
            else:
                error_message = f"Network error: {str(e)}"
            self.logger.error(f"Network error: {e}")
        except Exception as e:
            error_message = f"Connection error: {str(e)}"
            self.logger.error(f"WebSocket error: {e}")
        finally:
            self.connected = False
            self.root.after(0, lambda: [
                self.status_label.config(text="Disconnected", foreground="red"),
                self.connect_button.config(text="Connect", state="normal")
            ])
            
            # エラーメッセージを表示（変数スコープ問題を修正）
            if error_message:
                self.root.after(0, lambda msg=error_message: messagebox.showerror("Connection Error", msg))
    
    async def _handle_connection(self, websocket):
        """WebSocket接続の処理"""
        self.websocket = websocket
        self.connected = True
        
        # GUI更新
        self.root.after(0, lambda: [
            self.status_label.config(text="Connected", foreground="green"),
            self.connect_button.config(text="Disconnect", state="normal")
        ])
        
        self.logger.info(f"Connected to {self.server_url}")
        
        # コマンド送信タスクとメッセージ受信タスクを並行実行
        send_task = asyncio.create_task(self._send_commands_loop(websocket))
        receive_task = asyncio.create_task(self._receive_messages_loop(websocket))
        
        try:
            # どちらかのタスクが終了するまで待機
            await asyncio.gather(send_task, receive_task, return_exceptions=True)
        finally:
            send_task.cancel()
            receive_task.cancel()
            
    async def _send_commands_loop(self, websocket):
        """コマンド送信ループ"""
        while self.connected:
            try:
                # キューからコマンドを取得（非ブロッキング）
                if not self.command_queue.empty():
                    message = self.command_queue.get_nowait()
                    await websocket.send(message)
                else:
                    # キューが空の場合は少し待機
                    await asyncio.sleep(0.01)
            except Exception as e:
                self.logger.error(f"Error in send loop: {e}")
                break
                
    async def _receive_messages_loop(self, websocket):
        """メッセージ受信ループ"""
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    self.handle_server_message(data)
                except json.JSONDecodeError:
                    self.logger.error(f"Invalid JSON received: {message}")
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("Server connection closed")
        except Exception as e:
            self.logger.error(f"Error in receive loop: {e}")
            
    def run_websocket_client(self):
        """WebSocketクライアントを実行"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.websocket_client())
        except Exception as e:
            self.logger.error(f"WebSocket client error: {e}")
            
    def handle_server_message(self, data: Dict[str, Any]):
        """サーバーからのメッセージを処理"""
        msg_type = data.get('type')
        
        if msg_type == 'welcome':
            self.status_data = data.get('status', {})
            self.update_status_display()
            
        elif msg_type == 'status_update':
            self.status_data = data.get('data', {})
            self.update_status_display()
            
        elif msg_type == 'ack':
            # コマンド確認応答
            pass
            
    def update_status_display(self):
        """ステータス表示を更新"""
        def update():
            self.status_text.delete(1.0, tk.END)
            
            # 接続状態
            connected = self.status_data.get('connected', False)
            self.status_text.insert(tk.END, f"Robot Connected: {'Yes' if connected else 'No'}\n")
            
            # 緊急停止状態
            emergency = self.status_data.get('emergency_stop', False)
            self.status_text.insert(tk.END, f"Emergency Stop: {'ACTIVE' if emergency else 'Normal'}\n\n")
            
            # 現在位置
            positions = self.status_data.get('positions', {})
            if positions:
                self.status_text.insert(tk.END, "Current Positions:\n")
                for name, pos_list in positions.items():
                    if isinstance(pos_list, list):
                        formatted_pos = [f"{p:.1f}" for p in pos_list]
                        self.status_text.insert(tk.END, f"  {name}: [{', '.join(formatted_pos)}]\n")
                        
            # 目標位置
            targets = self.status_data.get('target_positions', {})
            if targets:
                self.status_text.insert(tk.END, "\nTarget Positions:\n")
                for name, pos_list in targets.items():
                    if isinstance(pos_list, list):
                        formatted_pos = [f"{p:.1f}" for p in pos_list]
                        self.status_text.insert(tk.END, f"  {name}: [{', '.join(formatted_pos)}]\n")
                        
            self.status_text.see(tk.END)
            
        self.root.after(0, update)
        
    def on_key_press(self, event):
        """キー押下イベント"""
        key = event.keysym.lower()
        
        if key not in self.pressed_keys and key in self.key_mapping:
            self.pressed_keys.add(key)
            self.send_command({
                'type': 'key_press',
                'key': key,
                'action': self.key_mapping[key]
            })
            
    def on_key_release(self, event):
        """キー離しイベント"""
        key = event.keysym.lower()
        
        if key in self.pressed_keys:
            self.pressed_keys.discard(key)
            self.send_command({
                'type': 'key_release', 
                'key': key,
                'action': self.key_mapping.get(key, '')
            })
            
    def emergency_stop(self):
        """緊急停止"""
        self.send_command({'type': 'emergency_stop'})
        messagebox.showwarning("Emergency Stop", "Emergency stop command sent!")
        
    def send_command(self, command: Dict[str, Any]):
        """コマンドをサーバーに送信"""
        if self.connected and self.websocket:
            try:
                message = json.dumps(command)
                # コマンドをキューに追加
                self.command_queue.put(message)
            except Exception as e:
                self.logger.error(f"Failed to queue command: {e}")
                
    def run(self):
        """クライアント実行"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            print("\nClient shutting down...")
        finally:
            if self.connected:
                self.disconnect()


def main():
    """メイン関数"""
    client = SO100RemoteClient()
    client.run()


if __name__ == "__main__":
    main()
