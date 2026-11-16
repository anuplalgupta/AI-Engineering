"""One storage interface over any S3-compatible object store (ADR 0002)."""

import io
import re
import uuid
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error

from ailms.platform.settings import get_settings


@dataclass(frozen=True)
class StoredObject:
    data: bytes
    content_type: str


class Storage(Protocol):
    def ensure_bucket(self) -> None: ...
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> StoredObject | None: ...
    def exists(self, key: str) -> bool: ...


class S3Storage:
    def __init__(
        self, endpoint: str, access_key: str, secret_key: str, bucket: str, region: str
    ) -> None:
        url = urlparse(endpoint)
        self._client = Minio(
            endpoint=url.netloc,
            access_key=access_key,
            secret_key=secret_key,
            secure=url.scheme == "https",
            region=region,
        )
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(bucket_name=self._bucket):
            self._client.make_bucket(bucket_name=self._bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def get(self, key: str) -> StoredObject | None:
        try:
            response = self._client.get_object(bucket_name=self._bucket, object_name=key)
        except S3Error as error:
            if error.code in ("NoSuchKey", "NoSuchObject"):
                return None
            raise
        try:
            content_type = response.headers.get("Content-Type", "application/octet-stream")
            return StoredObject(data=response.read(), content_type=content_type)
        finally:
            response.close()
            response.release_conn()

    def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(bucket_name=self._bucket, object_name=key)
        except S3Error as error:
            if error.code in ("NoSuchKey", "NoSuchObject"):
                return False
            raise
        return True


class InMemoryStorage:
    """For tests."""

    def __init__(self) -> None:
        self.objects: dict[str, StoredObject] = {}

    def ensure_bucket(self) -> None:
        pass

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = StoredObject(data=data, content_type=content_type)

    def get(self, key: str) -> StoredObject | None:
        return self.objects.get(key)

    def exists(self, key: str) -> bool:
        return key in self.objects


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        s = get_settings()
        _storage = S3Storage(s.s3_endpoint, s.s3_access_key, s.s3_secret_key, s.s3_bucket, s.s3_region)
    return _storage


def set_storage(storage: Storage | None) -> None:
    global _storage
    _storage = storage


_KEY_PART = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def is_valid_media_key(key: str) -> bool:
    """A media key is a relative path of plain name parts, at most 300 characters."""
    if not key or len(key) > 300:
        return False
    return all(_KEY_PART.match(part) for part in key.split("/"))


def organisation_key(organisation_id: uuid.UUID, key: str) -> str:
    """Where an organisation's file lives in the store. Files never cross organisations."""
    if not is_valid_media_key(key):
        raise ValueError(f"not a valid media key: {key!r}")
    return f"org/{organisation_id}/{key}"
