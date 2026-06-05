import argparse
import time
from typing import Any


def import_piper_interface() -> type:
    try:
        from piper_sdk import C_PiperInterface_V2

        return C_PiperInterface_V2
    except ImportError:
        from piper_sdk import C_PiperInterface

        return C_PiperInterface


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def call_connect_port(arm: Any, piper_init: bool) -> None:
    connect_port = getattr(arm, "ConnectPort")
    try:
        connect_port(piper_init=piper_init)
    except TypeError:
        connect_port()


def call_optional(arm: Any, method_name: str, *args: Any) -> bool:
    method = getattr(arm, method_name, None)
    if not callable(method):
        return False

    try:
        method(*args)
    except TypeError:
        method()
    return True


def reset_arm(interface_cls: type, can_name: str, args: argparse.Namespace) -> None:
    print(f"[{can_name}] connecting")
    try:
        arm = interface_cls(can_name=can_name, judge_flag=args.judge_flag)
    except TypeError:
        arm = interface_cls(can_name=can_name)
    call_connect_port(arm, piper_init=args.piper_init)
    time.sleep(args.connect_wait)

    if args.disable_first:
        print(f"[{can_name}] disabling arm before reset")
        if not call_optional(arm, "DisableArm", 7):
            print(f"[{can_name}] DisableArm is not available in this piper_sdk version")
        time.sleep(args.command_wait)

    print(f"[{can_name}] sending ResetPiper")
    if not call_optional(arm, "ResetPiper"):
        raise RuntimeError(
            "This piper_sdk version does not expose ResetPiper(). "
            "Please update piper_sdk or run the official demo piper_reset.py."
        )

    time.sleep(args.command_wait)

    if args.resume_emergency_stop:
        print(f"[{can_name}] sending EmergencyStop resume")
        if not call_optional(arm, "EmergencyStop", 0x02):
            print(f"[{can_name}] EmergencyStop is not available in this piper_sdk version")
        time.sleep(args.command_wait)

    status = getattr(arm, "GetArmStatus", None)
    if callable(status):
        print(f"[{can_name}] status: {status()}")

    disconnect = getattr(arm, "DisconnectPort", None)
    if callable(disconnect):
        disconnect()

    print(f"[{can_name}] reset command sent")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset Piper arms after using teach/drag mode so SDK control can be enabled again."
    )
    parser.add_argument(
        "--can",
        default="can2,can0",
        help="Comma-separated CAN interfaces to reset, e.g. can2,can0.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the safety confirmation prompt.",
    )
    parser.add_argument(
        "--no-disable-first",
        dest="disable_first",
        action="store_false",
        help="Do not call DisableArm before ResetPiper.",
    )
    parser.add_argument(
        "--piper-init",
        action="store_true",
        help="Let ConnectPort run PiperInit. Default is off to avoid limit-query failures after teach mode.",
    )
    parser.add_argument(
        "--judge-flag",
        action="store_true",
        help="Enable piper_sdk CAN-port judging in the interface constructor.",
    )
    parser.add_argument(
        "--resume-emergency-stop",
        action="store_true",
        help="Send EmergencyStop(0x02) after ResetPiper if available.",
    )
    parser.add_argument("--connect-wait", type=float, default=0.5)
    parser.add_argument("--command-wait", type=float, default=1.0)
    parser.set_defaults(disable_first=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    can_names = parse_csv(args.can)
    if not can_names:
        raise ValueError("--can must contain at least one CAN interface.")

    print("WARNING: ResetPiper will make the arm lose power immediately.")
    print("Make sure the arm is supported, clear of people/objects, and you are ready to re-enable it afterward.")
    print(f"CAN interfaces: {', '.join(can_names)}")
    if not args.yes:
        answer = input("Type RESET to continue: ").strip()
        if answer != "RESET":
            print("Canceled.")
            return

    interface_cls = import_piper_interface()
    for can_name in can_names:
        reset_arm(interface_cls, can_name, args)

    print("Done. After reset, try reading state first, then run SDK control/enable again.")


if __name__ == "__main__":
    main()
