"""AWS S3 storage service for audio files and LLM transcripts."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError


def _get_s3_config() -> dict[str, str]:
    """Read S3 configuration from environment variables."""
    return {
        "bucket": os.environ.get("S3_BUCKET", ""),
        "region": os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1")),
        "access_key": os.environ.get("AWS_ACCESS_KEY_ID", ""),
        "secret_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
        "prefix": os.environ.get("S3_PREFIX", "transcribe-studio"),
    }


def _get_client():
    """Create an S3 client. Uses IAM role on EC2, or env vars locally."""
    config = _get_s3_config()
    kwargs: dict[str, Any] = {"region_name": config["region"]}
    # If explicit keys are set, use them. Otherwise boto3 uses IAM role / credential chain.
    if config["access_key"] and config["secret_key"]:
        kwargs["aws_access_key_id"] = config["access_key"]
        kwargs["aws_secret_access_key"] = config["secret_key"]
    return boto3.client("s3", **kwargs)


def is_s3_configured() -> bool:
    """Check if S3 bucket is configured via environment."""
    return bool(os.environ.get("S3_BUCKET", "").strip())


def _s3_key(category: str, filename: str) -> str:
    """Build the S3 object key: prefix/category/filename."""
    prefix = os.environ.get("S3_PREFIX", "transcribe-studio").strip("/")
    return f"{prefix}/{category}/{filename}"


def upload_file(local_path: Path, category: str, filename: str) -> dict[str, Any]:
    """
    Upload a local file to S3.

    Args:
        local_path: Path to the local file
        category: 'audio' or 'llm_transcripts'
        filename: The stored filename (UUID-based)

    Returns:
        dict with ok, key, bucket
    """
    if not is_s3_configured():
        return {"ok": False, "message": "S3 not configured"}

    config = _get_s3_config()
    key = _s3_key(category, filename)

    try:
        client = _get_client()
        client.upload_file(str(local_path), config["bucket"], key)
        return {"ok": True, "key": key, "bucket": config["bucket"]}
    except (BotoCoreError, ClientError) as exc:
        return {"ok": False, "message": f"S3 upload failed: {exc}"}


def download_file(category: str, filename: str, local_path: Path) -> dict[str, Any]:
    """
    Download a file from S3 to local path.

    Args:
        category: 'audio' or 'llm_transcripts'
        filename: The stored filename
        local_path: Where to save locally

    Returns:
        dict with ok status
    """
    if not is_s3_configured():
        return {"ok": False, "message": "S3 not configured"}

    config = _get_s3_config()
    key = _s3_key(category, filename)

    try:
        client = _get_client()
        local_path.parent.mkdir(parents=True, exist_ok=True)
        client.download_file(config["bucket"], key, str(local_path))
        return {"ok": True, "key": key}
    except (BotoCoreError, ClientError) as exc:
        return {"ok": False, "message": f"S3 download failed: {exc}"}


def delete_file(category: str, filename: str) -> dict[str, Any]:
    """Delete a file from S3."""
    if not is_s3_configured():
        return {"ok": False, "message": "S3 not configured"}

    config = _get_s3_config()
    key = _s3_key(category, filename)

    try:
        client = _get_client()
        client.delete_object(Bucket=config["bucket"], Key=key)
        return {"ok": True, "key": key}
    except (BotoCoreError, ClientError) as exc:
        return {"ok": False, "message": f"S3 delete failed: {exc}"}


def generate_presigned_url(category: str, filename: str, expires_in: int = 3600) -> dict[str, Any]:
    """
    Generate a presigned URL for direct browser access (streaming audio).

    Args:
        category: 'audio' or 'llm_transcripts'
        filename: The stored filename
        expires_in: URL expiration in seconds (default 1 hour)

    Returns:
        dict with ok, url
    """
    if not is_s3_configured():
        return {"ok": False, "message": "S3 not configured"}

    config = _get_s3_config()
    key = _s3_key(category, filename)

    try:
        client = _get_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": config["bucket"], "Key": key},
            ExpiresIn=expires_in,
        )
        return {"ok": True, "url": url}
    except (BotoCoreError, ClientError) as exc:
        return {"ok": False, "message": f"Presigned URL failed: {exc}"}


def check_connection() -> dict[str, Any]:
    """Test S3 connectivity by listing the bucket (head_bucket)."""
    if not is_s3_configured():
        return {"ok": False, "message": "S3_BUCKET environment variable not set"}

    config = _get_s3_config()
    try:
        client = _get_client()
        client.head_bucket(Bucket=config["bucket"])
        return {
            "ok": True,
            "bucket": config["bucket"],
            "region": config["region"],
            "message": f"Connected to s3://{config['bucket']}",
        }
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        if code == "403":
            return {"ok": False, "message": f"Access denied to bucket '{config['bucket']}'"}
        elif code == "404":
            return {"ok": False, "message": f"Bucket '{config['bucket']}' does not exist"}
        return {"ok": False, "message": f"S3 error ({code}): {exc}"}
    except BotoCoreError as exc:
        return {"ok": False, "message": f"S3 connection failed: {exc}"}
