from functools import cached_property
import math

import numpy as np
from lerobot.cameras import make_cameras_from_configs
from lerobot.types import RobotAction, RobotObservation
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from lerobot.robots import Robot

try:
    from . import PiperRobotConfig
except ImportError:
    from __init__ import PiperRobotConfig

try:
    from piper_sdk import C_PiperInterface_V2
except ImportError:
    try:
        from piper_sdk import C_PiperInterface as C_PiperInterface_V2
    except ImportError:
        C_PiperInterface_V2 = None


class PiperRobot(Robot):
    config_class = PiperRobotConfig
    name = "piper"

    def __init__(self, config: PiperRobotConfig):
        super().__init__(config)
        self.config = config
        self.cameras = make_cameras_from_configs(config.cameras)
        self._connected = False
        self._followers: dict[str, object | None] = {"left": None, "right": None}

    @property
    def _arm_joint_names(self) -> list[str]:
        return [f"joint_{i}" for i in range(1, 7)]

    @property
    def _motors_ft(self) -> dict[str, type]:
        features: dict[str, type] = {}
        for side in ("left", "right"):
            for joint_name in self._arm_joint_names:
                features[f"{side}_{joint_name}.pos"] = float
            features[f"{side}_gripper.pos"] = float
        return features

    @property
    def _cameras_ft(self) -> dict[str, tuple[int, int, int]]:
        return {
            name: (camera_cfg.height, camera_cfg.width, 3)
            for name, camera_cfg in self.config.cameras.items()
        }

    @cached_property
    def observation_features(self) -> dict[str, type | tuple[int, int, int]]:
        return {**self._motors_ft, **self._cameras_ft}

    @cached_property
    def action_features(self) -> dict[str, type]:
        return self._motors_ft

    @property
    def is_connected(self) -> bool:
        cameras_connected = all(cam.is_connected for cam in self.cameras.values())
        arms_connected = all(
            arm is None or self._sdk_arm_is_connected(arm) for arm in self._followers.values()
        )
        return self._connected and cameras_connected and arms_connected

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        del calibrate  # Calibration behavior is not implemented yet.
        self._followers["left"] = self._make_follower(self.config.follower_left_port)
        self._followers["right"] = self._make_follower(self.config.follower_right_port)

        for cam in self.cameras.values():
            cam.connect()
        self._connected = True

    @property
    def is_calibrated(self) -> bool:
        return True

    def calibrate(self) -> None:
        return None

    def configure(self) -> None:
        return None

    def _make_follower(self, can_name: str | None) -> object | None:
        if can_name is None:
            return None

        if C_PiperInterface_V2 is None:
            raise ImportError("piper_sdk is not installed in the current Python environment.")

        arm = C_PiperInterface_V2(can_name=can_name)
        arm.ConnectPort()
        return arm

    def _sdk_arm_is_connected(self, arm: object) -> bool:
        get_status = getattr(arm, "get_connect_status", None)
        if callable(get_status):
            return bool(get_status())
        return True

    def _read_joint_positions(self, arm: object | None) -> list[float]:
        if arm is None:
            return [0.0] * 6

        joint_state = arm.GetArmJointMsgs().joint_state
        joints_mdeg = [
            joint_state.joint_1,
            joint_state.joint_2,
            joint_state.joint_3,
            joint_state.joint_4,
            joint_state.joint_5,
            joint_state.joint_6,
        ]
        return [math.radians(value / 1000.0) for value in joints_mdeg]

    def _read_gripper_position(self, arm: object | None) -> float:
        if arm is None:
            return 0.0

        gripper_state = arm.GetArmGripperMsgs().gripper_state
        return gripper_state.grippers_angle / 1_000_000.0

    @check_if_not_connected
    def get_observation(self) -> RobotObservation:
        observation: RobotObservation = {}

        for side in ("left", "right"):
            joints = self._read_joint_positions(self._followers[side])
            for index, position in enumerate(joints, start=1):
                observation[f"{side}_joint_{index}.pos"] = position
            observation[f"{side}_gripper.pos"] = self._read_gripper_position(self._followers[side])

        for camera_name, (height, width, channels) in self._cameras_ft.items():
            camera = self.cameras[camera_name]
            try:
                observation[camera_name] = camera.read_latest()
            except Exception:
                observation[camera_name] = np.zeros((height, width, channels), dtype=np.uint8)

        return observation

    @check_if_not_connected
    def send_action(self, action: RobotAction) -> RobotAction:
        del action
        raise NotImplementedError("Piper control interface is not implemented yet.")

    @check_if_not_connected
    def disconnect(self) -> None:
        for cam in self.cameras.values():
            cam.disconnect()
        self._connected = False
