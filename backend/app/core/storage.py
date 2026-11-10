"""File storage on S3 (SeaweedFS in dev): receipts and export files.

Objects are private. The browser only gets short-lived signed links, made after the
API has checked that the file belongs to the user (docs/DECISIONS.md).
"""

from collections.abc import Callable
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

SIGNED_URL_SECONDS = 300


def _client(endpoint: str) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


class Storage:
    def __init__(self, endpoint: str, public_endpoint: str, bucket: str) -> None:
        self._s3 = _client(endpoint)
        self._public = _client(public_endpoint)
        self.bucket = bucket
        self._bucket_ready = False

    async def _call[T](self, fn: Callable[[], T]) -> T:
        return await run_in_threadpool(fn)

    def _ensure_bucket(self) -> None:
        if self._bucket_ready:
            return
        try:
            self._s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._s3.create_bucket(Bucket=self.bucket)
        self._bucket_ready = True

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        def put() -> None:
            self._ensure_bucket()
            self._s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

        await self._call(put)

    async def get(self, key: str) -> bytes:
        def get() -> bytes:
            body: bytes = self._s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
            return body

        return await self._call(get)

    async def delete_prefix(self, prefix: str) -> int:
        """Delete every object under a prefix (a user's files); returns how many."""

        def delete() -> int:
            self._ensure_bucket()
            deleted = 0
            pages = self._s3.get_paginator("list_objects_v2").paginate(
                Bucket=self.bucket, Prefix=prefix
            )
            for page in pages:
                keys = [{"Key": item["Key"]} for item in page.get("Contents", [])]
                if keys:
                    self._s3.delete_objects(Bucket=self.bucket, Delete={"Objects": keys})
                    deleted += len(keys)
            return deleted

        return await self._call(delete)

    def signed_url(self, key: str, filename: str, *, download: bool) -> str:
        """A link that works for SIGNED_URL_SECONDS, shown inline or as a download."""
        disposition = "attachment" if download else "inline"
        url: str = self._public.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentDisposition": f"{disposition}; filename*=UTF-8''{quote(filename)}",
            },
            ExpiresIn=SIGNED_URL_SECONDS,
        )
        return url


@lru_cache
def get_storage() -> Storage:
    return Storage(
        settings.S3_ENDPOINT_URL,
        settings.S3_PUBLIC_URL or settings.S3_ENDPOINT_URL,
        settings.S3_BUCKET,
    )
