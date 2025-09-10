# SO-100 ロボット制御コマンド集

## 基本セットアップ

```bash
# LeRobot環境のアクティベート
conda activate lerobot
```

## キャリブレーション

### 基本コマンド
```bash
# デフォルト設定でキャリブレーション（COM5とCOM6を使用）
python lerobot/scripts/control_robot.py --robot.type so100 --control.type calibrate

# カスタム設定ファイルでキャリブレーション
python lerobot/scripts/control_robot.py --config_path so100_calibrate_config.json
```

**注意**: 
- キャリブレーションはテレオペレーションの前に必要です
- デフォルトではLeader: COM5, Follower: COM6を使用
- COMポートが異なる場合は設定ファイルを作成してください

### キャリブレーション手順
1. ロボットアームを安全な中間位置に手動で移動
2. プロンプトが表示されたらEnterキーを押す
3. 各軸について最小位置と最大位置を設定
4. キャリブレーションファイルが`.cache/calibration/so100/`に保存される

### キャリブレーションの完了後
```bash
# テレオペレーション実行
python lerobot/scripts/control_robot.py --config_path so100_teleop_config.json
```
python lerobot/scripts/control_robot.py --robot.type so100 --control.type calibrate --config_path so100_teleop_config.json

python lerobot/scripts/control_robot.py --config_path so100_teleop_config.json --control.type teleoperate

python lerobot/common/robot_devices/cameras/opencv.py --images-dir outputs/images_from_opencv_cameras

python lerobot/scripts/control_robot.py --robot.type=so101 --control.type=record --control.fps=30 --control.single_task="Grasp a lego block and put it in the bin." --control.repo_id="ganondorofu/so101_test" --control.warmup_time_s=5 --control.episode_time_s=30 --control.reset_time_s=30 --control.num_episodes=2 --control.display_data=false --control.push_to_hub=false --config_path so101_record_config.json
