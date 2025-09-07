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

"""Contains logic to instantiate a robot, read information from its motors and cameras,
and send orders to its motors.
"""
# TODO(rcadene, aliberts): reorganize the codebase into one file per robot, with the associated
# calibration procedure, to make it easy for people to add their own robot.

import json
import logging
import time
import warnings
from pathlib import Path

import numpy as np
import torch
import tkinter as tk

from lerobot.common.robot_devices.cameras.utils import make_cameras_from_configs
from lerobot.common.robot_devices.motors.utils import MotorsBus, make_motors_buses_from_configs
from lerobot.common.robot_devices.robots.configs import ManipulatorRobotConfig
from lerobot.common.robot_devices.robots.utils import get_arm_id
from lerobot.common.robot_devices.utils import RobotDeviceAlreadyConnectedError, RobotDeviceNotConnectedError


# Constants for robot control
DEFAULT_SPEED_SCALE = 1.0
DEFAULT_BASE_SPEED = 10.0  # Base speed in degrees
DEFAULT_HOLD_SPEED = 2.0  # Speed for moving to target position

SPEED_SCALE_MIN = 0.1
SPEED_SCALE_MAX = 5.0
HOLD_SPEED_MIN = 0.1
HOLD_SPEED_MAX = 10.0

# Motor indices
MOTOR_SHOULDER_PAN = 0
MOTOR_SHOULDER_LIFT = 1
MOTOR_ELBOW_FLEX = 2
MOTOR_WRIST_FLEX = 3
MOTOR_WRIST_ROLL = 4
MOTOR_GRIPPER = 5

MOTOR_NAMES = ["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"]

# GUI Constants
WINDOW_TITLE = "Robot Keyboard Control"
WINDOW_SIZE = "400x300"
FONT_FAMILY = "Arial"
FONT_SIZE_MODE = 12
FONT_SIZE_INFO = 10

# Instructions text
KEYBOARD_INSTRUCTIONS = """
キーボード操作説明 (長押しで継続移動):
WASD: 肩の回転と上下 (shoulder_pan, shoulder_lift)
QE: 肘の曲げ伸ばし (elbow_flex)
RF: 手首の前後 (wrist_flex)
ZX: 手首の回転 (wrist_roll)
CV: グリッパーの開閉 (gripper)
矢印キー: 肩の操作 (Up/Down: shoulder_lift, Left/Right: shoulder_pan)
数字キー: 各関節の操作 (1-6: 各モーター)
速度制御: + (速度アップ), - (速度ダウン), * (リセット)
目標位置移動速度: Ctrl++ (アップ), Ctrl+- (ダウン), Ctrl+* (リセット)
"""


class KeyboardController:
    """Handles keyboard input and control logic for robot manipulation."""

    def __init__(self, follower_arms):
        self.follower_arms = follower_arms
        self.pressed_keys = set()
        self.ctrl_pressed = False
        self.emergency_stop_active = False  # Emergency stop state

        # Speed management
        self.speed_scale = DEFAULT_SPEED_SCALE
        self.base_speed = DEFAULT_BASE_SPEED
        self.hold_speed = DEFAULT_HOLD_SPEED

        # Movement state
        self.continuous_deltas = {
            name: torch.zeros(len(self.follower_arms[name].motor_names))
            for name in self.follower_arms
        }
        self.target_positions = {}

        # Long press support
        self.key_timers = {}  # Track timers for each key
        self.repeat_delay = 50   # milliseconds between repeats (faster updates)
        self.initial_delay = 100  # milliseconds before first repeat (quicker start)

        # Base key mapping (without speed scaling)
        self.base_key_mapping = self._create_base_key_mapping()
        self.key_mapping = {}

        self._update_key_mapping()

    def _create_base_key_mapping(self):
        """Create the base key mapping dictionary."""
        return {
            # WASD keys - smaller delta values for smoother movement
            'w': (MOTOR_SHOULDER_LIFT, 0.5),   # shoulder_lift up
            's': (MOTOR_SHOULDER_LIFT, -0.5),  # shoulder_lift down
            'a': (MOTOR_SHOULDER_PAN, -0.5),  # shoulder_pan right (反転)
            'd': (MOTOR_SHOULDER_PAN, 0.5),   # shoulder_pan left (反転)

            # QE keys for elbow
            'q': (MOTOR_ELBOW_FLEX, 0.5),   # elbow_flex up
            'e': (MOTOR_ELBOW_FLEX, -0.5),  # elbow_flex down

            # RF keys for wrist flex
            'r': (MOTOR_WRIST_FLEX, 0.5),   # wrist_flex up
            'f': (MOTOR_WRIST_FLEX, -0.5),  # wrist_flex down

            # ZX keys for wrist roll
            'z': (MOTOR_WRIST_ROLL, -0.5),  # wrist_roll right (反転)
            'x': (MOTOR_WRIST_ROLL, 0.5),   # wrist_roll left (反転)

            # CV keys for gripper
            'c': (MOTOR_GRIPPER, -0.5),  # gripper close (反転)
            'v': (MOTOR_GRIPPER, 0.5),   # gripper open (反転)

            # Arrow keys
            'up': (MOTOR_SHOULDER_LIFT, 0.5),     # shoulder_lift up
            'down': (MOTOR_SHOULDER_LIFT, -0.5),  # shoulder_lift down
            'left': (MOTOR_SHOULDER_PAN, -0.5),  # shoulder_pan right (反転)
            'right': (MOTOR_SHOULDER_PAN, 0.5),  # shoulder_pan left (反転)

            # Number keys for direct motor control
            '1': (MOTOR_SHOULDER_PAN, -0.5),  # shoulder_pan positive (調整後)
            '2': (MOTOR_SHOULDER_LIFT, 0.5),   # shoulder_lift positive
            '3': (MOTOR_ELBOW_FLEX, 0.5),   # elbow_flex positive
            '4': (MOTOR_WRIST_FLEX, 0.5),   # wrist_flex positive
            '5': (MOTOR_WRIST_ROLL, -0.5),  # wrist_roll positive (調整後)
            '6': (MOTOR_GRIPPER, -0.5),   # gripper positive (調整後)

            # Shift + number keys for negative direction
            'exclam': (MOTOR_SHOULDER_PAN, 0.5),      # ! (shift+1) - shoulder_pan negative (調整後)
            'at': (MOTOR_SHOULDER_LIFT, -0.5),         # @ (shift+2) - shoulder_lift negative
            'numbersign': (MOTOR_ELBOW_FLEX, -0.5), # # (shift+3) - elbow_flex negative
            'dollar': (MOTOR_WRIST_FLEX, -0.5),     # $ (shift+4) - wrist_flex negative
            'percent': (MOTOR_WRIST_ROLL, 0.5),     # % (shift+5) - wrist_roll negative (調整後)
            'asciicircum': (MOTOR_GRIPPER, 0.5),  # ^ (shift+6) - gripper negative (調整後)
        }

    def _update_key_mapping(self):
        """Update key mapping based on current speed scale."""
        self.key_mapping = {}
        for key, (motor_idx, base_delta) in self.base_key_mapping.items():
            self.key_mapping[key] = (motor_idx, base_delta * self.base_speed * self.speed_scale)

    def adjust_speed(self, delta):
        """Adjust speed scale by delta amount."""
        old_speed = self.speed_scale
        self.speed_scale = max(SPEED_SCALE_MIN, min(SPEED_SCALE_MAX, self.speed_scale + delta))
        if self.speed_scale != old_speed:
            self._update_key_mapping()
            print(f"Speed adjusted: {old_speed:.1f}x -> {self.speed_scale:.1f}x "
                  f"({self.base_speed * self.speed_scale:.1f}° per step)")

    def reset_speed(self):
        """Reset speed to default."""
        old_speed = self.speed_scale
        self.speed_scale = DEFAULT_SPEED_SCALE
        if self.speed_scale != old_speed:
            self._update_key_mapping()
            print(f"Speed reset: {old_speed:.1f}x -> {self.speed_scale:.1f}x "
                  f"({self.base_speed * self.speed_scale:.1f}° per step)")

    def adjust_hold_speed(self, delta):
        """Adjust hold speed by delta amount."""
        old_speed = self.hold_speed
        self.hold_speed = max(HOLD_SPEED_MIN, min(HOLD_SPEED_MAX, self.hold_speed + delta))
        if self.hold_speed != old_speed:
            print(f"Hold speed adjusted: {old_speed:.1f}° -> {self.hold_speed:.1f}° per step")

    def reset_hold_speed(self):
        """Reset hold speed to default."""
        old_speed = self.hold_speed
        self.hold_speed = DEFAULT_HOLD_SPEED
        if self.hold_speed != old_speed:
            print(f"Hold speed reset: {old_speed:.1f}° -> {self.hold_speed:.1f}° per step")

    def get_speed_display_text(self):
        """Get formatted speed display text."""
        return (f"Speed: {self.speed_scale:.1f}x "
                f"({self.base_speed * self.speed_scale:.1f}°), "
                f"Hold: {self.hold_speed:.1f}°")

    def initialize_target_positions(self, current_positions):
        """Initialize target positions with current positions."""
        for name, pos in current_positions.items():
            self.target_positions[name] = pos.clone()
            print(f"Initialized target positions for {name}: {pos}")

    def update_target_position(self, key, is_connected=False):
        """Update target position for a specific key."""
        if key in self.key_mapping and is_connected:
            motor_idx, delta = self.key_mapping[key]
            motor_name = MOTOR_NAMES[motor_idx]
            
            # Update target position by adding delta
            self.target_positions["main"][motor_idx] += delta
            print(f"Target position updated - {motor_name}: {self.target_positions['main'][motor_idx]:.1f}° (delta: {delta:.1f}°)")
            return True
        return False

    def schedule_key_repeat(self, key, is_connected=False, root=None):
        """Schedule key repeat for long press."""
        if key in self.pressed_keys and key in self.key_mapping:
            # Update target position
            if self.update_target_position(key, is_connected):
                # Schedule next repeat
                if root and key in self.pressed_keys:  # Check if key is still pressed
                    self.key_timers[key] = root.after(self.repeat_delay, 
                                                    lambda: self.schedule_key_repeat(key, is_connected, root))

    def on_key_press(self, event, is_connected=False, root=None):
        """Handle key press events."""
        key = event.keysym.lower()
        
        # Block all key input except ESC during emergency stop
        if self.emergency_stop_active and key != 'escape':
            print(f"🚨 Key '{key}' blocked - Emergency stop active. Press ESC to resume.")
            return
            
        if key not in self.pressed_keys:
            self.pressed_keys.add(key)

            # Track Ctrl key state
            if key == 'control_l' or key == 'control_r':
                self.ctrl_pressed = True
                return

            # Handle speed control keys first
            if key == 'plus' or key == 'equal':  # + key
                if self.ctrl_pressed:
                    self.adjust_hold_speed(0.5)
                else:
                    self.adjust_speed(0.1)
                return
            elif key == 'minus':  # - key
                if self.ctrl_pressed:
                    self.adjust_hold_speed(-0.5)
                else:
                    self.adjust_speed(-0.1)
                return
            elif key == 'asterisk' or key == 'multiply':  # * key
                if self.ctrl_pressed:
                    self.reset_hold_speed()
                else:
                    self.reset_speed()
                return

            # Check if key is in mapping
            if key in self.key_mapping:
                motor_idx, delta = self.key_mapping[key]
                motor_name = MOTOR_NAMES[motor_idx]
                direction = "positive" if delta > 0 else "negative"
                print(f"Key '{key}' pressed - {motor_name} {direction} (delta: {delta:.1f}°)")

                # Update target position immediately for the first press
                if is_connected:
                    self.update_target_position(key, is_connected)
                    
                    # Start long press timer for continuous movement
                    if root:
                        # Cancel any existing timer for this key
                        if key in self.key_timers:
                            root.after_cancel(self.key_timers[key])
                        
                        # Schedule first repeat after initial delay
                        self.key_timers[key] = root.after(self.initial_delay, 
                                                        lambda: self.schedule_key_repeat(key, is_connected, root))
                else:
                    print(f"Not connected - target update skipped")
            else:
                print(f"Key '{key}' pressed - no mapping defined")

    def on_key_release(self, event, is_connected=False, root=None):
        """Handle key release events."""
        key = event.keysym.lower()
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)

            # Cancel any active timer for this key
            if key in self.key_timers and root:
                root.after_cancel(self.key_timers[key])
                del self.key_timers[key]

            # Track Ctrl key state
            if key == 'control_l' or key == 'control_r':
                self.ctrl_pressed = False
                return

            # Just log the key release - target positions remain unchanged
            if key in self.key_mapping:
                motor_idx, _ = self.key_mapping[key]
                motor_name = MOTOR_NAMES[motor_idx]
                print(f"Key '{key}' released - {motor_name} target remains at {self.target_positions['main'][motor_idx]:.1f}°")

    def on_escape_press(self, event, is_connected=False, root=None):
        """Emergency stop - immediately stop all motor movement and clear all timers."""
        if not self.emergency_stop_active:
            # Activate emergency stop
            print("🚨 EMERGENCY STOP ACTIVATED 🚨")
            self.emergency_stop_active = True
            
            # Clear all pressed keys
            self.pressed_keys.clear()
            
            # Cancel all active timers
            if root:
                for key, timer_id in list(self.key_timers.items()):
                    root.after_cancel(timer_id)
                    print(f"Cancelled timer for key '{key}'")
                self.key_timers.clear()
            
            # If connected, set target positions to current positions to stop movement
            if is_connected and hasattr(self, 'follower_arms'):
                try:
                    current_pos = self.follower_arms["main"].read("Present_Position")
                    current_pos = torch.from_numpy(current_pos)
                    
                    # Set all target positions to current positions (no gravity compensation)
                    self.target_positions["main"] = current_pos.clone()
                    
                    print("All motors stopped - target positions set to current positions")
                    print(f"Current positions locked at: {current_pos}")
                    
                except Exception as e:
                    print(f"Error reading current position for emergency stop: {e}")
            
            print("Emergency stop complete - all movement halted")
            print("Press ESC again to resume normal operation")
        else:
            # Deactivate emergency stop
            print("🟢 EMERGENCY STOP DEACTIVATED - Normal operation resumed")
            self.emergency_stop_active = False

    def calculate_goal_positions(self, current_positions):
        """Calculate goal positions - always move all motors to their target positions."""
        goal_positions = {}

        for name, current_pos in current_positions.items():
            if self.emergency_stop_active:
                # Emergency stop mode - hold exact current positions with no compensation
                goal_pos = current_pos.clone()
                # Update target positions to current positions to maintain stop
                self.target_positions[name] = current_pos.clone()
                print("🚨 EMERGENCY STOP ACTIVE - Motors locked at current positions")
            else:
                # Normal operation - use target positions as goal positions
                goal_pos = self.target_positions[name].clone()
                
                # Apply gravity compensation to counteract physical forces
                for i in range(len(goal_pos)):
                    motor_name = MOTOR_NAMES[i] if i < len(MOTOR_NAMES) else f"motor_{i}"
                    
                    if motor_name == "shoulder_lift":
                        # Moderate upward compensation for shoulder_lift to counteract gravity
                        goal_pos[i] = self.target_positions[name][i] + 6.0  # degrees upward (reduced)
                    elif motor_name == "elbow_flex":
                        # Light upward compensation for elbow_flex
                        goal_pos[i] = self.target_positions[name][i] + 3.0  # degrees upward (reduced)

            goal_positions[name] = goal_pos
            
            # Debug output
            if self.emergency_stop_active:
                print(f"EMERGENCY STOP - All motors locked")
            elif len(self.pressed_keys) > 0:  # Only show debug when keys are active
                print(f"Active control - Target: {self.target_positions[name]}")
                print(f"With gravity comp: {goal_pos}")

        return goal_positions


class RobotGUI:
    """Handles the Tkinter GUI for robot control."""

    def __init__(self, keyboard_controller):
        self.keyboard_controller = keyboard_controller
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)

        self._setup_ui()
        self._bind_keys()

        # Hide the window initially
        self.root.withdraw()

    def _setup_ui(self):
        """Setup the user interface components."""
        # Add mode display label
        self.mode_label = tk.Label(
            self.root,
            text="Mode: Leader",
            font=(FONT_FAMILY, FONT_SIZE_MODE)
        )
        self.mode_label.pack(pady=5)

        # Add speed display label
        self.speed_label = tk.Label(
            self.root,
            text=self.keyboard_controller.get_speed_display_text(),
            font=(FONT_FAMILY, FONT_SIZE_INFO)
        )
        self.speed_label.pack(pady=2)

        # Add instructions label
        self.instructions_label = tk.Label(
            self.root,
            text=KEYBOARD_INSTRUCTIONS,
            font=(FONT_FAMILY, FONT_SIZE_INFO),
            justify=tk.LEFT
        )
        self.instructions_label.pack(pady=5)

    def _bind_keys(self):
        """Bind keyboard events."""
        self.root.bind('<KeyPress>', self._on_key_press)
        self.root.bind('<KeyRelease>', self._on_key_release)
        self.root.bind('<Escape>', self._on_escape_press)

    def _on_escape_press(self, event):
        """Handle escape key press for emergency stop."""
        self.keyboard_controller.on_escape_press(event, is_connected=True, root=self.root)

    def _on_key_press(self, event):
        """Handle key press events."""
        self.keyboard_controller.on_key_press(event, is_connected=True, root=self.root)
        self.update_speed_display()

    def _on_key_release(self, event):
        """Handle key release events."""
        self.keyboard_controller.on_key_release(event, is_connected=True, root=self.root)

    def update_speed_display(self):
        """Update the speed display label."""
        if hasattr(self, 'speed_label'):
            self.speed_label.config(text=self.keyboard_controller.get_speed_display_text())

    def update_mode_display(self, mode):
        """Update the mode display label."""
        if hasattr(self, 'mode_label'):
            self.mode_label.config(text=f"Mode: {mode}")

    def show(self):
        """Show the GUI window."""
        self.root.deiconify()
        self.root.focus_force()

    def hide(self):
        """Hide the GUI window."""
        self.root.withdraw()

    def update(self):
        """Update the GUI."""
        self.root.update_idletasks()
        self.root.update()

    def destroy(self):
        """Destroy the GUI window."""
        if hasattr(self, 'root'):
            self.root.destroy()


def ensure_safe_goal_position(
    goal_pos: torch.Tensor, present_pos: torch.Tensor, max_relative_target: float | list[float]
):
    # Cap relative action target magnitude for safety.
    diff = goal_pos - present_pos
    max_relative_target = torch.tensor(max_relative_target)
    safe_diff = torch.minimum(diff, max_relative_target)
    safe_diff = torch.maximum(safe_diff, -max_relative_target)
    safe_goal_pos = present_pos + safe_diff

    if not torch.allclose(goal_pos, safe_goal_pos):
        logging.warning(
            "Relative goal position magnitude had to be clamped to be safe.\n"
            f"  requested relative goal position target: {diff}\n"
            f"    clamped relative goal position target: {safe_diff}"
        )

    return safe_goal_pos


def ensure_absolute_position_limits(
    goal_pos: torch.Tensor, motor_names: list[str], robot_type: str
) -> torch.Tensor:
    """Ensure goal positions are within absolute safe limits for each motor."""
    # ユーザーのリクエストにより、可動域制限を無効化
    return goal_pos


class ManipulatorRobot:
    # TODO(rcadene): Implement force feedback
    """This class allows to control any manipulator robot of various number of motors.

    Non exhaustive list of robots:
    - [Koch v1.0](https://github.com/AlexanderKoch-Koch/low_cost_robot), with and without the wrist-to-elbow expansion, developed
    by Alexander Koch from [Tau Robotics](https://tau-robotics.com)
    - [Koch v1.1](https://github.com/jess-moss/koch-v1-1) developed by Jess Moss
    - [Aloha](https://www.trossenrobotics.com/aloha-kits) developed by Trossen Robotics

    Example of instantiation, a pre-defined robot config is required:
    ```python
    robot = ManipulatorRobot(KochRobotConfig())
    ```

    Example of overwriting motors during instantiation:
    ```python
    # Defines how to communicate with the motors of the leader and follower arms
    leader_arms = {
        "main": DynamixelMotorsBusConfig(
            port="/dev/tty.usbmodem575E0031751",
            motors={
                # name: (index, model)
                "shoulder_pan": (1, "xl330-m077"),
                "shoulder_lift": (2, "xl330-m077"),
                "elbow_flex": (3, "xl330-m077"),
                "wrist_flex": (4, "xl330-m077"),
                "wrist_roll": (5, "xl330-m077"),
                "gripper": (6, "xl330-m077"),
            },
        ),
    }
    follower_arms = {
        "main": DynamixelMotorsBusConfig(
            port="/dev/tty.usbmodem575E0032081",
            motors={
                # name: (index, model)
                "shoulder_pan": (1, "xl430-w250"),
                "shoulder_lift": (2, "xl430-w250"),
                "elbow_flex": (3, "xl330-m288"),
                "wrist_flex": (4, "xl330-m288"),
                "wrist_roll": (5, "xl330-m288"),
                "gripper": (6, "xl330-m288"),
            },
        ),
    }
    robot_config = KochRobotConfig(leader_arms=leader_arms, follower_arms=follower_arms)
    robot = ManipulatorRobot(robot_config)
    ```

    Example of overwriting cameras during instantiation:
    ```python
    # Defines how to communicate with 2 cameras connected to the computer.
    # Here, the webcam of the laptop and the phone (connected in USB to the laptop)
    # can be reached respectively using the camera indices 0 and 1. These indices can be
    # arbitrary. See the documentation of `OpenCVCamera` to find your own camera indices.
    cameras = {
        "laptop": OpenCVCamera(camera_index=0, fps=30, width=640, height=480),
        "phone": OpenCVCamera(camera_index=1, fps=30, width=640, height=480),
    }
    robot = ManipulatorRobot(KochRobotConfig(cameras=cameras))
    ```

    Once the robot is instantiated, connect motors buses and cameras if any (Required):
    ```python
    robot.connect()
    ```

    Example of highest frequency teleoperation, which doesn't require cameras:
    ```python
    while True:
        robot.teleop_step()
    ```

    Example of highest frequency data collection from motors and cameras (if any):
    ```python
    while True:
        observation, action = robot.teleop_step(record_data=True)
    ```

    Example of controlling the robot with a policy:
    ```python
    while True:
        # Uses the follower arms and cameras to capture an observation
        observation = robot.capture_observation()

        # Assumes a policy has been instantiated
        with torch.inference_mode():
            action = policy.select_action(observation)

        # Orders the robot to move
        robot.send_action(action)
    ```

    Example of disconnecting which is not mandatory since we disconnect when the object is deleted:
    ```python
    robot.disconnect()
    ```
    """

    def __init__(
        self,
        config: ManipulatorRobotConfig,
    ):
        self.config = config
        self.robot_type = self.config.type
        self.calibration_dir = Path(self.config.calibration_dir)
        self.leader_arms = make_motors_buses_from_configs(self.config.leader_arms)
        self.follower_arms = make_motors_buses_from_configs(self.config.follower_arms)
        self.cameras = make_cameras_from_configs(self.config.cameras)
        self.is_connected = False
        self.logs = {}

        # Initialize keyboard controller and GUI
        self.keyboard_controller = KeyboardController(self.follower_arms)
        self.gui = RobotGUI(self.keyboard_controller)

    def get_motor_names(self, arm: dict[str, MotorsBus]) -> list:
        return [f"{arm}_{motor}" for arm, bus in arm.items() for motor in bus.motors]

    @property
    def camera_features(self) -> dict:
        cam_ft = {}
        for cam_key, cam in self.cameras.items():
            key = f"observation.images.{cam_key}"
            cam_ft[key] = {
                "shape": (cam.height, cam.width, cam.channels),
                "names": ["height", "width", "channels"],
                "info": None,
            }
        return cam_ft

    @property
    def motor_features(self) -> dict:
        action_names = self.get_motor_names(self.leader_arms)
        state_names = self.get_motor_names(self.leader_arms)
        return {
            "action": {
                "dtype": "float32",
                "shape": (len(action_names),),
                "names": action_names,
            },
            "observation.state": {
                "dtype": "float32",
                "shape": (len(state_names),),
                "names": state_names,
            },
        }

    @property
    def features(self):
        return {**self.motor_features, **self.camera_features}

    @property
    def has_camera(self):
        return len(self.cameras) > 0

    @property
    def num_cameras(self):
        return len(self.cameras)

    @property
    def available_arms(self):
        available_arms = []
        for name in self.follower_arms:
            arm_id = get_arm_id(name, "follower")
            available_arms.append(arm_id)
        for name in self.leader_arms:
            arm_id = get_arm_id(name, "leader")
            available_arms.append(arm_id)
        return available_arms

    def connect(self):
        if self.is_connected:
            raise RobotDeviceAlreadyConnectedError(
                "ManipulatorRobot is already connected. Do not run `robot.connect()` twice."
            )

        if not self.leader_arms and not self.follower_arms and not self.cameras:
            raise ValueError(
                "ManipulatorRobot doesn't have any device to connect. See example of usage in docstring of the class."
            )

        # Connect the arms
        for name in self.follower_arms:
            print(f"Connecting {name} follower arm.")
            self.follower_arms[name].connect()
        if self.leader_arms:  # Only connect leader arms if they exist
            for name in self.leader_arms:
                print(f"Connecting {name} leader arm.")
                self.leader_arms[name].connect()

        if self.robot_type in ["koch", "koch_bimanual", "aloha"]:
            from lerobot.common.robot_devices.motors.dynamixel import TorqueMode
        elif self.robot_type in ["so100", "so101", "moss", "lekiwi"]:
            from lerobot.common.robot_devices.motors.feetech import TorqueMode

        # We assume that at connection time, arms are in a rest position, and torque can
        # be safely disabled to run calibration and/or set robot preset configurations.
        for name in self.follower_arms:
            self.follower_arms[name].write("Torque_Enable", TorqueMode.DISABLED.value)
        for name in self.leader_arms:
            self.leader_arms[name].write("Torque_Enable", TorqueMode.DISABLED.value)

        self.activate_calibration()

        # Set robot preset (e.g. torque in leader gripper for Koch v1.1)
        if self.robot_type in ["koch", "koch_bimanual"]:
            self.set_koch_robot_preset()
        elif self.robot_type == "aloha":
            self.set_aloha_robot_preset()
        elif self.robot_type in ["so100", "so101", "moss", "lekiwi"]:
            self.set_so100_robot_preset()

        # Enable torque on all motors of the follower arms
        for name in self.follower_arms:
            print(f"Activating torque on {name} follower arm.")
            self.follower_arms[name].write("Torque_Enable", 1)

        if self.config.gripper_open_degree is not None:
            if self.robot_type not in ["koch", "koch_bimanual"]:
                raise NotImplementedError(
                    f"{self.robot_type} does not support position AND current control in the handle, which is require to set the gripper open."
                )
            # Set the leader arm in torque mode with the gripper motor set to an angle. This makes it possible
            # to squeeze the gripper and have it spring back to an open position on its own.
            for name in self.leader_arms:
                self.leader_arms[name].write("Torque_Enable", 1, "gripper")
                self.leader_arms[name].write("Goal_Position", self.config.gripper_open_degree, "gripper")

        # Check both arms can be read
        for name in self.follower_arms:
            self.follower_arms[name].read("Present_Position")
        for name in self.leader_arms:
            self.leader_arms[name].read("Present_Position")

        # Connect the cameras
        for name in self.cameras:
            self.cameras[name].connect()

        # Initialize target positions with current positions for keyboard control
        for name in self.follower_arms:
            current_pos = self.follower_arms[name].read("Present_Position")
            current_pos = torch.from_numpy(current_pos)
            self.keyboard_controller.initialize_target_positions({name: current_pos})

        self.is_connected = True

    def activate_calibration(self):
        """After calibration all motors function in human interpretable ranges.
        Rotations are expressed in degrees in nominal range of [-180, 180],
        and linear motions (like gripper of Aloha) in nominal range of [0, 100].
        """

        def load_or_run_calibration_(name, arm, arm_type):
            arm_id = get_arm_id(name, arm_type)
            arm_calib_path = self.calibration_dir / f"{arm_id}.json"

            if arm_calib_path.exists():
                with open(arm_calib_path) as f:
                    calibration = json.load(f)
            else:
                # TODO(rcadene): display a warning in __init__ if calibration file not available
                print(f"Missing calibration file '{arm_calib_path}'")

                if self.robot_type in ["koch", "koch_bimanual", "aloha"]:
                    from lerobot.common.robot_devices.robots.dynamixel_calibration import run_arm_calibration

                    calibration = run_arm_calibration(arm, self.robot_type, name, arm_type)

                elif self.robot_type in ["so100", "so101", "moss", "lekiwi"]:
                    from lerobot.common.robot_devices.robots.feetech_calibration import (
                        run_arm_manual_calibration,
                    )

                    calibration = run_arm_manual_calibration(arm, self.robot_type, name, arm_type)

                print(f"Calibration is done! Saving calibration file '{arm_calib_path}'")
                arm_calib_path.parent.mkdir(parents=True, exist_ok=True)
                with open(arm_calib_path, "w") as f:
                    json.dump(calibration, f)

            return calibration

        for name, arm in self.follower_arms.items():
            calibration = load_or_run_calibration_(name, arm, "follower")
            arm.set_calibration(calibration)
        for name, arm in self.leader_arms.items():
            calibration = load_or_run_calibration_(name, arm, "leader")
            arm.set_calibration(calibration)

    def set_koch_robot_preset(self):
        def set_operating_mode_(arm):
            from lerobot.common.robot_devices.motors.dynamixel import TorqueMode

            if (arm.read("Torque_Enable") != TorqueMode.DISABLED.value).any():
                raise ValueError("To run set robot preset, the torque must be disabled on all motors.")

            # Use 'extended position mode' for all motors except gripper, because in joint mode the servos can't
            # rotate more than 360 degrees (from 0 to 4095) And some mistake can happen while assembling the arm,
            # you could end up with a servo with a position 0 or 4095 at a crucial point See [
            # https://emanual.robotis.com/docs/en/dxl/x/x_series/#operating-mode11]
            all_motors_except_gripper = [name for name in arm.motor_names if name != "gripper"]
            if len(all_motors_except_gripper) > 0:
                # 4 corresponds to Extended Position on Koch motors
                arm.write("Operating_Mode", 4, all_motors_except_gripper)

            # Use 'position control current based' for gripper to be limited by the limit of the current.
            # For the follower gripper, it means it can grasp an object without forcing too much even tho,
            # it's goal position is a complete grasp (both gripper fingers are ordered to join and reach a touch).
            # For the leader gripper, it means we can use it as a physical trigger, since we can force with our finger
            # to make it move, and it will move back to its original target position when we release the force.
            # 5 corresponds to Current Controlled Position on Koch gripper motors "xl330-m077, xl330-m288"
            arm.write("Operating_Mode", 5, "gripper")

        for name in self.follower_arms:
            set_operating_mode_(self.follower_arms[name])

            # Set better PID values to close the gap between recorded states and actions
            # TODO(rcadene): Implement an automatic procedure to set optimal PID values for each motor
            
            # Enhanced PID for elbow_flex
            self.follower_arms[name].write("Position_P_Gain", 1500, "elbow_flex")
            self.follower_arms[name].write("Position_I_Gain", 0, "elbow_flex")
            self.follower_arms[name].write("Position_D_Gain", 600, "elbow_flex")
            
            # Strong PID values for shoulder_lift to counteract gravity
            self.follower_arms[name].write("Position_P_Gain", 2000, "shoulder_lift")
            self.follower_arms[name].write("Position_I_Gain", 50, "shoulder_lift")
            self.follower_arms[name].write("Position_D_Gain", 800, "shoulder_lift")
            
            print(f"Enhanced PID settings applied for gravity compensation on {name}")

        if self.config.gripper_open_degree is not None:
            for name in self.leader_arms:
                set_operating_mode_(self.leader_arms[name])

                # Enable torque on the gripper of the leader arms, and move it to 45 degrees,
                # so that we can use it as a trigger to close the gripper of the follower arms.
                self.leader_arms[name].write("Torque_Enable", 1, "gripper")
                self.leader_arms[name].write("Goal_Position", self.config.gripper_open_degree, "gripper")

    def set_aloha_robot_preset(self):
        def set_shadow_(arm):
            # Set secondary/shadow ID for shoulder and elbow. These joints have two motors.
            # As a result, if only one of them is required to move to a certain position,
            # the other will follow. This is to avoid breaking the motors.
            if "shoulder_shadow" in arm.motor_names:
                shoulder_idx = arm.read("ID", "shoulder")
                arm.write("Secondary_ID", shoulder_idx, "shoulder_shadow")

            if "elbow_shadow" in arm.motor_names:
                elbow_idx = arm.read("ID", "elbow")
                arm.write("Secondary_ID", elbow_idx, "elbow_shadow")

        for name in self.follower_arms:
            set_shadow_(self.follower_arms[name])

        for name in self.leader_arms:
            set_shadow_(self.leader_arms[name])

        for name in self.follower_arms:
            # Set a velocity limit of 131 as advised by Trossen Robotics
            self.follower_arms[name].write("Velocity_Limit", 131)

            # Use 'extended position mode' for all motors except gripper, because in joint mode the servos can't
            # rotate more than 360 degrees (from 0 to 4095) And some mistake can happen while assembling the arm,
            # you could end up with a servo with a position 0 or 4095 at a crucial point See [
            # https://emanual.robotis.com/docs/en/dxl/x/x_series/#operating-mode11]
            all_motors_except_gripper = [
                name for name in self.follower_arms[name].motor_names if name != "gripper"
            ]
            if len(all_motors_except_gripper) > 0:
                # 4 corresponds to Extended Position on Aloha motors
                self.follower_arms[name].write("Operating_Mode", 4, all_motors_except_gripper)

            # Use 'position control current based' for follower gripper to be limited by the limit of the current.
            # It can grasp an object without forcing too much even tho,
            # it's goal position is a complete grasp (both gripper fingers are ordered to join and reach a touch).
            # 5 corresponds to Current Controlled Position on Aloha gripper follower "xm430-w350"
            self.follower_arms[name].write("Operating_Mode", 5, "gripper")

            # Note: We can't enable torque on the leader gripper since "xc430-w150" doesn't have
            # a Current Controlled Position mode.

        if self.config.gripper_open_degree is not None:
            warnings.warn(
                f"`gripper_open_degree` is set to {self.config.gripper_open_degree}, but None is expected for Aloha instead",
                stacklevel=1,
            )

    def set_so100_robot_preset(self):
        for name in self.follower_arms:
            # Mode=0 for Position Control
            self.follower_arms[name].write("Mode", 0)
            # Set P_Coefficient to lower value to avoid shakiness (Default is 32)
            self.follower_arms[name].write("P_Coefficient", 16)
            # Set I_Coefficient and D_Coefficient to default value 0 and 32
            self.follower_arms[name].write("I_Coefficient", 0)
            self.follower_arms[name].write("D_Coefficient", 32)
            # Set maximum speed (remove speed limits)
            try:
                self.follower_arms[name].write("Maximum_Speed", 0)  # 0 = no limit
            except:
                pass  # Some motors may not support this parameter
            # Close the write lock so that Maximum_Acceleration gets written to EPROM address,
            # which is mandatory for Maximum_Acceleration to take effect after rebooting.
            self.follower_arms[name].write("Lock", 0)
            # Set Maximum_Acceleration to 254 to speedup acceleration and deceleration of
            # the motors. Note: this configuration is not in the official STS3215 Memory Table
            self.follower_arms[name].write("Maximum_Acceleration", 254)
            self.follower_arms[name].write("Acceleration", 254)

    def teleop_step(
        self, record_data=False, keyboard_control=False, default_mode="leader"
    ) -> None | tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        """Unified teleoperation step that handles both keyboard and leader control"""
        if keyboard_control:
            return self.keyboard_teleop_step(record_data)
        else:
            return self.leader_teleop_step(record_data)

    def keyboard_teleop_step(
        self, record_data=False
    ) -> None | tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        """Dedicated keyboard teleoperation step"""
        if not self.is_connected:
            raise RobotDeviceNotConnectedError(
                "ManipulatorRobot is not connected. You need to run `robot.connect()`."
            )

        # Update GUI for keyboard input
        self.gui.update()
        self.gui.show()
        self.gui.update_mode_display("Keyboard")

        # Read current positions
        current_positions = self._read_current_positions()

        # Calculate goal positions using keyboard controller
        goal_positions = self.keyboard_controller.calculate_goal_positions(current_positions)

        # Apply safety limits
        goal_positions = self._apply_safety_limits(goal_positions)

        # Send goal positions to motors
        follower_goal_pos = self._send_goal_positions(goal_positions)

        # Update GUI speed display
        self.gui.update_speed_display()

        # Display status
        self._display_keyboard_status()

        # Early exit when recording data is not requested
        if not record_data:
            return

        # Read follower position for recording
        follower_pos = self._read_follower_positions_for_recording()

        # Create state and action
        state = torch.cat([follower_pos[name] for name in self.follower_arms])
        action = torch.cat([follower_goal_pos[name] for name in self.follower_arms])

        # Populate output dictionaries
        obs_dict, action_dict = {}, {}
        obs_dict["observation.state"] = state
        action_dict["action"] = action
        for name in self.cameras:
            obs_dict[f"observation.images.{name}"] = self.cameras[name].async_read()

        return obs_dict, action_dict

    def leader_teleop_step(
        self, record_data=False
    ) -> None | tuple[dict[str, torch.Tensor], dict[str, torch.Tensor]]:
        """Dedicated leader arm teleoperation step"""
        if not self.is_connected:
            raise RobotDeviceNotConnectedError(
                "ManipulatorRobot is not connected. You need to run `robot.connect()`."
            )

        # Hide keyboard GUI
        self.gui.hide()
        self.gui.update_mode_display("Leader")

        # Read leader arm positions
        leader_pos = self._read_leader_positions()

        # Send goal position to the follower
        follower_goal_pos = self._send_leader_positions_as_goals(leader_pos)

        # Display status
        print("\rLeader mode - Following leader arm positions", end="", flush=True)

        # Early exit when recording data is not requested
        if not record_data:
            return

        # Read follower position for recording
        follower_pos = self._read_follower_positions_for_recording()

        # Create state and action
        state = torch.cat([follower_pos[name] for name in self.follower_arms])
        action = torch.cat([follower_goal_pos[name] for name in self.follower_arms])

        # Populate output dictionaries
        obs_dict, action_dict = {}, {}
        obs_dict["observation.state"] = state
        action_dict["action"] = action
        for name in self.cameras:
            obs_dict[f"observation.images.{name}"] = self.cameras[name].async_read()

        return obs_dict, action_dict

    def capture_observation(self):
        """The returned observations do not have a batch dimension."""
        if not self.is_connected:
            raise RobotDeviceNotConnectedError(
                "ManipulatorRobot is not connected. You need to run `robot.connect()`."
            )

        # Read follower position
        follower_pos = {}
        for name in self.follower_arms:
            before_fread_t = time.perf_counter()
            follower_pos[name] = self.follower_arms[name].read("Present_Position")
            follower_pos[name] = torch.from_numpy(follower_pos[name])
            self.logs[f"read_follower_{name}_pos_dt_s"] = time.perf_counter() - before_fread_t

        # Create state by concatenating follower current position
        state = []
        for name in self.follower_arms:
            if name in follower_pos:
                state.append(follower_pos[name])
        state = torch.cat(state)

        # Capture images from cameras
        images = {}
        for name in self.cameras:
            before_camread_t = time.perf_counter()
            images[name] = self.cameras[name].async_read()
            images[name] = torch.from_numpy(images[name])
            self.logs[f"read_camera_{name}_dt_s"] = self.cameras[name].logs["delta_timestamp_s"]
            self.logs[f"async_read_camera_{name}_dt_s"] = time.perf_counter() - before_camread_t

        # Populate output dictionaries and format to pytorch
        obs_dict = {}
        obs_dict["observation.state"] = state
        for name in self.cameras:
            obs_dict[f"observation.images.{name}"] = images[name]
        return obs_dict

    def send_action(self, action: torch.Tensor) -> torch.Tensor:
        """Command the follower arms to move to a target joint configuration.

        The relative action magnitude may be clipped depending on the configuration parameter
        `max_relative_target`. In this case, the action sent differs from original action.
        Thus, this function always returns the action actually sent.

        Args:
            action: tensor containing the concatenated goal positions for the follower arms.
        """
        if not self.is_connected:
            raise RobotDeviceNotConnectedError(
                "ManipulatorRobot is not connected. You need to run `robot.connect()`."
            )

        from_idx = 0
        to_idx = 0
        action_sent = []
        for name in self.follower_arms:
            # Get goal position of each follower arm by splitting the action vector
            to_idx += len(self.follower_arms[name].motor_names)
            goal_pos = action[from_idx:to_idx]
            from_idx = to_idx

            # Apply absolute position limits first (disabled by user request)
            goal_pos = ensure_absolute_position_limits(goal_pos, self.follower_arms[name].motor_names, self.robot_type)

            # Cap goal position when too far away from present position.
            # Completely disabled by user request - no movement restrictions
            # if self.config.max_relative_target is not None:
            #     present_pos = self.follower_arms[name].read("Present_Position")
            #     present_pos = torch.from_numpy(present_pos)
            #     goal_pos = ensure_safe_goal_position(goal_pos, present_pos, self.config.max_relative_target)

            # Save tensor to concat and return
            action_sent.append(goal_pos)

            # Send goal position to each follower
            goal_pos = goal_pos.numpy().astype(np.float32)
            self.follower_arms[name].write("Goal_Position", goal_pos)

        return torch.cat(action_sent)

    def print_logs(self):
        pass
        # TODO(aliberts): move robot-specific logs logic here

    def disconnect(self):
        if not self.is_connected:
            raise RobotDeviceNotConnectedError(
                "ManipulatorRobot is not connected. You need to run `robot.connect()` before disconnecting."
            )

        for name in self.follower_arms:
            self.follower_arms[name].disconnect()

        if self.leader_arms:  # Only disconnect leader arms if they exist
            for name in self.leader_arms:
                self.leader_arms[name].disconnect()

        for name in self.cameras:
            self.cameras[name].disconnect()

        # Destroy GUI
        self.gui.destroy()

        self.is_connected = False

    def _read_current_positions(self):
        """Read current positions from all follower arms."""
        current_positions = {}
        for name in self.follower_arms:
            before_fread_t = time.perf_counter()
            current_pos = self.follower_arms[name].read("Present_Position")
            current_pos = torch.from_numpy(current_pos)
            self.logs[f"read_follower_{name}_pos_dt_s"] = time.perf_counter() - before_fread_t
            current_positions[name] = current_pos
        return current_positions

    def _read_leader_positions(self):
        """Read current positions from all leader arms."""
        leader_pos = {}
        for name in self.leader_arms:
            before_lread_t = time.perf_counter()
            leader_pos[name] = self.leader_arms[name].read("Present_Position")
            leader_pos[name] = torch.from_numpy(leader_pos[name])
            self.logs[f"read_leader_{name}_pos_dt_s"] = time.perf_counter() - before_lread_t
        return leader_pos

    def _apply_safety_limits(self, goal_positions):
        """Apply safety limits to goal positions."""
        limited_positions = {}
        for name, goal_pos in goal_positions.items():
            # Apply absolute position limits (disabled by user request)
            limited_pos = ensure_absolute_position_limits(
                goal_pos, self.follower_arms[name].motor_names, self.robot_type
            )
            # Apply relative movement limits if configured (completely disabled by user request)
            # max_relative_target is set to None, so this check is completely disabled
            limited_positions[name] = limited_pos
        return limited_positions

    def _send_goal_positions(self, goal_positions):
        """Send goal positions to follower arms."""
        follower_goal_pos = {}
        for name in self.follower_arms:
            before_fwrite_t = time.perf_counter()
            goal_pos = goal_positions[name]

            follower_goal_pos[name] = goal_pos
            goal_pos_np = goal_pos.numpy().astype(np.float32)
            self.follower_arms[name].write("Goal_Position", goal_pos_np)
            self.logs[f"write_follower_{name}_goal_pos_dt_s"] = time.perf_counter() - before_fwrite_t

        # Check motor torque status
        self._check_motor_torque_status()
        return follower_goal_pos

    def _send_leader_positions_as_goals(self, leader_pos):
        """Send leader positions as goals to follower arms."""
        follower_goal_pos = {}
        for name in self.follower_arms:
            before_fwrite_t = time.perf_counter()
            goal_pos = leader_pos.get(name, self.follower_arms[name].read("Present_Position"))
            if not isinstance(goal_pos, torch.Tensor):
                goal_pos = torch.from_numpy(goal_pos)

            # Apply safety limits
            goal_pos = self._apply_safety_limits({name: goal_pos})[name]

            follower_goal_pos[name] = goal_pos
            goal_pos_np = goal_pos.numpy().astype(np.float32)
            self.follower_arms[name].write("Goal_Position", goal_pos_np)
            self.logs[f"write_follower_{name}_goal_pos_dt_s"] = time.perf_counter() - before_fwrite_t

        # Check motor torque status
        self._check_motor_torque_status()
        return follower_goal_pos

    def _check_motor_torque_status(self):
        """Check and display motor torque status."""
        for name in self.follower_arms:
            try:
                torque_status = self.follower_arms[name].read("Torque_Enable")
                print(f"Motor {name} torque status: {torque_status}")
            except Exception as e:
                print(f"Error reading torque status for {name}: {e}")

    def _display_keyboard_status(self):
        """Display keyboard control status."""
        print(f"\rKeyboard mode - {self.keyboard_controller.get_speed_display_text().replace('Speed: ', '')} - Pressed keys: {list(self.keyboard_controller.pressed_keys)}", end="", flush=True)

    def _read_follower_positions_for_recording(self):
        """Read follower positions for data recording."""
        follower_pos = {}
        for name in self.follower_arms:
            before_fread_t = time.perf_counter()
            follower_pos[name] = self.follower_arms[name].read("Present_Position")
            follower_pos[name] = torch.from_numpy(follower_pos[name])
            self.logs[f"read_follower_{name}_pos_dt_s"] = time.perf_counter() - before_fread_t
        return follower_pos

    def __del__(self):
        if getattr(self, "is_connected", False):
            self.disconnect()
