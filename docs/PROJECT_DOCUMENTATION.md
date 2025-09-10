# SO-100 WebSocketリモートコントロール プロジェクト全体ドキュメント

## 目次
1. [プロジェクト概要](#プロジェクト概要)
2. [システム構成](#システム構成)
3. [主要コンポーネント](#主要コンポーネント)
4. [技術仕様](#技術仕様)
5. [インストール・セットアップ](#インストールセットアップ)
6. [使用方法](#使用方法)
7. [コマンドリファレンス](#コマンドリファレンス)
8. [ソフトウェア開発](#ソフトウェア開発)
9. [ハードウェア仕様](#ハードウェア仕様)
10. [トラブルシューティング](#トラブルシューティング)
11. [開発履歴](#開発履歴)
12. [今後の展望](#今後の展望)

## プロジェクト概要

このプロジェクトは、Hugging FaceのLeRobotライブラリを基盤として、SO-100ロボットアームのためのWebSocket ベースのリモートコントロールシステムです。

### 主な目的
- **リアルタイム制御**: WebSocketを使った低遅延のロボット制御
- **遠隔操作**: ネットワーク経由でのロボット操作
- **視覚的インターフェース**: GUI付きクライアントによる直感的な操作
- **オープンソース**: LeRobotエコシステムとの完全統合

### プロジェクトの特徴
- 🤖 **SO-100/SO-101 ロボットアーム対応**: Feetech STS3215サーボモーター対応
- 🌐 **WebSocket通信**: リアルタイム双方向通信
- 🎮 **キーボード制御**: WASDキーによる直感的操作
- 📊 **リアルタイム監視**: 位置情報、状態データのライブ表示
- 🔧 **LeRobot統合**: Hugging Face LeRobotライブラリとの完全互換
- 🛡️ **安全機能**: 緊急停止、安全制限、エラー処理

## システム構成

### アーキテクチャ図
```
┌─────────────────┐    WebSocket     ┌─────────────────┐
│                 │    (ws://...)    │                 │
│  Client GUI     │ ←──────────────→ │  Server Robot   │
│  (Tkinter)      │                  │  (LeRobot)      │
│                 │                  │                 │
└─────────────────┘                  └─────────────────┘
       ↑                                       ↓
       │                                       │
┌─────────────────┐                  ┌─────────────────┐
│ キーボード入力    │                  │ SO-100 Robot    │
│ (WASD制御)      │                  │ (USB/COM)       │
└─────────────────┘                  └─────────────────┘
```

### コンポーネント間の関係
1. **Client (GUI)**: ユーザーインターフェース、キーボード入力
2. **WebSocket Server**: ロボット制御、LeRobot統合
3. **Robot Hardware**: SO-100アーム、Feetechモーター
4. **Communication Layer**: WebSocket + asyncio

## 主要コンポーネント

### 1. WebSocketサーバー (`SO100WebSocketServer`)
- **役割**: ロボット制御の中心
- **機能**:
  - LeRobotライブラリとの統合
  - モーター制御とステータス監視
  - 非同期WebSocket通信
  - 安全機能とエラー処理

### 2. WebSocketクライアント (`SO100WebSocketClient`)
- **役割**: ユーザーインターフェース
- **機能**:
  - TkinterベースのGUI
  - キーボード入力処理
  - リアルタイムデータ表示
  - サーバーとの通信管理

### 3. LeRobot統合層
- **設定管理**: `So100RobotConfig`
- **モーター制御**: `FeetechMotorsBusConfig`
- **ロボット管理**: `ManipulatorRobot`

## 技術仕様

### プログラミング言語・フレームワーク
- **Python 3.10+**: メインプログラミング言語
- **asyncio**: 非同期プログラミング
- **websockets**: WebSocket通信
- **tkinter**: GUI フレームワーク
- **LeRobot**: ロボット制御ライブラリ
- **PyTorch**: 機械学習・データ処理

### 通信仕様
- **プロトコル**: WebSocket (RFC 6455)
- **データ形式**: JSON
- **認証**: なし（ローカルネットワーク前提）
- **暗号化**: なし（内部ネットワーク使用）

### ハードウェア要件
- **OS**: Windows 10/11 (主要開発環境), Linux, macOS
- **Python**: 3.10以上
- **USB Port**: モーター制御ボード接続用
- **Network**: WebSocket通信用
- **RAM**: 4GB以上推奨
- **CPU**: デュアルコア以上推奨

## インストール・セットアップ

### 1. Windows環境構築（推奨）

#### 自動セットアップ
```cmd
# バッチファイルでセットアップ
setup-windows.bat

# PowerShellでセットアップ（推奨）
.\setup-windows.ps1

# 開発環境込み
.\setup-windows.ps1 -Dev
```

#### 手動セットアップ
```cmd
# Python仮想環境作成
python -m venv venv
venv\Scripts\activate.bat

# Windows向け依存関係インストール
pip install -r requirements-windows.txt

# 開発依存関係（オプション）
pip install -r requirements-dev-windows.txt
```

### 2. Linux/macOS環境構築

```bash
# リポジトリクローン
git clone https://github.com/huggingface/lerobot.git
cd lerobot

# Python環境作成
conda create -y -n lerobot python=3.10
conda activate lerobot

# 依存関係インストール
pip install -e .
pip install websockets
```

### 3. SO-100ハードウェア設定
1. **モーター接続**: STS3215モーターをWaveShare制御ボードに接続
2. **USB接続**: 制御ボードをPCのUSBポートに接続
3. **電源接続**: 5V/3A電源アダプターを接続
4. **COMポート確認**: 
   - **Windows**: デバイスマネージャーでCOMポート番号を確認
   - **Linux**: `ls /dev/ttyUSB*` or `ls /dev/ttyACM*`

### 4. 設定ファイル作成
```json
{
  "com_port": "COM3",
  "server_host": "localhost",
  "server_port": 8765,
  "log_level": "INFO",
  "robot_type": "so100"
}
```

## 使用方法

### Windows環境での起動

#### サーバー起動（簡単）
```cmd
start_server.bat
```

#### クライアント起動（簡単）
```cmd
start_client.bat
```

### コマンドライン起動

#### サーバー起動
```cmd
# Windows
venv\Scripts\activate.bat
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 [オプション]

# Linux/macOS
source venv/bin/activate
python websocket_control_robot.py server --robot.type=so100 --com-port /dev/ttyUSB0 [オプション]
```

#### サーバー起動オプション
- `--robot.type=so100`: ロボットタイプ指定
- `--com-port COM3`: COMポート指定（Windows: COM3, Linux: /dev/ttyUSB0）
- `--host 0.0.0.0`: バインドアドレス（デフォルト: localhost）
- `--port 8765`: ポート番号（デフォルト: 8765）
- `--log-level DEBUG`: ログレベル設定

#### クライアント起動
```cmd
# Windows
venv\Scripts\activate.bat
python websocket_control_robot.py client --server-url ws://[サーバーIP]:8765

# Linux/macOS
source venv/bin/activate  
python websocket_control_robot.py client --server-url ws://[サーバーIP]:8765
```

#### クライアント使用方法
1. **接続**: サーバーURLを指定して接続
2. **キーボード制御**:
   - `W`: 前進
   - `S`: 後退
   - `A`: 左回転
   - `D`: 右回転
   - `Q`: 上昇
   - `E`: 下降
   - `Space`: グリッパー開閉
   - `Esc`: 緊急停止

## コマンドリファレンス

**📋 詳細は [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) を参照してください**

### 主要コマンド一覧

#### セットアップ
```cmd
# 自動環境構築
setup-windows.bat

# PowerShell版（高機能）
.\setup-windows.ps1 -Dev

# 状態確認
check-status.bat
```

#### 基本操作
```cmd
# サーバー起動（ロボット制御）
start_server.bat
# または
python websocket_control_robot.py server --robot.type=so100 --com-port COM3

# クライアント起動（操作UI）
start_client.bat
# または  
python websocket_control_robot.py client --server-url ws://localhost:8765
```

#### キーボード制御
| キー | 動作 | 説明 |
|------|------|------|
| `W/S` | 前進/後退 | Y軸方向移動 |
| `A/D` | 左/右回転 | Z軸回転 |
| `Q/E` | 上昇/下降 | Z軸方向移動 |
| `Space` | グリッパー | 開閉切り替え |
| `Esc` | 緊急停止 | 全動作停止 |

#### トラブルシューティング
```cmd
# COMポート確認
python -c "import serial.tools.list_ports; [print(port.device) for port in serial.tools.list_ports.comports()]"

# ログ確認
type logs\server.log

# 依存関係更新
pip install -r requirements-windows.txt --upgrade
```

### 使用シナリオ

#### 初回セットアップ
1. `setup-windows.bat` - 環境構築
2. `check-status.bat` - 状態確認
3. `notepad config.json` - 設定調整
4. `start_server.bat` - テスト起動

#### 日常使用
1. `start_server.bat` - サーバー起動
2. `start_client.bat` - クライアント起動
3. キーボードでロボット操作
4. `Ctrl+C` / `Alt+F4` - 終了

#### リモート操作
```cmd
# サーバー側（ロボット接続PC）
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 --host 0.0.0.0

# クライアント側（操作用PC）  
python websocket_control_robot.py client --server-url ws://192.168.1.100:8765
```

## ソフトウェア開発

### ファイル構成
```
main/
├── websocket_control_robot.py    # メインプログラム
├── PROJECT_DOCUMENTATION.md      # このドキュメント
├── kankyo.md                     # 環境設定メモ
└── [その他のファイル]

lerobot/
├── configs/                      # 設定ファイル
├── common/
│   ├── robot_devices/           # ロボットデバイス
│   ├── policies/                # 制御ポリシー
│   └── utils/                   # ユーティリティ
└── scripts/                     # 実行スクリプト
```

### 主要クラス

#### `SO100WebSocketServer`
```python
class SO100WebSocketServer:
    def __init__(self, config):
        self.robot = None
        self.robot_connected = False
        self.serial_lock = threading.Lock()  # シリアル通信排他制御
        
    async def start_server(self):
        # WebSocketサーバー開始
        
    def _control_loop(self):
        # ロボット制御ループ（ヘッドレスモード）
        
    def _update_robot_status(self):
        # ロボット状態更新（頻度制限付き）
```

#### `SO100WebSocketClient`
```python
class SO100WebSocketClient:
    def __init__(self):
        self.websocket = None
        self.running = True
        
    async def connect_to_server(self, uri):
        # サーバー接続
        
    def setup_gui(self):
        # Tkinter GUI セットアップ
        
    def handle_keypress(self, event):
        # キーボード入力処理
```

### 重要な実装ポイント

#### 1. シリアル通信の排他制御
```python
# COM ポートアクセス競合を防ぐ
with self.serial_lock:
    current_positions = self.robot._read_current_positions()
    self.robot._send_goal_positions(goal_positions)
```

#### 2. 非同期処理とGUI統合
```python
# Tkinter メインループでasyncio実行
def run_async_in_tk(self, coroutine):
    future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
    return future.result()
```

#### 3. エラー処理とロバストネス
```python
try:
    # ロボット操作
    pass
except Exception as e:
    if "Port is in use" in str(e):
        self.logger.debug(f"Serial port busy: {e}")
    else:
        self.logger.error(f"Unexpected error: {e}")
```

## ハードウェア仕様

### SO-100/SO-101 ロボットアーム
- **DoF (自由度)**: 6軸
- **モーター**: Feetech STS3215 サーボモーター
- **制御方式**: シリアル通信 (UART)
- **電源**: 5V/3A DC アダプター
- **通信**: USB経由（WaveShare制御ボード）

### モーター仕様
- **型番**: STS3215
- **電圧**: 7.4V
- **トルク**: 16.5kg·cm (6V時)
- **ギア比**: 1/345 (C001), 1/191 (C044), 1/147 (C046)
- **通信**: シリアル (UART, TTL)

### 制御ボード
- **製造元**: WaveShare
- **インターフェース**: USB-C
- **機能**: UART-USB変換、モーター電源管理
- **対応OS**: Windows, Linux, macOS

## トラブルシューティング

### よくある問題と解決方法

#### 1. "Port is in use" エラー
**症状**: シリアルポートへの同時アクセスエラー
**原因**: 複数スレッドがCOMポートに同時アクセス
**解決方法**:
```python
# シリアルロックの実装
self.serial_lock = threading.Lock()
with self.serial_lock:
    # シリアル通信処理
```

#### 2. WebSocket接続エラー
**症状**: クライアントがサーバーに接続できない
**原因**: ファイアウォール、ポート設定、ネットワーク問題
**解決方法**:
1. ファイアウォール設定確認
2. ポート番号確認 (デフォルト: 8765)
3. IPアドレス確認

#### 3. ロボット初期化失敗
**症状**: ロボットが認識されない、モーターが応答しない
**原因**: COMポート設定、ケーブル接続、電源問題
**解決方法**:
1. デバイスマネージャーでCOMポート確認
2. USBケーブル・電源ケーブル確認
3. モーターIDとボーレート確認

#### 4. GUI応答なし
**症状**: Tkinter GUI がフリーズ
**原因**: メインスレッドでのブロッキング処理
**解決方法**:
```python
# 非同期処理をTkinterで実行
asyncio.run_coroutine_threadsafe(async_function(), self.loop)
```

### デバッグ手順
1. **ログレベル設定**: `--log-level DEBUG`
2. **COMポート確認**: デバイスマネージャー
3. **ネットワーク確認**: ping, telnet テスト
4. **モーター確認**: Feetech 公式ソフトウェア

## 開発履歴

### フェーズ1: 基本制御システム (初期開発)
- 基本的なキーボード制御実装
- LeRobot ライブラリ統合
- 単体動作テスト

### フェーズ2: リモート制御システム (WebSocket実装)
- WebSocket サーバー・クライアント開発
- 非同期通信実装
- GUI クライアント開発

### フェーズ3: システム統合・安定化 (現在)
- シリアル通信排他制御実装
- エラー処理強化
- パフォーマンス最適化

### 主要な技術的課題と解決
1. **COM ポート競合**: threading.Lock() による排他制御
2. **asyncio-Tkinter 統合**: run_coroutine_threadsafe() 使用
3. **リアルタイム性**: 制御ループとステータス更新の分離
4. **エラー処理**: 段階的エラーハンドリング実装

## 今後の展望

### 短期計画 (1-3ヶ月)
- [ ] 完全なシリアル通信同期化
- [ ] パフォーマンスチューニング
- [ ] 追加センサー統合 (カメラ、力覚センサー)
- [ ] ユーザーマニュアル充実

### 中期計画 (3-6ヶ月)
- [ ] 機械学習ポリシー統合
- [ ] 軌道計画機能
- [ ] マルチロボット対応
- [ ] Web ベース UI 開発

### 長期計画 (6ヶ月以上)
- [ ] ROS2 統合
- [ ] クラウド連携
- [ ] AI ベース自律動作
- [ ] 商用レベル品質向上

### 貢献方法
1. **Issue 報告**: GitHub でバグ報告・機能要望
2. **Pull Request**: コード改善・新機能追加
3. **ドキュメント**: 使用例・チュートリアル作成
4. **テスト**: 異なる環境でのテスト・フィードバック

## ライセンス・謝辞

### ライセンス
- **LeRobot**: Apache 2.0 License
- **このプロジェクト**: MIT License (予定)

### 謝辞
- **Hugging Face**: LeRobot ライブラリ提供
- **RobotStudio**: SO-100/SO-101 ハードウェア設計
- **Feetech**: STS3215 サーボモーター
- **オープンソースコミュニティ**: 継続的な改善・サポート

---

**最終更新**: 2025年1月9日  
**プロジェクト責任者**: [Your Name]  
**連絡先**: [Contact Information]  
**リポジトリ**: [GitHub Repository URL]  

このドキュメントは継続的に更新されます。最新版は常にプロジェクトリポジトリで確認してください。
