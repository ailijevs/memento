#!/usr/bin/env python3
"""Encode a JPG/JPEG from backend/data to base64 and write it in backend/."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path


DEFAULT_OUTPUT_NAME = "image_base64.txt"


def _find_default_input(data_dir: Path) -> Path:
    candidates = sorted(
        p for p in data_dir.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}
    )
    if not candidates:
        raise FileNotFoundError(f"No .jpg/.jpeg file found in {data_dir}")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a JPG/JPEG from backend/data to a base64-encoded string file in backend/."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional path to a specific image file. Defaults to first JPG/JPEG in backend/data.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Optional output file path. Defaults to backend/{DEFAULT_OUTPUT_NAME}.",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    data_dir = backend_dir / "data"

    input_path = args.input if args.input else _find_default_input(data_dir)
    if not input_path.is_absolute():
        input_path = (Path.cwd() / input_path).resolve()

    if not input_path.exists() or not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    output_path = args.output if args.output else (backend_dir / DEFAULT_OUTPUT_NAME)
    if not output_path.is_absolute():
        output_path = (Path.cwd() / output_path).resolve()

    encoded = base64.b64encode(input_path.read_bytes()).decode("utf-8")
    output_path.write_text(encoded, encoding="utf-8")

    print(f"Encoded: {input_path}")
    print(f"Wrote:   {output_path}")
    print(f"Bytes:   {len(encoded)} characters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
