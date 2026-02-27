from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from src.utils.logging import get_logger


logger = get_logger(__name__)
DEFAULT_LOCAL_DIR = Path("data/raw")


def _normalize_prefix(prefix: str) -> str:
    clean = prefix.strip().strip("/")
    return f"{clean}/" if clean else ""


def _build_s3_key(prefix: str, local_file: Path, local_dir: Path) -> str:
    rel = local_file.relative_to(local_dir).as_posix()
    return f"{_normalize_prefix(prefix)}{rel}"


def _relative_from_key(prefix: str, key: str) -> Path:
    normalized = _normalize_prefix(prefix)
    if normalized and key.startswith(normalized):
        return Path(key[len(normalized) :])
    return Path(key)


def _resolve_bucket(bucket_arg: str | None) -> str:
    bucket = bucket_arg or os.getenv("S3_BUCKET", "")
    if not bucket:
        raise SystemExit("S3 bucket missing. Set S3_BUCKET in .env or pass --bucket.")
    return bucket


def upload_raw_data(bucket: str, prefix: str, local_dir: Path, region: str | None = None) -> None:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise SystemExit("Missing optional dependency for S3 sync. Run: pip install boto3") from exc

    if not local_dir.exists():
        raise SystemExit(f"Local directory not found: {local_dir}")

    session = boto3.session.Session(region_name=region or os.getenv("AWS_REGION"))
    s3 = session.client("s3")

    files = [p for p in local_dir.rglob("*") if p.is_file() and p.suffix.lower() in {".csv", ".parquet"}]
    if not files:
        raise SystemExit(f"No CSV/Parquet files found in {local_dir}")

    for file_path in files:
        key = _build_s3_key(prefix=prefix, local_file=file_path, local_dir=local_dir)
        logger.info("Uploading %s -> s3://%s/%s", file_path, bucket, key)
        try:
            s3.upload_file(str(file_path), bucket, key)
        except (BotoCoreError, ClientError) as exc:
            raise SystemExit(f"S3 upload failed for {file_path}: {exc}") from exc

    logger.info("S3 upload complete (%s files)", len(files))


def download_raw_data(bucket: str, prefix: str, local_dir: Path, region: str | None = None) -> None:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise SystemExit("Missing optional dependency for S3 sync. Run: pip install boto3") from exc

    local_dir.mkdir(parents=True, exist_ok=True)

    session = boto3.session.Session(region_name=region or os.getenv("AWS_REGION"))
    s3 = session.client("s3")

    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix=_normalize_prefix(prefix))

        downloaded = 0
        for page in pages:
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                rel_path = _relative_from_key(prefix=prefix, key=key)
                if rel_path.suffix.lower() not in {".csv", ".parquet"}:
                    continue

                target = local_dir / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                logger.info("Downloading s3://%s/%s -> %s", bucket, key, target)
                s3.download_file(bucket, key, str(target))
                downloaded += 1

        if downloaded == 0:
            logger.warning("No CSV/Parquet files found under s3://%s/%s", bucket, _normalize_prefix(prefix))
        else:
            logger.info("S3 download complete (%s files)", downloaded)
    except (BotoCoreError, ClientError) as exc:
        raise SystemExit(f"S3 download failed: {exc}") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync MindLift raw data with S3")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for cmd in ["upload", "download"]:
        sub = subparsers.add_parser(cmd)
        sub.add_argument("--bucket", default=None)
        sub.add_argument("--prefix", default=os.getenv("S3_PREFIX", "mindlift/raw"))
        sub.add_argument("--local-dir", type=Path, default=DEFAULT_LOCAL_DIR)
        sub.add_argument("--region", default=None)

    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    bucket = _resolve_bucket(args.bucket)

    if args.command == "upload":
        upload_raw_data(bucket=bucket, prefix=args.prefix, local_dir=args.local_dir, region=args.region)
    elif args.command == "download":
        download_raw_data(bucket=bucket, prefix=args.prefix, local_dir=args.local_dir, region=args.region)
    else:
        raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
