# SO-100 WebSocket API リファレンス

## 📡 WebSocket通信仕様

### 接続エンドポイント
```
ws://[HOST]:[PORT]
```
- **デフォルト**: `ws://localhost:8765`
- **リモート例**: `ws://192.168.1.100:8765`

---

## 📤 送信メッセージ（Client → Server）

### 1. ロボット制御コマンド

#### 基本移動コマンド
```json
{
  "type": "control",
  "command": "move",
  "direction": "forward|backward|left|right|up|down",
  "timestamp": 1234567890.123
}
```

**direction値**:
- `forward` - 前進（Y軸正方向）
- `backward` - 後退（Y軸負方向）  
- `left` - 左回転（Z軸正方向）
- `right` - 右回転（Z軸負方向）
- `up` - 上昇（Z軸正方向）
- `down` - 下降（Z軸負方向）

#### グリッパー制御
```json
{
  "type": "control", 
  "command": "gripper",
  "action": "toggle|open|close",
  "timestamp": 1234567890.123
}
```

#### 緊急停止
```json
{
  "type": "control",
  "command": "emergency_stop",
  "timestamp": 1234567890.123
}
```

#### 位置指定移動
```json
{
  "type": "control",
  "command": "move_to_position",
  "position": {
    "x": 100.0,
    "y": 200.0,
    "z": 150.0,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 45.0
  },
  "timestamp": 1234567890.123
}
```

### 2. システムコマンド

#### 状態要求
```json
{
  "type": "request",
  "command": "status",
  "timestamp": 1234567890.123
}
```

#### 設定要求
```json
{
  "type": "request", 
  "command": "config",
  "timestamp": 1234567890.123
}
```

#### Ping（接続確認）
```json
{
  "type": "ping",
  "timestamp": 1234567890.123
}
```

---

## 📥 受信メッセージ（Server → Client）

### 1. 接続応答

#### ウェルカムメッセージ
```json
{
  "type": "welcome",
  "message": "Connected to SO-100 WebSocket Server",
  "server_version": "1.0.0",
  "robot_type": "so100",
  "com_port": "COM3",
  "capabilities": ["control", "status", "emergency_stop"],
  "timestamp": 1234567890.123
}
```

### 2. ロボット状態

#### リアルタイム状態更新
```json
{
  "type": "status",
  "robot_connected": true,
  "current_positions": {
    "main": [0.0, 45.0, -30.0, 0.0, 75.0, 0.0]
  },
  "target_positions": {
    "main": [5.0, 45.0, -30.0, 0.0, 75.0, 0.0]  
  },
  "joint_names": ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"],
  "gripper_state": "open|closed",
  "safety_status": "normal|warning|error",
  "timestamp": 1234567890.123
}
```

#### エラー状態
```json
{
  "type": "error",
  "error_code": "COM_PORT_ERROR|ROBOT_DISCONNECTED|SAFETY_VIOLATION",
  "message": "Human readable error message",
  "details": {
    "com_port": "COM3",
    "last_error": "Port is in use"
  },
  "timestamp": 1234567890.123
}
```

### 3. コマンド応答

#### 成功応答
```json
{
  "type": "response",
  "command": "move",
  "status": "success",
  "message": "Movement command executed",
  "timestamp": 1234567890.123
}
```

#### エラー応答  
```json
{
  "type": "response",
  "command": "move",
  "status": "error", 
  "error": "SAFETY_LIMIT_EXCEEDED",
  "message": "Target position exceeds safety limits",
  "timestamp": 1234567890.123
}
```

### 4. システム応答

#### Pong（Ping応答）
```json
{
  "type": "pong",
  "timestamp": 1234567890.123
}
```

#### 設定情報
```json
{
  "type": "config",
  "robot_config": {
    "type": "so100",
    "dof": 6,
    "com_port": "COM3",
    "fps": 30,
    "safety_limits_enabled": true
  },
  "server_config": {
    "host": "0.0.0.0",
    "port": 8765,
    "max_connections": 5
  },
  "timestamp": 1234567890.123
}
```

---

## 🔄 通信フロー

### 基本的な通信シーケンス

```
Client                           Server
  |                                |
  |---- WebSocket接続要求 -------->|
  |<-------- welcome -------------|
  |                                |
  |---- control command --------->|
  |<-------- response ------------|
  |                                |
  |<---- status (定期送信) -------|
  |                                |
  |---- ping ------------------>|
  |<---- pong -------------------|
  |                                |
  |---- emergency_stop ---------->|
  |<-------- response ------------|
```

### エラーハンドリング

```
Client                           Server
  |                                |
  |---- invalid command --------->|
  |<-------- error response ------|
  |                                |
  |                                | (ロボット切断)
  |<-------- error status -------|
  |                                |
  |---- reconnect attempt ------->|
  |<-------- welcome (再接続) ----|
```

---

## 🛡️ セキュリティとエラーハンドリング

### エラーコード一覧

| エラーコード | 説明 | 対処法 |
|--------------|------|--------|
| `COM_PORT_ERROR` | COMポート接続エラー | ポート設定確認、ケーブル確認 |
| `ROBOT_DISCONNECTED` | ロボット切断 | 電源、USB接続確認 |
| `SAFETY_VIOLATION` | 安全制限違反 | 目標位置を安全範囲内に調整 |
| `INVALID_COMMAND` | 無効なコマンド | コマンド形式確認 |
| `JSON_PARSE_ERROR` | JSON解析エラー | メッセージ形式確認 |
| `MOTOR_ERROR` | モーターエラー | モーター状態確認、再起動 |

### 安全機能

1. **位置制限**: 各関節の動作範囲制限
2. **速度制限**: 最大速度・加速度制限
3. **緊急停止**: Escキーまたはemergency_stopコマンド
4. **接続監視**: ハートビート、タイムアウト検出
5. **エラー復旧**: 自動再接続、状態復旧

---

## 🧪 テスト用コマンド

### WebSocket接続テスト
```bash
# curl使用（Linux/WSL）
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" http://localhost:8765

# PowerShell使用（Windows）
Test-NetConnection localhost -Port 8765
```

### メッセージ送信テスト（Python）
```python
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # Ping送信
        await websocket.send(json.dumps({
            "type": "ping",
            "timestamp": time.time()
        }))
        
        # 応答受信
        response = await websocket.recv()
        print(f"Received: {response}")

asyncio.run(test_websocket())
```

### ロボット制御テスト
```python
import asyncio
import websockets
import json
import time

async def test_robot_control():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        # 前進コマンド
        await websocket.send(json.dumps({
            "type": "control",
            "command": "move", 
            "direction": "forward",
            "timestamp": time.time()
        }))
        
        response = await websocket.recv()
        print(f"Move response: {response}")
        
        # 状態要求
        await websocket.send(json.dumps({
            "type": "request",
            "command": "status",
            "timestamp": time.time()
        }))
        
        status = await websocket.recv()
        print(f"Status: {status}")

asyncio.run(test_robot_control())
```

---

## 📚 実装例

### 簡単なWebSocketクライアント
```python
import asyncio
import websockets
import json
import time

class SO100Client:
    def __init__(self, uri):
        self.uri = uri
        self.websocket = None
    
    async def connect(self):
        self.websocket = await websockets.connect(self.uri)
        welcome = await self.websocket.recv()
        print(f"Connected: {welcome}")
    
    async def move_forward(self):
        command = {
            "type": "control",
            "command": "move",
            "direction": "forward", 
            "timestamp": time.time()
        }
        await self.websocket.send(json.dumps(command))
        response = await self.websocket.recv()
        return json.loads(response)
    
    async def get_status(self):
        request = {
            "type": "request",
            "command": "status",
            "timestamp": time.time()
        }
        await self.websocket.send(json.dumps(request))
        status = await self.websocket.recv()
        return json.loads(status)
    
    async def emergency_stop(self):
        command = {
            "type": "control", 
            "command": "emergency_stop",
            "timestamp": time.time()
        }
        await self.websocket.send(json.dumps(command))

# 使用例
async def main():
    client = SO100Client("ws://localhost:8765")
    await client.connect()
    
    # 前進
    result = await client.move_forward()
    print(f"Move result: {result}")
    
    # 状態確認
    status = await client.get_status()
    print(f"Robot status: {status}")

asyncio.run(main())
```

この API リファレンスを使用して、SO-100 WebSocket システムとの通信を実装してください！
