import argparse
import inspect
import subprocess
import time
from typing import Any


def import_piper_interface() -> tuple[Any, type]:
    import piper_sdk

    interface_cls = getattr(piper_sdk, "C_PiperInterface_V2", None)
    if interface_cls is None:
        interface_cls = getattr(piper_sdk, "C_PiperInterface")
    return piper_sdk, interface_cls


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def print_signature(cls: type, method_name: str) -> None:
    method = getattr(cls, method_name, None)
    if method is None:
        print(f"  {method_name}: missing")
        return

    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        signature = "<signature unavailable>"
    print(f"  {method_name}: {signature}")


def run_command(args: list[str]) -> None:
    print(f"$ {' '.join(args)}")
    result = subprocess.run(args, check=False, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip())
    print(f"exit code: {result.returncode}")


def call_connect_port(arm: Any, piper_init: bool) -> None:
    connect_port = getattr(arm, "ConnectPort")
    try:
        connect_port(piper_init=piper_init)
    except TypeError:
        connect_port()


def diagnose_arm(interface_cls: type, can_name: str, piper_init: bool) -> None:
    print(f"=== {can_name} ===")
    try:
        arm = interface_cls(can_name=can_name)
        print("constructed interface")
    except Exception as exc:
        print(f"constructor failed: {exc!r}")
        return

    try:
        call_connect_port(arm, piper_init=piper_init)
        print(f"ConnectPort(piper_init={piper_init}) returned")
    except Exception as exc:
        print(f"ConnectPort failed: {exc!r}")

    time.sleep(0.5)

    for method_name in ("GetArmStatus", "GetArmJointMsgs", "GetArmGripperMsgs"):
        method = getattr(arm, method_name, None)
        if not callable(method):
            print(f"{method_name}: missing")
            continue
        try:
            print(f"{method_name}: {method()}")
        except Exception as exc:
            print(f"{method_name} failed: {exc!r}")

    disconnect = getattr(arm, "DisconnectPort", None)
    if callable(disconnect):
        try:
            disconnect()
        except Exception as exc:
            print(f"DisconnectPort failed: {exc!r}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose the installed piper_sdk and CAN state.")
    parser.add_argument("--can", default="can2,can0")
    parser.add_argument("--piper-init", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    piper_sdk, interface_cls = import_piper_interface()

    print("piper_sdk:")
    print(f"  file: {getattr(piper_sdk, '__file__', '<unknown>')}")
    print(f"  version: {getattr(piper_sdk, '__version__', '<unknown>')}")
    print(f"  interface class: {interface_cls}")
    print()

    print("interface signatures:")
    for method_name in (
        "__init__",
        "ConnectPort",
        "MotionCtrl_1",
        "MotionCtrl_2",
        "ResetPiper",
        "EnableArm",
        "DisableArm",
        "JointCtrl",
        "GripperCtrl",
        "EmergencyStop",
    ):
        print_signature(interface_cls, method_name)
    print()

    for can_name in parse_csv(args.can):
        run_command(["ip", "-details", "-statistics", "link", "show", can_name])
        diagnose_arm(interface_cls, can_name, args.piper_init)
        print()


if __name__ == "__main__":
    main()
