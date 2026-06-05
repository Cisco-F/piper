import argparse
import json
from pathlib import Path
from typing import Any

import torch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline inference from a local LeRobot checkpoint.")
    parser.add_argument(
        "--policy-path",
        default="outputs/train/act_piper_pick_cube/checkpoints/last/pretrained_model",
        help="Path to the local pretrained_model checkpoint directory.",
    )
    parser.add_argument(
        "--repo-id",
        default="local/piper_pick_cube",
        help="Dataset repo id used during training.",
    )
    parser.add_argument(
        "--dataset-root",
        default="data/lerobot/local/piper_pick_cube",
        help="Path to the dataset directory that contains meta/info.json.",
    )
    parser.add_argument("--episode-index", type=int, default=0, help="Episode index to inspect.")
    parser.add_argument(
        "--frame-offset",
        type=int,
        default=0,
        help="Frame offset inside the selected episode.",
    )
    parser.add_argument(
        "--num-frames",
        type=int,
        default=5,
        help="How many consecutive frames to run through the policy.",
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Inference device.",
    )
    parser.add_argument(
        "--video-backend",
        default="pyav",
        choices=("pyav", "torchcodec"),
        help="Video backend for loading dataset frames.",
    )
    parser.add_argument(
        "--save-json",
        default="",
        help="Optional path to save inference outputs as JSON.",
    )
    return parser.parse_args()


def import_lerobot_dataset() -> type:
    for module_name in ("lerobot.datasets", "lerobot.datasets.lerobot_dataset"):
        try:
            module = __import__(module_name, fromlist=["LeRobotDataset"])
        except ImportError:
            continue
        dataset_cls = getattr(module, "LeRobotDataset", None)
        if dataset_cls is not None:
            return dataset_cls
    raise ImportError("Could not import LeRobotDataset from the current lerobot installation.")


def load_policy(policy_path: str, device: str):
    from lerobot.configs import PreTrainedConfig
    from lerobot.policies import get_policy_class, make_pre_post_processors

    config = PreTrainedConfig.from_pretrained(policy_path)
    config.pretrained_path = policy_path
    config.device = device

    policy_class = get_policy_class(config.type)
    policy = policy_class.from_pretrained(policy_path, config=config)
    policy.eval()
    policy.to(device)

    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=config,
        pretrained_path=policy_path,
        dataset_stats=None,
        preprocessor_overrides={"device_processor": {"device": device}},
    )
    return config, policy, preprocessor, postprocessor


def load_dataset(repo_id: str, dataset_root: str, video_backend: str):
    dataset_cls = import_lerobot_dataset()
    return dataset_cls(repo_id=repo_id, root=dataset_root, video_backend=video_backend)


def get_episode_bounds(dataset: Any, episode_index: int) -> tuple[int, int]:
    episodes = dataset.meta.episodes
    from_indices = episodes["dataset_from_index"]
    to_indices = episodes.get("dataset_to_index")

    start = int(from_indices[episode_index])
    if to_indices is not None:
        stop = int(to_indices[episode_index])
    elif episode_index + 1 < len(from_indices):
        stop = int(from_indices[episode_index + 1])
    else:
        stop = len(dataset)

    return start, stop


def select_policy_inputs(sample: dict[str, Any]) -> dict[str, Any]:
    ignored_keys = {
        "action",
        "timestamp",
        "frame_index",
        "episode_index",
        "index",
        "task_index",
        "next.reward",
        "next.done",
    }
    batch: dict[str, Any] = {}
    for key, value in sample.items():
        if key in ignored_keys:
            continue
        if key.startswith("next."):
            continue
        batch[key] = value
    return batch


def action_tensor_to_dict(action_tensor: torch.Tensor, action_names: list[str]) -> dict[str, float]:
    flat = action_tensor.detach().to("cpu").reshape(-1).tolist()
    values = flat[: len(action_names)]
    return {name: float(value) for name, value in zip(action_names, values, strict=True)}


def ground_truth_action_to_dict(sample: dict[str, Any], action_names: list[str]) -> dict[str, float]:
    action = sample.get("action")
    if action is None:
        return {}
    if isinstance(action, torch.Tensor):
        values = action.detach().to("cpu").reshape(-1).tolist()
    else:
        values = list(action)
    values = values[: len(action_names)]
    return {name: float(value) for name, value in zip(action_names, values, strict=True)}


def summarize_action_diff(predicted: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    if not target:
        return {}
    diffs = [abs(predicted[name] - target[name]) for name in predicted if name in target]
    if not diffs:
        return {}
    return {
        "mean_abs_error": sum(diffs) / len(diffs),
        "max_abs_error": max(diffs),
    }


def main() -> None:
    args = parse_args()

    if args.num_frames <= 0:
        raise ValueError("--num-frames must be greater than 0.")
    if args.frame_offset < 0:
        raise ValueError("--frame-offset must be non-negative.")

    dataset = load_dataset(
        repo_id=args.repo_id,
        dataset_root=args.dataset_root,
        video_backend=args.video_backend,
    )
    _, policy, preprocessor, postprocessor = load_policy(args.policy_path, args.device)

    action_feature = dataset.meta.features["action"]
    action_names = list(action_feature["names"])
    episode_start, episode_stop = get_episode_bounds(dataset, args.episode_index)
    frame_start = episode_start + args.frame_offset
    frame_stop = min(frame_start + args.num_frames, episode_stop)

    if frame_start >= episode_stop:
        raise ValueError(
            f"Requested frame starts at {frame_start}, but episode {args.episode_index} ends at {episode_stop}."
        )

    print(f"policy path: {args.policy_path}")
    print(f"dataset root: {args.dataset_root}")
    print(f"episode index: {args.episode_index}")
    print(f"frame range: [{frame_start}, {frame_stop})")
    print(f"device: {args.device}")
    print()

    outputs: list[dict[str, Any]] = []
    policy.reset()

    for frame_index in range(frame_start, frame_stop):
        sample = dict(dataset[frame_index])
        batch = select_policy_inputs(sample)
        processed = preprocessor(batch)

        with torch.inference_mode():
            action = policy.select_action(processed)
            action = postprocessor(action)

        predicted_action = action_tensor_to_dict(action, action_names)
        target_action = ground_truth_action_to_dict(sample, action_names)
        diff_summary = summarize_action_diff(predicted_action, target_action)

        result = {
            "frame_index": frame_index,
            "episode_index": args.episode_index,
            "task": sample.get("task", ""),
            "predicted_action": predicted_action,
            "target_action": target_action,
            "diff_summary": diff_summary,
        }
        outputs.append(result)

        print(f"frame {frame_index}")
        if result["task"]:
            print(f"  task: {result['task']}")
        print("  predicted_action:")
        for name, value in predicted_action.items():
            print(f"    {name}: {value:.6f}")
        if target_action:
            print("  target_action:")
            for name, value in target_action.items():
                print(f"    {name}: {value:.6f}")
        if diff_summary:
            print(
                "  diff:"
                f" mean_abs_error={diff_summary['mean_abs_error']:.6f}"
                f" max_abs_error={diff_summary['max_abs_error']:.6f}"
            )
        print()

    if args.save_json:
        output_path = Path(args.save_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(outputs, indent=2) + "\n", encoding="utf-8")
        print(f"saved json to {output_path}")


if __name__ == "__main__":
    main()
