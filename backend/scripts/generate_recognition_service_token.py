#!/usr/bin/env python3
"""Generate a secure random token for RECOGNITION_SERVICE_TOKEN (backend and glasses-app)."""

from __future__ import annotations

import argparse
import base64
import secrets
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Print a random secret suitable for RECOGNITION_SERVICE_TOKEN. "
            "Set the same value in backend/.env and glasses-app/.env."
        )
    )
    parser.add_argument(
        "--bytes",
        type=int,
        default=32,
        metavar="N",
        help="Number of random bytes (default: 32). Larger is stronger but longer.",
    )
    parser.add_argument(
        "--format",
        choices=("hex", "urlsafe"),
        default="hex",
        help="hex: 2N hex chars (default). urlsafe: ~ceil(4N/3) URL-safe base64 chars.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Print only the token (no usage hint on stderr).",
    )
    args = parser.parse_args()

    if args.bytes < 16:
        print("error: use at least 16 bytes for a reasonable secret", file=sys.stderr)
        return 2

    raw = secrets.token_bytes(args.bytes)
    if args.format == "hex":
        token = raw.hex()
    else:
        token = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    print(token)
    if not args.quiet:
        print(
            "\nAdd to backend/.env and glasses-app/.env:\n"
            f"  RECOGNITION_SERVICE_TOKEN={token}\n",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
