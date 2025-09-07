# SO-100 Remote Control System

別のパソコンからSO-100ロボットアームをリモート操作するためのシステムです。

## システム構成

### サーバー側（SO-100が接続されているパソコン）
- `remote_control_server.py`: WebSocketサーバー
- SO-100ロボットアームが物理的に接続されている
- LeRobotライブラリが必要

### クライアント側（操作用パソコン）
- `remote_control_client.py`: GUIクライアント
- ネットワーク経由でサーバーに接続
- キーボード操作でロボットを制御

## セットアップ手順

### 1. 依存関係のインストール

#### サーバー側
```bash
# LeRobotの環境が既にセットアップされている場合
pip install websockets

# 新規セットアップの場合
pip install -r remote_requirements.txt
```

#### クライアント側  
```bash
pip install -r remote_requirements.txt
```

### 2. ネットワーク設定

#### サーバー側（SO-100接続PC）
1. IPアドレスを確認
   ```bash
   ipconfig  # Windows
   # または
   ifconfig  # Linux/Mac
   ```

2. ファイアウォール設定
   - ポート8765を開放
   - Windows Defender等でPythonの通信を許可

#### クライアント側（操作PC）
1. サーバーIPアドレスを記録
2. 同一ネットワーク内にあることを確認

## 使用方法

### 1. サーバー起動（SO-100接続PC）
```bash
cd /path/to/SO-100/main
python remote_control_server.py
```

起動メッセージ例：
```
INFO:__main__:Starting SO-100 remote server on 0.0.0.0:8765
INFO:__main__:Initializing SO-100 robot...
INFO:__main__:Robot initialized successfully
INFO:__main__:Server started successfully
```

### 2. クライアント起動（操作PC）
```bash
cd /path/to/SO-100/main
python remote_control_client.py
```

### 3. 接続
1. クライアントGUIが開く
2. Server URLに `ws://[サーバーIP]:8765` を入力
   - 例: `ws://192.168.1.100:8765`
3. "Connect" ボタンをクリック
4. 接続成功で "Connected" と表示

### 4. ロボット操作

#### キーボード制御
- **WASD**: shoulder_pan/lift制御
  - W: shoulder_lift up
  - S: shoulder_lift down  
  - A: shoulder_pan left
  - D: shoulder_pan right

- **QE**: elbow_flex制御
  - Q: elbow_flex up
  - E: elbow_flex down

- **RF**: wrist_flex制御
  - R: wrist_flex up
  - F: wrist_flex down

- **ZX**: wrist_roll制御
  - Z: wrist_roll left
  - X: wrist_roll right

- **CV**: gripper制御
  - C: gripper open
  - V: gripper close

- **ESC**: 緊急停止

#### 緊急停止
- ESCキー または 緊急停止ボタンで即座に停止
- 再度ESCで通常操作に復帰

## ステータス表示

クライアントGUIに以下の情報がリアルタイム表示されます：

- **Robot Connected**: ロボット接続状態
- **Emergency Stop**: 緊急停止状態  
- **Current Positions**: 現在の関節角度
- **Target Positions**: 目標関節角度

## トラブルシューティング

### 接続できない場合
1. **ネットワーク確認**
   ```bash
   ping [サーバーIP]
   ```

2. **ポート確認**
   ```bash
   telnet [サーバーIP] 8765
   ```

3. **ファイアウォール**
   - Windows Defender等でポート8765を開放
   - セキュリティソフトの設定確認

### ロボットが動かない場合
1. **サーバー側ログ確認**
   - ロボット初期化エラーの有無
   - コマンド受信ログ

2. **SO-100接続確認**
   - USBケーブル接続
   - ドライバーインストール
   - 電源供給

### 動作が遅い場合
1. **ネットワーク遅延**
   - 有線LAN使用推奨
   - Wi-Fi品質確認

2. **更新頻度調整**
   - サーバー側の `time.sleep(0.05)` を調整
   - クライアント側の更新間隔調整

## カスタマイズ

### キーマッピング変更
`remote_control_client.py` の `key_mapping` 辞書を編集：

```python
self.key_mapping = {
    'w': 'shoulder_lift_up',
    # 他のキーマッピング...
}
```

### 通信ポート変更
サーバー・クライアント両方で同じポート番号に変更：

```python
# サーバー側
SO100RemoteServer(host='0.0.0.0', port=9999)

# クライアント側
self.server_url = "ws://localhost:9999"
```

### 制御パラメータ調整
サーバー側で移動量やスピードを調整：

```python
# remote_control_server.py内
delta = 0.5  # 移動量
time.sleep(0.05)  # 制御間隔
```

## セキュリティ注意事項

- 信頼できるネットワーク内でのみ使用
- パスワード認証等は実装されていない
- 本番環境では追加のセキュリティ対策を推奨

## ライセンス

LeRobotプロジェクトのライセンスに準拠
