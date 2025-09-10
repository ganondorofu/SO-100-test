# SO-100 WebSocket Remote Control - コマンドリファレンス

## 📋 目次
1. [セットアップコマンド](#セットアップコマンド)
2. [サーバーコマンド](#サーバーコマンド)
3. [クライアントコマンド](#クライアントコマンド)
4. [メンテナンスコマンド](#メンテナンスコマンド)
5. [開発者コマンド](#開発者コマンド)
6. [キーボード操作](#キーボード操作)
7. [トラブルシューティングコマンド](#トラブルシューティングコマンド)

---

## セットアップコマンド

### 🔧 初回環境構築

#### バッチファイル（推奨）
```cmd
setup-windows.bat
```
**動作**: 
- Python仮想環境作成
- 依存関係の自動インストール
- COMポート検出
- 設定ファイル作成

#### PowerShell版（高機能）
```powershell
# 基本セットアップ
.\setup-windows.ps1

# 開発環境込み
.\setup-windows.ps1 -Dev

# COMポート指定
.\setup-windows.ps1 -ComPort "COM5"

# ハードウェアチェックスキップ
.\setup-windows.ps1 -SkipHardwareCheck
```
**動作**:
- PowerShell実行ポリシーチェック
- システム情報詳細確認
- 開発ツール自動インストール
- Windows固有の最適化設定

#### 手動セットアップ
```cmd
# 仮想環境作成
python -m venv venv

# 仮想環境アクティベート
venv\Scripts\activate.bat

# 依存関係インストール
pip install -r requirements-windows.txt

# 開発依存関係（オプション）
pip install -r requirements-dev-windows.txt
```

---

## サーバーコマンド

### 🤖 ロボット制御サーバー起動

#### 簡単起動
```cmd
start_server.bat
```
**動作**:
- 対話式COMポート選択
- 自動設定読み込み
- WebSocketサーバー起動
- ロボット初期化・接続

#### 完全コマンドライン
```cmd
python websocket_control_robot.py server [オプション]
```

#### 主要オプション
| オプション | デフォルト | 説明 | 例 |
|------------|------------|------|-----|
| `--robot.type` | so100 | ロボットタイプ | `--robot.type=so100` |
| `--com-port` | COM3 | COMポート | `--com-port COM5` |
| `--host` | localhost | バインドアドレス | `--host 0.0.0.0` |
| `--port` | 8765 | ポート番号 | `--port 9000` |
| `--log-level` | INFO | ログレベル | `--log-level DEBUG` |

#### 使用例
```cmd
# 基本起動
python websocket_control_robot.py server --robot.type=so100 --com-port COM3

# デバッグモード
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 --log-level DEBUG

# 外部接続許可
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 --host 0.0.0.0

# カスタムポート
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 --port 9000
```

**動作内容**:
1. 設定ファイル読み込み
2. COMポート接続テスト
3. モーター初期化
4. WebSocketサーバー開始
5. クライアント接続待機
6. リアルタイム制御ループ実行

---

## クライアントコマンド

### 🎮 操作クライアント起動

#### 簡単起動
```cmd
start_client.bat
```
**動作**:
- 対話式サーバーURL入力
- GUI ウィンドウ表示
- WebSocket接続確立
- キーボード操作有効化

#### 完全コマンドライン
```cmd
python websocket_control_robot.py client --server-url ws://[HOST]:[PORT]
```

#### 接続例
```cmd
# ローカル接続
python websocket_control_robot.py client --server-url ws://localhost:8765

# リモート接続
python websocket_control_robot.py client --server-url ws://192.168.1.100:8765

# カスタムポート
python websocket_control_robot.py client --server-url ws://10.0.20.109:9000
```

**動作内容**:
1. サーバー接続確立
2. Tkinter GUI 起動
3. リアルタイムデータ受信開始
4. キーボード入力監視開始
5. ロボット状態表示更新

---

## メンテナンスコマンド

### 🔍 状態確認
```cmd
check-status.bat
```
**動作**:
- Python環境チェック
- 仮想環境確認
- 依存関係状況
- 設定ファイル検証
- COMポート検出
- ネットワーク状態
- 総合判定・推奨事項表示

### 📦 依存関係管理
```cmd
# 仮想環境アクティベート
venv\Scripts\activate.bat

# パッケージ一覧表示
pip list

# パッケージ更新
pip install -r requirements-windows.txt --upgrade

# 特定パッケージ更新
pip install websockets --upgrade

# 開発依存関係更新
pip install -r requirements-dev-windows.txt --upgrade
```

### 🔧 設定管理
```cmd
# 設定テンプレートから設定作成
copy config-template.json config.json

# 設定ファイル確認
type config.json

# 設定ファイル編集
notepad config.json
```

---

## 開発者コマンド

### 🧪 テスト実行
```cmd
# 仮想環境アクティベート
venv\Scripts\activate.bat

# 全テスト実行
pytest

# 特定テストファイル
pytest tests/test_websocket.py

# カバレッジ付きテスト
pytest --cov=websocket_control_robot tests/

# 詳細出力
pytest -v -s
```

### 🔍 コード品質チェック
```cmd
# フォーマットチェック
black --check websocket_control_robot.py

# フォーマット適用
black websocket_control_robot.py

# リントチェック
flake8 websocket_control_robot.py

# 型チェック
mypy websocket_control_robot.py

# セキュリティチェック
bandit websocket_control_robot.py
```

### 📊 プロファイリング
```cmd
# メモリプロファイル
python -m memory_profiler websocket_control_robot.py

# 実行時間プロファイル
python -m cProfile -o profile.stats websocket_control_robot.py server --robot.type=so100 --com-port COM3

# プロファイル結果表示
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(10)"
```

---

## キーボード操作

### 🎮 基本制御

| キー | 動作 | 詳細説明 |
|------|------|----------|
| `W` | 前進 | Y軸正方向（前方）への移動 |
| `S` | 後退 | Y軸負方向（後方）への移動 |
| `A` | 左回転 | Z軸正方向（左）への回転 |
| `D` | 右回転 | Z軸負方向（右）への回転 |
| `Q` | 上昇 | Z軸正方向（上方）への移動 |
| `E` | 下降 | Z軸負方向（下方）への移動 |
| `Space` | グリッパー | グリッパーの開閉切り替え |
| `Esc` | 緊急停止 | 全モーター即座停止 |

### ⚙️ システム操作

| 操作 | 動作 | 説明 |
|------|------|------|
| `Alt + F4` | クライアント終了 | GUIウィンドウを閉じる |
| `Ctrl + C` | サーバー停止 | コンソールでサーバー停止 |
| `F5` | 再接続 | WebSocket接続リトライ |
| `F1` | ヘルプ表示 | 操作ガイド表示 |

---

## トラブルシューティングコマンド

### 🔌 COMポート問題
```cmd
# COMポート一覧表示
python -c "import serial.tools.list_ports; [print(f'{port.device} - {port.description}') for port in serial.tools.list_ports.comports()]"

# 特定COMポートテスト
python -c "import serial; s=serial.Serial('COM3', 1000000, timeout=1); print('OK'); s.close()"

# デバイスマネージャー起動
devmgmt.msc
```

### 🌐 ネットワーク問題
```cmd
# ローカルIP確認
ipconfig

# ポート使用状況確認
netstat -an | findstr :8765

# ファイアウォール確認
netsh advfirewall show allprofiles

# Ping テスト
ping 192.168.1.100

# WebSocket接続テスト
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" http://localhost:8765
```

### 🐍 Python環境問題
```cmd
# Python バージョン確認
python --version

# pip バージョン確認
pip --version

# インストール済みパッケージ確認
pip list | findstr websockets
pip list | findstr torch

# パッケージ依存関係確認
pip show websockets

# 壊れたパッケージ修復
pip install --force-reinstall websockets
```

### 💾 ログ確認
```cmd
# サーバーログ確認
type logs\server.log

# エラーログ抽出
findstr "ERROR" logs\server.log

# 最新ログ表示（PowerShell）
Get-Content logs\server.log -Tail 20 -Wait

# ログファイル削除（リセット）
del logs\*.log
```

### 🔄 システムリセット
```cmd
# 仮想環境完全削除・再構築
rmdir /s venv
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements-windows.txt

# 設定ファイルリセット
del config.json
copy config-template.json config.json

# ログ削除
rmdir /s logs
mkdir logs
```

---

## 🚀 使用シナリオ別コマンド

### シナリオ1: 初回セットアップ
```cmd
# 1. 自動セットアップ実行
setup-windows.bat

# 2. 状態確認
check-status.bat

# 3. 設定調整
notepad config.json

# 4. テスト起動
start_server.bat
```

### シナリオ2: 日常的な使用
```cmd
# 1. サーバー起動
start_server.bat

# 2. クライアント起動（別ウィンドウ）
start_client.bat

# 3. 操作終了後
# Ctrl+C でサーバー停止
# Alt+F4 でクライアント終了
```

### シナリオ3: リモート操作
```cmd
# サーバー側（ロボット接続PC）
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 --host 0.0.0.0

# クライアント側（操作用PC）
python websocket_control_robot.py client --server-url ws://192.168.1.100:8765
```

### シナリオ4: 開発・デバッグ
```cmd
# 1. 開発環境セットアップ
setup-windows.ps1 -Dev

# 2. デバッグモードでサーバー起動
python websocket_control_robot.py server --robot.type=so100 --com-port COM3 --log-level DEBUG

# 3. テスト実行
pytest tests/

# 4. コード品質チェック
black websocket_control_robot.py
flake8 websocket_control_robot.py
```

---

## 📖 コマンドクイックリファレンス

| 目的 | コマンド |
|------|----------|
| **初回セットアップ** | `setup-windows.bat` |
| **状態確認** | `check-status.bat` |
| **サーバー起動** | `start_server.bat` |
| **クライアント起動** | `start_client.bat` |
| **COMポート確認** | `python -c "import serial.tools.list_ports; [print(port.device) for port in serial.tools.list_ports.comports()]"` |
| **依存関係更新** | `pip install -r requirements-windows.txt --upgrade` |
| **ログ確認** | `type logs\server.log` |
| **設定編集** | `notepad config.json` |
| **テスト実行** | `pytest` |
| **緊急停止** | `Ctrl+C` (サーバー), `Esc` (クライアント) |

このリファレンスを使って、SO-100 WebSocket Remote Controlシステムを効率的に操作してください！
