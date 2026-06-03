import argparse
import time

from __init__ import PiperRobotConfig
from piper import PiperRobot
from recorder import PiperEpisodeRecorder


def resolve_action_source(args: argparse.Namespace) -> str:
    if args.action_source != "auto":
        return args.action_source

    if args.leader_left_can and args.leader_right_can:
        return "leader"
    return "follower"


def main() -> None:
    parser = argparse.ArgumentParser(description="Record a minimal Piper teleop episode.")
    parser.add_argument("--task", default="pick_cube", help="Task name stored in metadata.")
    parser.add_argument("--output-dir", default="data/raw", help="Directory for recorded episodes.")
    parser.add_argument("--fps", type=float, default=10.0, help="Recording frequency.")
    parser.add_argument("--duration", type=float, default=None, help="Optional duration in seconds.")
    parser.add_argument("--follower-left-can", default="can2", help="Left follower CAN interface.")
    parser.add_argument("--follower-right-can", default="can0", help="Right follower CAN interface.")
    parser.add_argument("--leader-left-can", default=None, help="Left leader CAN interface.")
    parser.add_argument("--leader-right-can", default=None, help="Right leader CAN interface.")
    parser.add_argument(
        "--action-source",
        choices=("auto", "leader", "follower"),
        default="auto",
        help="Use leader joints as actions when available, otherwise follower joints.",
    )
    args = parser.parse_args()

    if args.fps <= 0:
        raise ValueError("--fps must be greater than 0.")

    action_source = resolve_action_source(args)
    if action_source == "leader" and not (args.leader_left_can and args.leader_right_can):
        raise ValueError("Leader action recording requires both --leader-left-can and --leader-right-can.")

    config = PiperRobotConfig(
        leader_left_port=args.leader_left_can,
        leader_right_port=args.leader_right_can,
        follower_left_port=args.follower_left_can,
        follower_right_port=args.follower_right_can,
        cameras={},
    )
    robot = PiperRobot(config)
    period = 1.0 / args.fps
    started_at = time.monotonic()

    try:
        robot.connect()
        with PiperEpisodeRecorder(
            output_dir=args.output_dir,
            task=args.task,
            fps=args.fps,
            action_source=action_source,
        ) as recorder:
            print(f"Recording to {recorder.episode_dir}")
            print("Press Ctrl+C to stop.")
            while True:
                loop_started_at = time.monotonic()
                observation = robot.get_observation()
                if action_source == "leader":
                    action = robot.get_leader_action()
                else:
                    action = {
                        key: value
                        for key, value in observation.items()
                        if key.endswith(".pos")
                    }

                recorder.record_frame(observation=observation, action=action)

                if args.duration is not None and time.monotonic() - started_at >= args.duration:
                    break

                elapsed = time.monotonic() - loop_started_at
                time.sleep(max(0.0, period - elapsed))
    except KeyboardInterrupt:
        print("\nStopping recording.")
    finally:
        if robot.is_connected:
            robot.disconnect()


if __name__ == "__main__":
    main()
