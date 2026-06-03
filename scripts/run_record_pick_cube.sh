#!/usr/bin/env bash
set -euo pipefail

TASK="${TASK:-pick_cube}"
REPO_ID="${REPO_ID:-local/piper_pick_cube}"
ROOT="${ROOT:-data/lerobot}"
FPS="${FPS:-10}"

FOLLOWER_LEFT_CAN="${FOLLOWER_LEFT_CAN:-can2}"
FOLLOWER_RIGHT_CAN="${FOLLOWER_RIGHT_CAN:-can0}"
LEADER_LEFT_CAN="${LEADER_LEFT_CAN:-}"
LEADER_RIGHT_CAN="${LEADER_RIGHT_CAN:-}"
ACTION_SOURCE="${ACTION_SOURCE:-auto}"

# Current verified camera mapping:
# OpenCV 2 -> top view, OpenCV 4 -> left view, OpenCV 0 -> right view.
CAMERA_INDICES="${CAMERA_INDICES:-2,4,0}"
CAMERA_NAMES="${CAMERA_NAMES:-cam_top,cam_left,cam_right}"
CAMERA_WIDTH="${CAMERA_WIDTH:-640}"
CAMERA_HEIGHT="${CAMERA_HEIGHT:-480}"
CAMERA_FPS="${CAMERA_FPS:-30}"

args=(
  record_episode.py
  --task "$TASK"
  --dataset-format lerobot
  --repo-id "$REPO_ID"
  --root "$ROOT"
  --follower-left-can "$FOLLOWER_LEFT_CAN"
  --follower-right-can "$FOLLOWER_RIGHT_CAN"
  --action-source "$ACTION_SOURCE"
  --camera-indices "$CAMERA_INDICES"
  --camera-names "$CAMERA_NAMES"
  --camera-width "$CAMERA_WIDTH"
  --camera-height "$CAMERA_HEIGHT"
  --camera-fps "$CAMERA_FPS"
  --fps "$FPS"
  --prompt-outcome
)

if [[ -n "$LEADER_LEFT_CAN" ]]; then
  args+=(--leader-left-can "$LEADER_LEFT_CAN")
fi

if [[ -n "$LEADER_RIGHT_CAN" ]]; then
  args+=(--leader-right-can "$LEADER_RIGHT_CAN")
fi

python "${args[@]}"
