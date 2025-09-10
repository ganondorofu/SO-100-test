# Copyright 2024 The HuggingFace Inc. team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Utilities to control a robot.

Useful to record a dataset, replay a recorded episode, run the policy on your robot
and record an evaluation dataset, and to recalibrate your robot if needed.

Examples of usage:

- Recalibrate your robot:
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --control.type=calibrate
```

- Unlimited teleoperation at highest frequency (~200 Hz is expected), to exit with CTRL+C:
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --robot.cameras='{}' \
    --control.type=teleoperate

# Add the cameras from the robot definition to visualize them:
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --control.type=teleoperate
```

- Unlimited keyboard control for follower arm (simplified):
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --robot.cameras='{}' \
    --control.type=keyboard

# With custom COM port (automatically updates config file):
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --robot.port=COM5 \
    --robot.cameras='{}' \
    --control.type=keyboard
```

- Unlimited teleoperation with keyboard control for follower arm:
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --robot.cameras='{}' \
    --control.type=teleoperate \
    --control.keyboard_control=true \
    --control.default_mode=keyboard
```

**Control Modes:**
- **Keyboard Mode** (`--control.type=keyboard`): Direct keyboard control of follower arm (no leader arm required)
- **Teleoperate Mode** (`--control.type=teleoperate`): Leader arm following or keyboard control with mode switching
- **Calibrate Mode** (`--control.type=calibrate`): Calibrate robot motors
- **Record Mode** (`--control.type=record`): Record robot movements for dataset creation
- **Replay Mode** (`--control.type=replay`): Replay recorded episodes

**Keyboard Controls (長押しで継続移動):**
- W/S: 肩の上げ下げ (shoulder_lift)
- A/D: 肩の左右回転 (shoulder_pan)
- Q/E: 肘の曲げ伸ばし (elbow_flex)
- R/F: 手首の前後 (wrist_flex)
- Z/X: 手首の回転 (wrist_roll)
- C/V: グリッパーの開閉 (gripper)

**Keyboard-only Configuration:**
For keyboard mode without leader arm hardware, use an empty leader_arms configuration:
```json
{
  "robot": {
    "type": "so100",
    "leader_arms": {},
    "follower_arms": { ... },
    "cameras": {}
  },
  "control": {
    "type": "keyboard",
    "display_data": false
  }
}
```

- Unlimited teleoperation at a limited frequency of 30 Hz, to simulate data recording frequency:
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --control.type=teleoperate \
    --control.fps=30
```

- Record one episode in order to test replay:
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --control.type=record \
    --control.fps=30 \
    --control.single_task="Grasp a lego block and put it in the bin." \
    --control.repo_id=$USER/koch_test \
    --control.num_episodes=1 \
    --control.push_to_hub=True
```

- Visualize dataset:
```bash
python lerobot/scripts/visualize_dataset.py \
    --repo-id $USER/koch_test \
    --episode-index 0
```

- Replay this test episode:
```bash
python lerobot/scripts/control_robot.py replay \
    --robot.type=so100 \
    --control.type=replay \
    --control.fps=30 \
    --control.repo_id=$USER/koch_test \
    --control.episode=0
```

- Record a full dataset in order to train a policy, with 2 seconds of warmup,
30 seconds of recording for each episode, and 10 seconds to reset the environment in between episodes:
```bash
python lerobot/scripts/control_robot.py record \
    --robot.type=so100 \
    --control.type=record \
    --control.fps 30 \
    --control.repo_id=$USER/koch_pick_place_lego \
    --control.num_episodes=50 \
    --control.warmup_time_s=2 \
    --control.episode_time_s=30 \
    --control.reset_time_s=10
```

- For remote controlled robots like LeKiwi, run this script on the robot edge device (e.g. RaspBerryPi):
```bash
python lerobot/scripts/control_robot.py \
  --robot.type=lekiwi \
  --control.type=remote_robot
```

**NOTE**: You can use your keyboard to control data recording flow.
- Tap right arrow key '->' to early exit while recording an episode and go to resseting the environment.
- Tap right arrow key '->' to early exit while resetting the environment and got to recording the next episode.
- Tap left arrow key '<-' to early exit and re-record the current episode.
- Tap escape key 'esc' to stop the data recording.
This might require a sudo permission to allow your terminal to monitor keyboard events.

**NOTE**: You can resume/continue data recording by running the same data recording command and adding `--control.resume=true`.

- Train on this dataset with the ACT policy:
```bash
python lerobot/scripts/train.py \
  --dataset.repo_id=${HF_USER}/koch_pick_place_lego \
  --policy.type=act \
  --output_dir=outputs/train/act_koch_pick_place_lego \
  --job_name=act_koch_pick_place_lego \
  --device=cuda \
  --wandb.enable=true
```

- Run the pretrained policy on the robot:
```bash
python lerobot/scripts/control_robot.py \
    --robot.type=so100 \
    --control.type=record \
    --control.fps=30 \
    --control.single_task="Grasp a lego block and put it in the bin." \
    --control.repo_id=$USER/eval_act_koch_pick_place_lego \
    --control.num_episodes=10 \
    --control.warmup_time_s=2 \
    --control.episode_time_s=30 \
    --control.reset_time_s=10 \
    --control.push_to_hub=true \
    --control.policy.path=outputs/train/act_koch_pick_place_lego/checkpoints/080000/pretrained_model
```
"""

import logging
import os
import sys
import time
import json
from dataclasses import asdict
from pathlib import Path
from pprint import pformat

try:
    import rerun as rr
except ImportError:
    print("Warning: rerun module not found. Display functionality may be limited.")
    rr = None

# from safetensors.torch import load_file, save_file
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.policies.factory import make_policy
from lerobot.common.robot_devices.control_configs import (
    CalibrateControlConfig,
    ControlConfig,
    ControlPipelineConfig,
    KeyboardControlConfig,
    RecordControlConfig,
    RemoteRobotConfig,
    ReplayControlConfig,
    TeleoperateControlConfig,
)
from lerobot.common.robot_devices.control_utils import (
    control_loop,
    init_keyboard_listener,
    is_headless,
    log_control_info,
    record_episode,
    reset_environment,
    sanity_check_dataset_name,
    sanity_check_dataset_robot_compatibility,
    stop_recording,
    warmup_record,
)
from lerobot.common.robot_devices.robots.utils import Robot, make_robot_from_config
from lerobot.common.robot_devices.utils import busy_wait, safe_disconnect
from lerobot.common.utils.utils import has_method, init_logging, log_say
from lerobot.configs import parser

########################################################################################
# Control modes
########################################################################################


@safe_disconnect
def calibrate(robot: Robot, cfg: CalibrateControlConfig):
    # TODO(aliberts): move this code in robots' classes
    if robot.robot_type.startswith("stretch"):
        if not robot.is_connected:
            robot.connect()
        if not robot.is_homed():
            robot.home()
        return

    arms = robot.available_arms if cfg.arms is None else cfg.arms
    unknown_arms = [arm_id for arm_id in arms if arm_id not in robot.available_arms]
    available_arms_str = " ".join(robot.available_arms)
    unknown_arms_str = " ".join(unknown_arms)

    if arms is None or len(arms) == 0:
        raise ValueError(
            "No arm provided. Use `--arms` as argument with one or more available arms.\n"
            f"For instance, to recalibrate all arms add: `--arms {available_arms_str}`"
        )

    if len(unknown_arms) > 0:
        raise ValueError(
            f"Unknown arms provided ('{unknown_arms_str}'). Available arms are `{available_arms_str}`."
        )

    for arm_id in arms:
        arm_calib_path = robot.calibration_dir / f"{arm_id}.json"
        if arm_calib_path.exists():
            print(f"Removing '{arm_calib_path}'")
            arm_calib_path.unlink()
        else:
            print(f"Calibration file not found '{arm_calib_path}'")

    if robot.is_connected:
        robot.disconnect()

    if robot.robot_type.startswith("lekiwi") and "main_follower" in arms:
        print("Calibrating only the lekiwi follower arm 'main_follower'...")
        robot.calibrate_follower()
        return

    if robot.robot_type.startswith("lekiwi") and "main_leader" in arms:
        print("Calibrating only the lekiwi leader arm 'main_leader'...")
        robot.calibrate_leader()
        return

    # Calling `connect` automatically runs calibration
    # when the calibration file is missing
    robot.connect()
    robot.disconnect()
    print("Calibration is done! You can now teleoperate and record datasets!")


@safe_disconnect
def teleoperate(robot: Robot, cfg: TeleoperateControlConfig):
    if cfg.keyboard_control:
        keyboard_teleoperate(robot, cfg)
    else:
        leader_teleoperate(robot, cfg)


@safe_disconnect
def keyboard_teleoperate(robot: Robot, cfg: TeleoperateControlConfig):
    """Dedicated keyboard teleoperation mode"""
    control_loop(
        robot,
        control_time_s=cfg.teleop_time_s,
        fps=cfg.fps,
        teleoperate=True,
        display_data=cfg.display_data,
        keyboard_control=True,
        default_mode="keyboard",
    )


@safe_disconnect
def leader_teleoperate(robot: Robot, cfg: TeleoperateControlConfig):
    """Dedicated leader arm teleoperation mode"""
    control_loop(
        robot,
        control_time_s=cfg.teleop_time_s,
        fps=cfg.fps,
        teleoperate=True,
        display_data=cfg.display_data,
        keyboard_control=False,
        default_mode="leader",
    )


@safe_disconnect
def keyboard(robot: Robot, cfg: KeyboardControlConfig):
    """Dedicated keyboard control mode"""
    control_loop(
        robot,
        control_time_s=cfg.teleop_time_s,
        fps=cfg.fps,
        teleoperate=True,
        display_data=cfg.display_data,
        keyboard_control=True,
        default_mode="keyboard",
    )


@safe_disconnect
def record(
    robot: Robot,
    cfg: RecordControlConfig,
) -> LeRobotDataset:
    # TODO(rcadene): Add option to record logs
    if cfg.resume:
        dataset = LeRobotDataset(
            cfg.repo_id,
            root=cfg.root,
        )
        if len(robot.cameras) > 0:
            dataset.start_image_writer(
                num_processes=cfg.num_image_writer_processes,
                num_threads=cfg.num_image_writer_threads_per_camera * len(robot.cameras),
            )
        sanity_check_dataset_robot_compatibility(dataset, robot, cfg.fps, cfg.video)
    else:
        # Create empty dataset or load existing saved episodes
        sanity_check_dataset_name(cfg.repo_id, cfg.policy)
        dataset = LeRobotDataset.create(
            cfg.repo_id,
            cfg.fps,
            root=cfg.root,
            robot=robot,
            use_videos=cfg.video,
            image_writer_processes=cfg.num_image_writer_processes,
            image_writer_threads=cfg.num_image_writer_threads_per_camera * len(robot.cameras),
        )

    # Load pretrained policy
    policy = None if cfg.policy is None else make_policy(cfg.policy, ds_meta=dataset.meta)

    if not robot.is_connected:
        robot.connect()

    listener, events = init_keyboard_listener()

    # Execute a few seconds without recording to:
    # 1. teleoperate the robot to move it in starting position if no policy provided,
    # 2. give times to the robot devices to connect and start synchronizing,
    # 3. place the cameras windows on screen
    enable_teleoperation = policy is None
    log_say("Warmup record", cfg.play_sounds)
    warmup_record(robot, events, enable_teleoperation, cfg.warmup_time_s, cfg.display_data, cfg.fps)

    if has_method(robot, "teleop_safety_stop"):
        robot.teleop_safety_stop()

    recorded_episodes = 0
    while True:
        if recorded_episodes >= cfg.num_episodes:
            break

        log_say(f"Recording episode {dataset.num_episodes}", cfg.play_sounds)
        record_episode(
            robot=robot,
            dataset=dataset,
            events=events,
            episode_time_s=cfg.episode_time_s,
            display_data=cfg.display_data,
            policy=policy,
            fps=cfg.fps,
            single_task=cfg.single_task,
        )

        # Execute a few seconds without recording to give time to manually reset the environment
        # Current code logic doesn't allow to teleoperate during this time.
        # TODO(rcadene): add an option to enable teleoperation during reset
        # Skip reset for the last episode to be recorded
        if not events["stop_recording"] and (
            (recorded_episodes < cfg.num_episodes - 1) or events["rerecord_episode"]
        ):
            log_say("Reset the environment", cfg.play_sounds)
            reset_environment(robot, events, cfg.reset_time_s, cfg.fps)

        if events["rerecord_episode"]:
            log_say("Re-record episode", cfg.play_sounds)
            events["rerecord_episode"] = False
            events["exit_early"] = False
            dataset.clear_episode_buffer()
            continue

        dataset.save_episode()
        recorded_episodes += 1

        if events["stop_recording"]:
            break

    log_say("Stop recording", cfg.play_sounds, blocking=True)
    stop_recording(robot, listener, cfg.display_data)

    if cfg.push_to_hub:
        dataset.push_to_hub(tags=cfg.tags, private=cfg.private)

    log_say("Exiting", cfg.play_sounds)
    return dataset


@safe_disconnect
def replay(
    robot: Robot,
    cfg: ReplayControlConfig,
):
    # TODO(rcadene, aliberts): refactor with control_loop, once `dataset` is an instance of LeRobotDataset
    # TODO(rcadene): Add option to record logs

    dataset = LeRobotDataset(cfg.repo_id, root=cfg.root, episodes=[cfg.episode])
    actions = dataset.hf_dataset.select_columns("action")

    if not robot.is_connected:
        robot.connect()

    log_say("Replaying episode", cfg.play_sounds, blocking=True)
    for idx in range(dataset.num_frames):
        start_episode_t = time.perf_counter()

        action = actions[idx]["action"]
        robot.send_action(action)

        dt_s = time.perf_counter() - start_episode_t
        busy_wait(1 / cfg.fps - dt_s)

        dt_s = time.perf_counter() - start_episode_t
        log_control_info(robot, dt_s, fps=cfg.fps)


def _init_rerun(control_config: ControlConfig, session_name: str = "lerobot_control_loop") -> None:
    """Initializes the Rerun SDK for visualizing the control loop.

    Args:
        control_config: Configuration determining data display and robot type.
        session_name: Rerun session name. Defaults to "lerobot_control_loop".

    Raises:
        ValueError: If viewer IP is missing for non-remote configurations with display enabled.
    """
    if rr is None:
        print("Warning: rerun module not available. Skipping display initialization.")
        return
        
    if (control_config.display_data and not is_headless()) or (
        control_config.display_data and isinstance(control_config, RemoteRobotConfig)
    ):
        # Configure Rerun flush batch size default to 8KB if not set
        batch_size = os.getenv("RERUN_FLUSH_NUM_BYTES", "8000")
        os.environ["RERUN_FLUSH_NUM_BYTES"] = batch_size

        # Initialize Rerun based on configuration
        rr.init(session_name)
        if isinstance(control_config, RemoteRobotConfig):
            viewer_ip = control_config.viewer_ip
            viewer_port = control_config.viewer_port
            if not viewer_ip or not viewer_port:
                raise ValueError(
                    "Viewer IP & Port are required for remote config. Set via config file/CLI or disable control_config.display_data."
                )
            logging.info(f"Connecting to viewer at {viewer_ip}:{viewer_port}")
            rr.connect_tcp(f"{viewer_ip}:{viewer_port}")
        else:
            # Get memory limit for rerun viewer parameters
            memory_limit = os.getenv("LEROBOT_RERUN_MEMORY_LIMIT", "10%")
            rr.spawn(memory_limit=memory_limit)


def control_robot(cfg: ControlPipelineConfig):
    init_logging()
    logging.info(pformat(asdict(cfg)))

    robot = make_robot_from_config(cfg.robot)

    # TODO(Steven): Blueprint for fixed window size

    if isinstance(cfg.control, CalibrateControlConfig):
        calibrate(robot, cfg.control)
    elif isinstance(cfg.control, TeleoperateControlConfig):
        _init_rerun(control_config=cfg.control, session_name="lerobot_control_loop_teleop")
        teleoperate(robot, cfg.control)
    elif isinstance(cfg.control, KeyboardControlConfig):
        _init_rerun(control_config=cfg.control, session_name="lerobot_control_loop_keyboard")
        keyboard(robot, cfg.control)
    elif isinstance(cfg.control, RecordControlConfig):
        _init_rerun(control_config=cfg.control, session_name="lerobot_control_loop_record")
        record(robot, cfg.control)
    elif isinstance(cfg.control, ReplayControlConfig):
        replay(robot, cfg.control)
    elif isinstance(cfg.control, RemoteRobotConfig):
        from lerobot.common.robot_devices.robots.lekiwi_remote import run_lekiwi

        _init_rerun(control_config=cfg.control, session_name="lerobot_control_loop_remote")
        run_lekiwi(cfg.robot)

    if robot.is_connected:
        # Disconnect manually to avoid a "Core dump" during process
        # termination due to camera threads not properly exiting.
        robot.disconnect()


def _get_config_path_for_keyboard_mode():
    """Get the config path for keyboard mode if keyboard control type is specified."""
    # Check if --control.type=keyboard is specified in CLI args
    keyboard_mode = False
    robot_port = None
    
    for arg in sys.argv:
        if arg == "--control.type=keyboard":
            keyboard_mode = True
            break
    
    if keyboard_mode:
        # Check for COM port specification and update config file
        for i, arg in enumerate(sys.argv):
            if arg.startswith("--robot.port="):
                robot_port = arg.split("=", 1)[1]
                # Remove the --robot.port argument from sys.argv to avoid parsing errors
                sys.argv.remove(arg)
                break
            elif arg == "--robot.port" and i + 1 < len(sys.argv):
                robot_port = sys.argv[i + 1]
                # Remove both --robot.port and its value from sys.argv
                sys.argv.remove(arg)
                sys.argv.remove(robot_port)
                break
        
        # Update config file with COM port if specified
        if robot_port:
            _update_config_file_com_port(robot_port)
        
        # Use so100_keyboard_config.json automatically for keyboard mode
        config_path = Path(__file__).parent.parent.parent / "so100_keyboard_config.json"
        if config_path.exists():
            return config_path
        else:
            print(f"Warning: {config_path} not found, using default config")
            return None
    return None


def _process_com_port_for_keyboard_mode(cfg):
    """Process COM port setting for keyboard and teleoperate modes from command line arguments."""
    # Check for follower.COM and leader.COM arguments
    follower_port = None
    leader_port = None
    
    for i, arg in enumerate(sys.argv):
        # Check for --follower.COM
        if arg.startswith("--follower.COM="):
            follower_port = arg.split("=", 1)[1]
        elif arg == "--follower.COM" and i + 1 < len(sys.argv):
            follower_port = sys.argv[i + 1]
        # Check for --leader.COM
        elif arg.startswith("--leader.COM="):
            leader_port = arg.split("=", 1)[1]
        elif arg == "--leader.COM" and i + 1 < len(sys.argv):
            leader_port = sys.argv[i + 1]
        # Legacy support for --robot.port
        elif arg.startswith("--robot.port="):
            follower_port = arg.split("=", 1)[1]
        elif arg == "--robot.port" and i + 1 < len(sys.argv):
            follower_port = sys.argv[i + 1]
    
    # Update follower arm configuration
    if follower_port and hasattr(cfg, 'robot') and hasattr(cfg.robot, 'follower_arms'):
        print(f"🔌 フォロワーアーム COMポート: {follower_port}")
        try:
            if hasattr(cfg.robot.follower_arms, 'main'):
                if hasattr(cfg.robot.follower_arms.main, 'port'):
                    cfg.robot.follower_arms.main.port = follower_port
                else:
                    setattr(cfg.robot.follower_arms.main, 'port', follower_port)
            elif isinstance(cfg.robot.follower_arms, dict) and 'main' in cfg.robot.follower_arms:
                if hasattr(cfg.robot.follower_arms['main'], 'port'):
                    cfg.robot.follower_arms['main'].port = follower_port
                else:
                    setattr(cfg.robot.follower_arms['main'], 'port', follower_port)
        except Exception as e:
            print(f"⚠️ フォロワーアーム COMポート設定エラー: {e}")
    
    # Update leader arm configuration (for teleoperate mode)
    if leader_port and hasattr(cfg, 'robot') and hasattr(cfg.robot, 'leader_arms'):
        print(f"🔌 リーダーアーム COMポート: {leader_port}")
        try:
            if hasattr(cfg.robot.leader_arms, 'main'):
                if hasattr(cfg.robot.leader_arms.main, 'port'):
                    cfg.robot.leader_arms.main.port = leader_port
                else:
                    setattr(cfg.robot.leader_arms.main, 'port', leader_port)
            elif isinstance(cfg.robot.leader_arms, dict) and 'main' in cfg.robot.leader_arms:
                if hasattr(cfg.robot.leader_arms['main'], 'port'):
                    cfg.robot.leader_arms['main'].port = leader_port
                else:
                    setattr(cfg.robot.leader_arms['main'], 'port', leader_port)
        except Exception as e:
            print(f"⚠️ リーダーアーム COMポート設定エラー: {e}")
    
    # Show current configuration
    if follower_port or leader_port:
        print("📋 COMポート設定完了")
        if follower_port:
            print(f"  フォロワーアーム: {follower_port}")
        if leader_port:
            print(f"  リーダーアーム: {leader_port}")
    
    return cfg
    
    return cfg


def _update_config_file_com_port(com_port):
    """Update the COM port in the keyboard config file."""
    config_path = Path(__file__).parent.parent.parent / "so100_keyboard_config.json"
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Update COM port in config while preserving all other fields
            if 'robot' in config and 'follower_arms' in config['robot'] and 'main' in config['robot']['follower_arms']:
                config['robot']['follower_arms']['main']['port'] = com_port
                # Ensure type field exists
                if 'type' not in config['robot']['follower_arms']['main']:
                    config['robot']['follower_arms']['main']['type'] = 'feetech'
                
                # Write back to file
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 設定ファイル更新: {com_port}")
                return True
        except Exception as e:
            print(f"⚠️ 設定ファイル更新エラー: {e}")
    
    return False


@parser.wrap()
def main_control_robot(cfg: ControlPipelineConfig):
    # Process COM port setting for keyboard mode
    cfg = _process_com_port_for_keyboard_mode(cfg)
    control_robot(cfg)


if __name__ == "__main__":
    # Check if keyboard mode is requested and set config path accordingly
    config_path = _get_config_path_for_keyboard_mode()
    if config_path:
        # Use custom parser wrap with config path for keyboard mode
        @parser.wrap(config_path=config_path)
        def control_robot_with_config(cfg: ControlPipelineConfig):
            # Process COM port setting for keyboard mode
            cfg = _process_com_port_for_keyboard_mode(cfg)
            control_robot(cfg)

        control_robot_with_config()
    else:
        # Use default parser wrap
        main_control_robot()
