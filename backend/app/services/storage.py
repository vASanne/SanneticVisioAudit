"""S3-compatible storage for raw HTML."""

from __future__ import annotations

import io
from urllib.parse import urlsplit
from uuid import UUID

from minio import Minio

from app.core.config import Settings


class ObjectStorage:
    """Store crawled HTML in the configured S3-compatible bucket."""

    def __init__(self, settings: Settings) -> None:
        parsed = urlsplit(settings.s3_endpoint)
        self._bucket = settings.s3_bucket
        self._client = Minio(
            parsed.netloc,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=parsed.scheme == "https",
        )

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_html(self, audit_id: UUID, page_id: UUID, body: bytes) -> str:
        key = f"{audit_id}/{page_id}.html"
        self._client.put_object(
            self._bucket,
            key,
            io.BytesIO(body),
            length=len(body),
            content_type="text/html; charset=utf-8",
        )
        return key
