from functools import cached_property

from lerobot.cameras import make_cameras_from_configs
from lerobot.types import RobotAction, RobotObservation
from lerobot.utils.decorators import check_if_already_connected, check_if_not_connected

from . import PiperRobotConfig
from lerobot.robots import Robot


class PiperRobot(Robot):
    config_class = PiperRobotConfig
    name = "piper"

    def __init__(self, config: PiperRobotConfig):
        super().__init__(config)
        self.config = config
        self.cameras = make_cameras_from_configs(config.cameras)
        self._connected = False

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
        return self._connected and all(cam.is_connected for cam in self.cameras.values())

    @check_if_already_connected
    def connect(self, calibrate: bool = True) -> None:
        del calibrate  # Calibration behavior is not implemented yet.
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

    @check_if_not_connected
    def get_observation(self) -> RobotObservation:
        raise NotImplementedError("Piper observation interface is not implemented yet.")

    @check_if_not_connected
    def send_action(self, action: RobotAction) -> RobotAction:
        del action
        raise NotImplementedError("Piper control interface is not implemented yet.")

    @check_if_not_connected
    def disconnect(self) -> None:
        for cam in self.cameras.values():
            cam.disconnect()
        self._connected = False
