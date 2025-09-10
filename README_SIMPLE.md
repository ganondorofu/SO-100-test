# SO-100 ロボットアーム 簡単セットアップガイド

## 必要な環境

```bash
# Conda環境作成
conda create -n lerobot python=3.10
conda activate lerobot

# 基本パッケージ
pip install torch torchvision
pip install lerobot
pip install websockets
pip install opencv-python
pip install pyserial
pip install tkinter

# Windowsの場合、追加で必要
pip install pywin32
```

## 使用方法

### 1. 基本起動
```bash
cd main
python so100_manager.py
```

### 2. 直接コマンド実行例

#### キーボード制御
```bash
# サーバー起動（別ターミナル）
python websocket_control_robot.py server --robot.type=so100 --com-port COM5

# クライアント起動
python websocket_control_robot.py client --server-url ws://localhost:8765
```

#### テレオペレーション
```bash
python -m lerobot.scripts.control_robot \
  --robot-path lerobot.common.robot_devices.robots.so100 \
  --robot-overrides "robot.port=COM5"
```

#### データ収集
```bash
python -m lerobot.scripts.control_robot \
  --robot-path lerobot.common.robot_devices.robots.so100 \
  --robot-overrides "robot.port=COM5" \
  --record --record-dir ./data/my_dataset
```

#### 学習
```bash
python -m lerobot.scripts.train \
  --config-name act \
  --dataset-path ./data/my_dataset
```

## 設定

### COMポート確認
Windowsデバイスマネージャーでシリアルポートを確認してください。

### ロボット設定
- **SO-100**: `--robot.type=so100`
- **SO-101**: `--robot.type=so101`

## トラブルシューティング

### よくあるエラー
1. **COMポートエラー**: デバイスマネージャーでポート番号確認
2. **モジュールエラー**: `pip install [パッケージ名]`
3. **権限エラー**: 管理者権限でターミナル起動

### 対話型マネージャー
詳細設定は `python so100_manager.py` で簡単操作可能
