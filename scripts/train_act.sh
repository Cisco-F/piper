#!/usr/bin/env bash
set -euo pipefail

REPO_ID="${REPO_ID:-local/piper_pick_cube}"
ROOT="${ROOT:-data/lerobot}"
POLICY_TYPE="${POLICY_TYPE:-act}"
JOB_NAME="${JOB_NAME:-${POLICY_TYPE}_piper_pick_cube}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/train/${JOB_NAME}}"
POLICY_REPO_ID="${POLICY_REPO_ID:-local/${JOB_NAME}}"

DEVICE="${DEVICE:-cuda}"
STEPS="${STEPS:-5000}"
BATCH_SIZE="${BATCH_SIZE:-16}"
LOG_FREQ="${LOG_FREQ:-100}"
SAVE_FREQ="${SAVE_FREQ:-1000}"
WANDB_ENABLE="${WANDB_ENABLE:-false}"

DATASET_ROOT="${DATASET_ROOT:-${ROOT}/${REPO_ID}}"

if [[ ! -f "${DATASET_ROOT}/meta/info.json" ]]; then
  echo "Dataset metadata not found: ${DATASET_ROOT}/meta/info.json" >&2
  echo "Set ROOT and REPO_ID, or set DATASET_ROOT to the directory that contains meta/info.json." >&2
  exit 1
fi

if ! find "${DATASET_ROOT}/data" -name "*.parquet" -print -quit >/dev/null 2>&1; then
  echo "No parquet files found under ${DATASET_ROOT}/data." >&2
  echo "LeRobot stores joint states/actions in parquet files; record or finalize the dataset first." >&2
  exit 1
fi

if ! command -v lerobot-train >/dev/null 2>&1; then
  echo "lerobot-train was not found in PATH." >&2
  echo "Activate your LeRobot Python environment first, then rerun this script." >&2
  exit 1
fi

echo "Training ${POLICY_TYPE} policy"
echo "  dataset: ${REPO_ID}"
echo "  dataset root: ${DATASET_ROOT}"
echo "  output: ${OUTPUT_DIR}"
echo "  device: ${DEVICE}"
echo "  steps: ${STEPS}"
echo
echo "If POLICY_TYPE=${POLICY_TYPE} uses a pretrained checkpoint, LeRobot may download it the first time."
echo "For ACT from scratch, the dataset videos/parquet are enough and no robot model is pulled."
echo "Training is finished when the command reaches STEPS=${STEPS} and writes checkpoints under ${OUTPUT_DIR}."
echo

lerobot-train \
  --dataset.repo_id="${REPO_ID}" \
  --dataset.root="${DATASET_ROOT}" \
  --policy.type="${POLICY_TYPE}" \
  --output_dir="${OUTPUT_DIR}" \
  --job_name="${JOB_NAME}" \
  --policy.device="${DEVICE}" \
  --steps="${STEPS}" \
  --batch_size="${BATCH_SIZE}" \
  --log_freq="${LOG_FREQ}" \
  --save_freq="${SAVE_FREQ}" \
  --wandb.enable="${WANDB_ENABLE}" \
  --policy.repo_id="${POLICY_REPO_ID}"
