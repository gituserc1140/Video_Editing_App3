from __future__ import annotations

import uuid
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from config import settings


def _get_s3_client():
    return boto3.client("s3", region_name=settings.AWS_S3_REGION or None)


def _build_object_key(filename: str) -> str:
    extension = ""
    if filename and "." in filename:
        extension = "." + filename.rsplit(".", 1)[-1].lower()
    prefix = settings.S3_UPLOAD_PREFIX.strip("/")
    unique_name = f"{uuid.uuid4().hex}{extension}"
    return f"{prefix}/{unique_name}" if prefix else unique_name


def upload_video(file_bytes: bytes, filename: str, content_type: Optional[str] = None) -> str:
    """Upload video bytes to the configured private S3 bucket.

    Returns a time-limited presigned URL (valid for
    ``settings.S3_PRESIGNED_URL_EXPIRY_SECONDS`` seconds) that Creatomate can use
    to fetch the object. The bucket itself is expected to remain private; the
    presigned URL is the only way to access the object, and it stops working
    once it expires.
    """
    if not settings.AWS_S3_BUCKET:
        raise ValueError(
            "AWS_S3_BUCKET is not configured; set it as an environment variable or Streamlit secret"
        )
    if not file_bytes:
        raise ValueError("No video file bytes provided")

    key = _build_object_key(filename)
    client = _get_s3_client()

    extra_args = {"ContentType": content_type} if content_type else {}

    try:
        client.put_object(Bucket=settings.AWS_S3_BUCKET, Key=key, Body=file_bytes, **extra_args)
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
            ExpiresIn=settings.S3_PRESIGNED_URL_EXPIRY_SECONDS,
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"Failed to upload video to S3: {exc}") from exc

    return url
