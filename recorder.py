from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class EpisodeMetadata:
    task: str
    fps: float
    started_at: str
    action_source: str


class PiperEpisodeRecorder:
    def __init__(
        self,
        output_dir: str | Path,
        task: str,
        fps: float,
        action_source: str = "leader",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.task = task
        self.fps = fps
        self.action_source = action_source
        self.episode_dir: Path | None = None
        self.frames_path: Path | None = None
        self._frames_file: Any | None = None
        self._frame_index = 0

    def __enter__(self) -> "PiperEpisodeRecorder":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        episode_name = time.strftime("episode_%Y%m%d_%H%M%S")
        self.episode_dir = self.output_dir / episode_name
        self.episode_dir.mkdir()

        metadata = EpisodeMetadata(
            task=self.task,
            fps=self.fps,
            started_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            action_source=self.action_source,
        )
        metadata_path = self.episode_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(metadata.__dict__, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        self.frames_path = self.episode_dir / "frames.jsonl"
        self._frames_file = self.frames_path.open("w", encoding="utf-8")
        return self.episode_dir

    def record_frame(self, observation: dict[str, Any], action: dict[str, Any]) -> None:
        if self._frames_file is None:
            raise RuntimeError("Recorder has not been started.")

        frame = {
            "frame_index": self._frame_index,
            "timestamp": time.time(),
            "observation": self._json_ready(observation),
            "action": self._json_ready(action),
        }
        self._frames_file.write(json.dumps(frame, ensure_ascii=False) + "\n")
        self._frame_index += 1

    def close(self) -> None:
        if self._frames_file is not None:
            self._frames_file.close()
            self._frames_file = None

    def _json_ready(self, values: dict[str, Any]) -> dict[str, Any]:
        json_values: dict[str, Any] = {}
        for key, value in values.items():
            if isinstance(value, np.ndarray):
                json_values[key] = {
                    "type": "ndarray",
                    "shape": list(value.shape),
                    "dtype": str(value.dtype),
                    "omitted": True,
                }
            elif isinstance(value, np.generic):
                json_values[key] = value.item()
            else:
                json_values[key] = value
        return json_values
