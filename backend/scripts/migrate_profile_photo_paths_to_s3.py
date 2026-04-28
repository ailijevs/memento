#!/usr/bin/env python3
"""Migrate profile photo_path values from HTTPS URLs to S3 object keys.

For each profile row where `photo_path` starts with `https://` (or also `http://`
with `--include-http`), this script:
1) downloads the remote image bytes,
2) uploads to the configured S3 bucket using the existing S3Service,
3) updates `profiles.photo_path` to the new S3 key.

Run this from the `backend/` directory.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import get_settings
from app.db.supabase import get_admin_client
from app.services.s3 import S3Service


@dataclass
class MigrationStats:
    scanned: int = 0
    migrated: int = 0
    failed: int = 0
    skipped: int = 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate profiles.photo_path HTTPS URLs to S3 keys."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List rows that would be migrated without uploading/updating.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="How many matching rows to fetch per batch (default: 100).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of rows to process.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=20.0,
        help="HTTP download timeout in seconds (default: 20).",
    )
    parser.add_argument(
        "--include-http",
        action="store_true",
        help="Also migrate values that start with http:// (not only https://).",
    )
    return parser.parse_args()


def fetch_candidates_page(
    client: Any,
    *,
    offset: int,
    batch_size: int,
    include_http: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    https_response = (
        client.table("profiles")
        .select("user_id,photo_path")
        .like("photo_path", "https://%")
        .order("user_id")
        .range(offset, offset + batch_size - 1)
        .limit(batch_size)
        .execute()
    )
    rows.extend(https_response.data or [])

    if include_http and len(rows) < batch_size:
        http_response = (
            client.table("profiles")
            .select("user_id,photo_path")
            .like("photo_path", "http://%")
            .order("user_id")
            .range(offset, offset + (batch_size - len(rows)) - 1)
            .limit(batch_size - len(rows))
            .execute()
        )
        rows.extend(http_response.data or [])

    return rows


def collect_candidates(
    client: Any,
    *,
    batch_size: int,
    include_http: bool,
) -> list[dict[str, Any]]:
    """Snapshot all matching rows before mutation to avoid pagination drift."""
    collected: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = fetch_candidates_page(
            client,
            offset=offset,
            batch_size=batch_size,
            include_http=include_http,
        )
        if not page:
            break
        collected.extend(page)
        offset += len(page)
    return collected


def download_image_bytes(url: str, timeout_seconds: float) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "memento-photo-migration/1.0",
            "Accept": "image/*,*/*;q=0.8",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        data = response.read()
    if not data:
        raise ValueError("Downloaded image is empty.")
    return data


def migrate_row(
    *,
    client: Any,
    s3_service: S3Service,
    bucket_name: str,
    user_id: str,
    photo_url: str,
    timeout_seconds: float,
    dry_run: bool,
) -> str:
    if dry_run:
        print(f"[DRY-RUN] user_id={user_id} photo_path={photo_url}")
        return "dry-run"

    image_bytes = download_image_bytes(photo_url, timeout_seconds)
    new_s3_key = s3_service.upload_profile_picture(
        user_id=user_id,
        image=image_bytes,
        bucket_name=bucket_name,
        source="linkedin",
    )

    (
        client.table("profiles")
        .update({"photo_path": new_s3_key})
        .eq("user_id", user_id)
        .execute()
    )
    print(f"[OK] user_id={user_id} {photo_url} -> {new_s3_key}")
    return new_s3_key


def main() -> int:
    args = parse_args()

    if args.batch_size <= 0:
        print("Error: --batch-size must be > 0", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit <= 0:
        print("Error: --limit must be > 0 when provided", file=sys.stderr)
        return 2

    settings = get_settings()
    if not settings.s3_bucket_name and not args.dry_run:
        print(
            "Error: s3_bucket_name is not configured. Set S3_BUCKET_NAME in backend/.env",
            file=sys.stderr,
        )
        return 2

    client = get_admin_client()
    s3_service = S3Service()
    stats = MigrationStats()

    print(
        "Starting profile photo migration"
        f" (dry_run={args.dry_run}, batch_size={args.batch_size}, limit={args.limit})"
    )

    candidates = collect_candidates(
        client,
        batch_size=args.batch_size,
        include_http=args.include_http,
    )
    if args.limit is not None:
        candidates = candidates[: args.limit]

    for row in candidates:
        user_id = str(row.get("user_id") or "").strip()
        photo_path = str(row.get("photo_path") or "").strip()
        stats.scanned += 1

        if not user_id or not photo_path:
            stats.skipped += 1
            print(f"[SKIP] invalid row: user_id={user_id!r} photo_path={photo_path!r}")
            continue

        if not (
            photo_path.startswith("https://")
            or (args.include_http and photo_path.startswith("http://"))
        ):
            stats.skipped += 1
            print(f"[SKIP] user_id={user_id} photo_path is not target URL: {photo_path}")
            continue

        try:
            migrate_row(
                client=client,
                s3_service=s3_service,
                bucket_name=str(settings.s3_bucket_name),
                user_id=user_id,
                photo_url=photo_path,
                timeout_seconds=args.timeout_seconds,
                dry_run=args.dry_run,
            )
            stats.migrated += 1
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            stats.failed += 1
            print(f"[FAIL] user_id={user_id} photo_path={photo_path} reason={exc}")
        except Exception as exc:  # noqa: BLE001 - keep processing remaining rows
            stats.failed += 1
            print(f"[FAIL] user_id={user_id} photo_path={photo_path} unexpected={exc}")

    print(
        "Done. "
        f"scanned={stats.scanned} migrated={stats.migrated} "
        f"failed={stats.failed} skipped={stats.skipped}"
    )
    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
