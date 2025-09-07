# SO-100### 🔧 初回セットアップ##### サーバー側PC（SO-100接続PC）の環境構築
```bash
# 1. Condaのインストール確認
conda --version

# 2. LeRobot環境の作成
conda create -n lerobot python=3.10 -y
conda activate lerobot

# 3. LeRobotのインストール
pip install lerobot[robot]

# 4. WebSocket通信用ライブラリ
pip install websockets

# 5. SO-100設定確認
python -c "from lerobot.common.robot_devices.robots.so100 import SO100Robot; print('SO-100 setup OK')"
```

##### クライアント側PC（操作PC）の環境構築セットアップ（推奨）
```bash
# サーバー側PC（SO-100接続PC）
setup_server_environment.bat

# クライアント側PC（操作PC）  
setup_client_environment.bat
```

#### 🔧 手動セットアップ（上級者向け）

##### サーバー側PC（SO-100接続PC）の環境構築mote Control System

## 🎯 ローカルネットワーク簡易セットアップ

### 前提条件
- 両方のPCが同じネットワーク（WiFi/LAN）に接続されていること
- **ファイアウォール設定やポート開放は不要！**

### � 初回セットアップ（初回のみ）

#### サーバー側PC（SO-100接続PC）の環境構築
```bash
# 1. Condaのインストール確認
conda --version

# 2. LeRobot環境の作成
conda create -n lerobot python=3.10 -y
conda activate lerobot

# 3. LeRobotのインストール
pip install lerobot[robot]

# 4. WebSocket通信用ライブラリ
pip install websockets

# 5. SO-100設定確認
python -c "from lerobot.common.robot_devices.robots.so100 import SO100Robot; print('SO-100 setup OK')"
```

#### クライアント側PC（操作PC）の環境構築
```bash
# 1. Condaのインストール確認
conda --version

# 2. リモートクライアント用環境作成
conda create -n so100-remote python=3.10 -y
conda activate so100-remote

# 3. 必要なライブラリのインストール
pip install websockets tkinter
```

### �📋 簡単3ステップ

#### 1. サーバー起動（ロボット側PC）
```bash
# LeRobot環境をアクティベート
conda activate lerobot

# サーバー起動
```bash
# サーバー起動
cd main
python remote_control_server.py
```

起動時に表示される情報をメモ：
```
🌐 Local Network IP: 192.168.1.100:8765
📱 Client URL: ws://192.168.1.100:8765
```

#### 2. クライアント起動（操作側PC）
```bash
# リモートクライアント環境をアクティベート
conda activate so100-remote

# クライアント起動
```bash
# クライアント起動
cd main
python remote_control_client.py
```

#### 3. 接続
1. クライアントのServer URLフィールドに、サーバーが表示したClient URLを入力
2. 「Connect」ボタンをクリック
3. 「Connected」と表示されたら完了！

## 🎮 操作方法（キー反転済み）

### 基本操作
- **WASD**: Shoulder制御 (A/D反転)
  - W: Shoulder Lift Up
  - S: Shoulder Lift Down  
  - A: Shoulder Pan Right (反転)
  - D: Shoulder Pan Left (反転)

- **QE**: Elbow制御
  - Q: Elbow Flex Up
  - E: Elbow Flex Down

- **RF**: Wrist Flex制御
  - R: Wrist Flex Up
  - F: Wrist Flex Down

- **ZX**: Wrist Roll制御（反転）
  - Z: Wrist Roll Right (反転)
  - X: Wrist Roll Left (反転)

- **CV**: Gripper制御（反転）
  - C: Gripper Close (反転)
  - V: Gripper Open (反転)

### 安全機能
- **ESC**: 緊急停止（全モーター停止）

## 🔧 トラブルシューティング

### 環境関連のエラー
```bash
# Conda環境が見つからない場合
conda info --envs

# LeRobot環境の再作成
conda remove -n lerobot --all -y
conda create -n lerobot python=3.10 -y
conda activate lerobot
pip install lerobot[robot] websockets

# SO-100接続テスト
python -c "from lerobot.common.robot_devices.robots.so100 import SO100Robot; robot = SO100Robot(); print('Connection OK')"
```

### 接続できない場合
1. 両方のPCが同じネットワークに接続されているか確認
2. サーバーのIPアドレスが正しいか確認
3. ウイルス対策ソフトがブロックしていないか確認

### 動作が遅い場合
- WiFiの電波強度を確認
- 有線LAN接続を推奨

### エラーが出る場合
1. サーバーを再起動
2. 管理者権限でコマンドプロンプトを実行
3. Pythonライブラリの再インストール：
   ```bash
   pip install websockets asyncio
   ```

---

## 📚 詳細セットアップ（上級者向け）

### システム構成

#### サーバー側（SO-100が接続されているパソコン）
- `remote_control_server.py`: WebSocketサーバー
- SO-100ロボットアームが物理的に接続されている
- LeRobotライブラリが必要

#### クライアント側（操作用パソコン）
- `remote_control_client.py`: GUIクライアント
- ネットワーク経由でサーバーに接続
- キーボード操作でロボットを制御

### 依存関係のインストール

#### サーバー側（完全なセットアップ）
```bash
# Conda環境作成とアクティベート
conda create -n lerobot python=3.10 -y
conda activate lerobot

# LeRobotの完全インストール
pip install lerobot[robot]

# 追加の通信ライブラリ
pip install websockets

# インストール確認
python -c "import lerobot; print(f'LeRobot version: {lerobot.__version__}')"
python -c "from lerobot.common.robot_devices.robots.so100 import SO100Robot; print('SO-100 support OK')"
```

#### クライアント側（軽量セットアップ）
```bash
# 軽量なリモートクライアント環境
conda create -n so100-remote python=3.10 -y
conda activate so100-remote

# 最小限のライブラリのみ
pip install websockets
```

#### ワンライナーセットアップ（上級者向け）
```bash
# サーバー側
conda create -n lerobot python=3.10 -y && conda activate lerobot && pip install lerobot[robot] websockets

# クライアント側  
conda create -n so100-remote python=3.10 -y && conda activate so100-remote && pip install websockets
```

### ステータス表示

クライアントGUIに以下の情報がリアルタイム表示されます：

- **Robot Connected**: ロボット接続状態
- **Emergency Stop**: 緊急停止状態  
- **Current Positions**: 現在の関節角度
- **Target Positions**: 目標関節角度

### カスタマイズ

#### キーマッピング変更
`remote_control_client.py` の `key_mapping` 辞書を編集：

```python
self.key_mapping = {
    'w': 'shoulder_lift_up',
    # 他のキーマッピング...
}
```

#### 通信ポート変更
サーバー・クライアント両方で同じポート番号に変更：

```python
# サーバー側
SO100RemoteServer(host='127.0.0.1', port=9999)

# クライアント側
self.server_url = "ws://localhost:9999"
```

### セキュリティ注意事項

- ローカルネットワーク内でのみ使用（ファイアウォール設定不要）
- パスワード認証等は実装されていない
- 信頼できるネットワーク内でのみ使用してください
