import argparse
from pathlib import Path

import cv2


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_camera_ref(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe OpenCV cameras and save snapshots.")
    parser.add_argument(
        "--indices",
        default="0,1,2,3,4,5",
        help="Comma-separated camera indices or paths to test.",
    )
    parser.add_argument("--output-dir", default="data/camera_probe", help="Snapshot output directory.")
    parser.add_argument("--width", type=int, default=640, help="Requested capture width.")
    parser.add_argument("--height", type=int, default=480, help="Requested capture height.")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for camera_ref in parse_csv(args.indices):
        capture = cv2.VideoCapture(parse_camera_ref(camera_ref))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

        ok, frame = capture.read()
        capture.release()

        if not ok or frame is None:
            print(f"{camera_ref}: failed")
            continue

        safe_name = camera_ref.replace("/", "_")
        image_path = output_dir / f"camera_{safe_name}.jpg"
        cv2.imwrite(str(image_path), frame)
        print(f"{camera_ref}: ok -> {image_path}")


if __name__ == "__main__":
    main()
