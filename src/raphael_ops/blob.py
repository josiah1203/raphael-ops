"""Backup blob storage — MinIO when configured, local filesystem fallback."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any


def _local_backup_dir() -> Path:
    base = Path(os.environ.get("RAPHAEL_BACKUP_DIR", "/tmp/raphael-backups"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def put_backup(key: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, default=str).encode("utf-8")
    endpoint = os.environ.get("RAPHAEL_MINIO_ENDPOINT", "").strip()
    if not endpoint:
        path = _local_backup_dir() / key.replace("/", "__")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"file://{path}"

    from minio import Minio

    client = Minio(
        endpoint,
        access_key=os.environ.get("RAPHAEL_MINIO_ACCESS_KEY", "raphael"),
        secret_key=os.environ.get("RAPHAEL_MINIO_SECRET_KEY", "raphaeldev"),
        secure=os.environ.get("RAPHAEL_MINIO_SECURE", "false").lower() in ("1", "true", "yes"),
    )
    bucket = os.environ.get("RAPHAEL_MINIO_BACKUP_BUCKET", os.environ.get("RAPHAEL_MINIO_BUCKET", "raphael-backups"))
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(bucket, key, io.BytesIO(data), len(data), content_type="application/json")
    return f"s3://{bucket}/{key}"
