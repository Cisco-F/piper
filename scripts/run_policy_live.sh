#!/usr/bin/env bash
set -euo pipefail

POLICY_PATH="${POLICY_PATH:-outputs/train/act_piper_pick_cube/checkpoints/last/pretrained_model}"
REPO_ID="${REPO_ID:-local/piper_pick_cube}"
DATASET_ROOT="${DATASET_ROOT:-data/lerobot/local/piper_pick_cube}"
VIDEO_BACKEND="${VIDEO_BACKEND:-pyav}"
TASK="${TASK:-pick_cube}"
DURATION="${DURATION:-10}"
FPS="${FPS:-10}"
DEVICE="${DEVICE:-cuda}"
EXECUTE="${EXECUTE:-false}"

FOLLOWER_LEFT_CAN="${FOLLOWER_LEFT_CAN:-can2}"
FOLLOWER_RIGHT_CAN="${FOLLOWER_RIGHT_CAN:-can0}"

# Current verified camera mapping:
# OpenCV 2 -> top view, OpenCV 4 -> left view, OpenCV 0 -> right view.
CAMERA_INDICES="${CAMERA_INDICES:-2,4,0}"
CAMERA_NAMES="${CAMERA_NAMES:-cam_top,cam_left,cam_right}"
CAMERA_WIDTH="${CAMERA_WIDTH:-640}"
CAMERA_HEIGHT="${CAMERA_HEIGHT:-480}"
CAMERA_FPS="${CAMERA_FPS:-30}"

CONTROL_SPEED="${CONTROL_SPEED:-10}"
MAX_JOINT_STEP_RAD="${MAX_JOINT_STEP_RAD:-0.025}"
MAX_GRIPPER_STEP_M="${MAX_GRIPPER_STEP_M:-0.001}"
SMOOTHING_ALPHA="${SMOOTHING_ALPHA:-0.25}"
PACE_BY_REACH="${PACE_BY_REACH:-false}"
ADVANCE_THRESHOLD_RAD="${ADVANCE_THRESHOLD_RAD:-0.08}"
MAX_HOLD_STEPS="${MAX_HOLD_STEPS:-30}"
PRINT_EVERY="${PRINT_EVERY:-1}"
LOG_JSONL="${LOG_JSONL:-}"

args=(
  run_policy_live.py
  --policy-path "$POLICY_PATH"
  --repo-id "$REPO_ID"
  --dataset-root "$DATASET_ROOT"
  --video-backend "$VIDEO_BACKEND"
  --task "$TASK"
  --duration "$DURATION"
  --fps "$FPS"
  --device "$DEVICE"
  --follower-left-can "$FOLLOWER_LEFT_CAN"
  --follower-right-can "$FOLLOWER_RIGHT_CAN"
  --camera-indices "$CAMERA_INDICES"
  --camera-names "$CAMERA_NAMES"
  --camera-width "$CAMERA_WIDTH"
  --camera-height "$CAMERA_HEIGHT"
  --camera-fps "$CAMERA_FPS"
  --control-speed "$CONTROL_SPEED"
  --max-joint-step-rad "$MAX_JOINT_STEP_RAD"
  --max-gripper-step-m "$MAX_GRIPPER_STEP_M"
  --smoothing-alpha "$SMOOTHING_ALPHA"
  --advance-threshold-rad "$ADVANCE_THRESHOLD_RAD"
  --max-hold-steps "$MAX_HOLD_STEPS"
  --print-every "$PRINT_EVERY"
)

if [[ "$PACE_BY_REACH" == "true" ]]; then
  args+=(--pace-by-reach)
fi

if [[ -n "$LOG_JSONL" ]]; then
  args+=(--log-jsonl "$LOG_JSONL")
fi

if [[ "$EXECUTE" == "true" ]]; then
  args+=(--execute)
fi

python "${args[@]}"
