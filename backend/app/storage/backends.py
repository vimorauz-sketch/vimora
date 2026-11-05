"""Object storage backends. Uploaded content is private; it is never served from a web root."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Protocol

from app.core.config import settings


class StorageBackend(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def open(self, key: str) -> BinaryIO: ...
    def delete(self, key: str) -> None: ...
    def presigned_url(self, key: str, *, filename: str, content_type: str, ttl: int) -> str | None: ...
    def healthy(self) -> bool: ...


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # keys are server generated, but still defend against traversal
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root) + os.sep):
            raise ValueError("Invalid storage key")
        return p

    def put(self, key: str, data: bytes, content_type: str) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".part")
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.chmod(tmp, 0o600)
        tmp.replace(p)

    def open(self, key: str) -> BinaryIO:
        return open(self._path(key), "rb")

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink()
        except FileNotFoundError:
            pass

    def presigned_url(self, key: str, *, filename: str, content_type: str, ttl: int) -> str | None:
        return None  # served through the authenticated download endpoint

    def healthy(self) -> bool:
        return os.access(self.root, os.W_OK)


class S3Storage:
    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or None,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        extra = {} if settings.S3_ENDPOINT else {"ServerSideEncryption": "AES256"}  # AWS SSE; MinIO etc. vary
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, **extra)

    def open(self, key: str) -> BinaryIO:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"]

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def presigned_url(self, key: str, *, filename: str, content_type: str, ttl: int) -> str | None:
        safe = filename.replace('"', "")
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{safe}"',
                "ResponseContentType": "application/octet-stream",
            },
            ExpiresIn=ttl,
        )

    def healthy(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except Exception:
            return False


@lru_cache
def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3Storage()
    return LocalStorage(settings.LOCAL_STORAGE_PATH)
