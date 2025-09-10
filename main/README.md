# SO-100 Robot Control System

SO-100ロボット用の対話型制御・学習システム

## 必要な環境

1. **Conda環境の作成**
```bash
conda create -n lerobot python=3.10
conda activate lerobot
```

2. **依存関係のインストール**
```bash
pip install lerobot
pip install websockets
pip install opencv-python
pip install pyserial
```

- ✅ **Windows最適化**: Windows 10/11で完全動作確認済み
- 🎮 **直感的操作**: WASDキーによるリアルタイム制御
- 🌐 **ネットワーク対応**: LAN経由でのリモート操作
- 🔧 **簡単セットアップ**: 自動化されたインストールスクリプト
- 📊 **リアルタイム監視**: ロボット状態のライブ表示
- 🛡️ **安全機能**: 緊急停止、安全制限、エラー処理
- 🎯 **対話型マネージャー**: 全機能を統合した使いやすいメニューシステム
- 🧠 **学習機能**: データ収集・学習・評価のワンストップ操作
- 📷 **カメラ統合**: キャリブレーション・録画・解析機能
- 🔍 **診断機能**: 自動問題検出・解決支援

## ⚡ クイックスタート

### 🚀 自動セットアップ（推奨）
```cmd
# 完全自動セットアップ・診断・起動
quick_start.bat
```

### 📋 ステップバイステップ

#### 1. 基本セットアップ
```cmd
setup-windows.bat
```

#### 2. 対話型マネージャー起動
```cmd
start_manager.bat
# または
start_manager.ps1  # PowerShell版
```

#### 3. 個別起動（上級者向け）
```cmd
# サーバーのみ
start_server.bat

# クライアントのみ  
start_client.bat
```

## 📋 必要環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11 (64-bit) |
| Python | 3.10以上 |
| RAM | 4GB以上 |
| USB | 空きUSBポート（ロボット接続） |
| ネットワーク | WiFi/Ethernet（リモート操作時） |

## 🎮 対話型マネージャー

**SO-100 Manager** は全機能を統合した対話型システムです：

### 📋 基本操作
- **環境チェック**: システム状態の自動診断
- **自動セットアップ**: 依存関係とロボット設定の自動インストール
- **ロボット診断**: 接続・モーター・通信の包括的テスト

### 🎮 制御モード
- **キーボード制御**: WASDキーでのリアルタイム操作
- **WebSocket制御**: ネットワーク経由のリモート操作
- **テレオペレーション**: デモンストレーション記録・再生

### 🧠 学習・評価
- **データ収集**: 自動データ記録・ラベリング
- **モデル学習**: ACT、Diffusion、TDMPCポリシーの学習
- **評価実行**: 学習済みモデルの性能評価

### 📷 カメラ機能
- **自動キャリブレーション**: チェスボードパターンによる校正
- **録画・解析**: データ収集時の映像記録

### 🔬 高度な機能
- **データセット可視化**: 収集データの詳細表示
- **ベンチマーク**: システム性能測定
- **ログ解析**: 詳細なデバッグ情報表示

## 🎮 操作方法

| キー | 動作 | 説明 |
|------|------|------|
| `W` | 前進 | アーム全体を前方に移動 |
| `S` | 後退 | アーム全体を後方に移動 |
| `A` | 左回転 | ベース軸を左に回転 |
| `D` | 右回転 | ベース軸を右に回転 |
| `Q` | 上昇 | アーム全体を上方に移動 |
| `E` | 下降 | アーム全体を下方に移動 |
| `Space` | グリッパー | グリッパーの開閉切り替え |
| `Esc` | 緊急停止 | 即座に全動作停止 |

## 📁 主要ファイル

```
SO-100/
├── 📜 README.md                    # このファイル
├── 🎮 so100_manager.py             # 🌟 対話型統合マネージャー
├── 🚀 quick_start.bat              # 完全自動セットアップ
├── 🚀 start_manager.bat            # マネージャー起動
├── � start_manager.ps1            # マネージャー起動(PS)
├── �🔧 setup-windows.bat            # 基本セットアップ
├── 🚀 start_server.bat             # サーバー起動
├── 🚀 start_client.bat             # クライアント起動
├── 🐍 websocket_control_robot.py   # WebSocket制御プログラム
├── 📋 requirements-windows.txt     # 依存関係
├── ⚙️ config-template.json         # 設定テンプレート
└── 📚 docs/                        # 詳細ドキュメント
    ├── COMMAND_REFERENCE.md        # コマンドリファレンス
    ├── WEBSOCKET_API_REFERENCE.md  # API仕様
    └── PROJECT_DOCUMENTATION.md   # 技術仕様書
```

## 🔗 リモート接続

### サーバー（ロボット側）
```cmd
start_server.bat
# -> Server running on ws://0.0.0.0:8765
```

### クライアント（操作側）
```cmd
# サーバーのIPアドレスを指定
python websocket_control_robot.py client --server-url ws://192.168.1.100:8765
```

## 🛠️ 詳細セットアップ

### 手動インストール
```cmd
# 1. 仮想環境作成
python -m venv venv
venv\Scripts\activate.bat

# 2. 依存関係インストール
pip install -r requirements-windows.txt

# 3. 設定ファイル作成
copy config-template.json config.json
notepad config.json  # COMポート設定

# 4. テスト起動
python websocket_control_robot.py server --robot.type=so100 --com-port COM3
```

### ハードウェアセットアップ
1. **SO-100 接続**: USB-Cケーブルでロボットとコンピューターを接続
2. **電源接続**: 5V/3A電源アダプターをロボットに接続
3. **COMポート確認**: デバイスマネージャーでCOM番号を確認
4. **設定更新**: `config.json`でCOMポートを設定

## 🆘 トラブルシューティング

### よくある問題

#### "Python was not found"
**解決**: [python.org](https://python.org) からPython 3.10+をインストール

#### "Port is in use"
**解決**: 
1. 他のアプリケーションがCOMポートを使用していないか確認
2. デバイスマネージャーでドライバー更新
3. USBケーブル再接続

#### GUI が表示されない
**解決**: `pip install tk` でtkinterを再インストール

### ログ確認
```cmd
# ログファイル確認
type logs\server.log

# リアルタイム監視（PowerShell）
Get-Content logs\server.log -Tail 20 -Wait
```

### 状態確認
```cmd
# プロジェクト全体の状態確認
check-status.bat

# COMポート確認
python -c "import serial.tools.list_ports; [print(port.device) for port in serial.tools.list_ports.comports()]"
```

## 🔄 更新

```cmd
git pull origin main
venv\Scripts\activate.bat
pip install -r requirements-windows.txt --upgrade
```

## 📚 詳細ドキュメント

- 📋 **[コマンドリファレンス](docs/COMMAND_REFERENCE.md)** - 全コマンドと操作方法
- 📡 **[WebSocket API仕様](docs/WEBSOCKET_API_REFERENCE.md)** - 開発者向けAPI仕様
- 🔧 **[技術仕様書](docs/PROJECT_DOCUMENTATION.md)** - 詳細な技術情報

## 🤝 貢献・サポート

- 🐛 **バグ報告**: [GitHub Issues](https://github.com/huggingface/lerobot/issues)
- 💬 **コミュニティ**: [Discord](https://discord.gg/s3KuuzsPFb)
- 📖 **LeRobot公式**: [Hugging Face LeRobot](https://huggingface.co/docs/lerobot)

## 📜 ライセンス

Apache 2.0 License - 詳細は [LICENSE](LICENSE) を参照

---

**SO-100 WebSocket Remote Control** - Windows環境でのロボット制御を簡単に 🤖✨
