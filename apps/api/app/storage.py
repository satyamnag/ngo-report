"""Object storage abstraction.

Two backends:
  - "local": filesystem under settings.storage_local_dir (zero-dependency dev).
  - "minio": S3-compatible object store via the official `minio` SDK.

All object keys are server-generated (uuid-based); user filenames are never used
as keys. This prevents path traversal / user-controlled filenames.
"""

import io
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .config import settings


@dataclass
class ObjectData:
    data: bytes
    content_type: str


class Storage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def get(self, key: str) -> ObjectData: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorage(Storage):
    def __init__(self, root: str) -> None:
        self._root = os.path.abspath(root)

    def _path(self, key: str) -> str:
        # Prevent path traversal: resolve and confirm inside root.
        path = os.path.realpath(os.path.join(self._root, key))
        if not path.startswith(self._root + os.sep) and path != self._root:
            raise ValueError("invalid storage key")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)

    def get(self, key: str) -> ObjectData:
        with open(self._path(key), "rb") as fh:
            return ObjectData(data=fh.read(), content_type="application/octet-stream")

    def exists(self, key: str) -> bool:
        return os.path.exists(self._path(key))

    def delete(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass


class MinioStorage(Storage):
    def __init__(self) -> None:
        from minio import Minio

        self._client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_bucket
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get(self, key: str) -> ObjectData:
        response = self._client.get_object(self._bucket, key)
        try:
            return ObjectData(data=response.read(), content_type=response.headers.get("Content-Type", "application/octet-stream"))
        finally:
            response.close()
            response.release_conn()

    def exists(self, key: str) -> bool:
        from minio.error import S3Error

        try:
            self._client.stat_object(self._bucket, key)
            return True
        except S3Error:
            return False

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)


_storage: Storage | None = None


def get_storage() -> Storage:
    """Singleton storage client. Not shared across processes (minio SDK is
    process-safe but not fork-safe) — Celery workers create their own."""
    global _storage
    if _storage is None:
        if settings.storage_backend == "minio":
            _storage = MinioStorage()
        else:
            _storage = LocalStorage(settings.storage_local_dir)
    return _storage


def reset_storage() -> None:
    global _storage
    _storage = None