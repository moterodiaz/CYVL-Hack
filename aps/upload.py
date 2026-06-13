"""Upload files to APS Object Storage Service (OSS).

Uses the signed-S3 upload flow (get presigned URL → PUT to S3 → complete),
matching the proven pattern from hackathonBuckets.
"""
import base64
import logging
import os

import requests
from config import APS_HOST

logger = logging.getLogger(__name__)


def ensure_bucket(token, bucket_key):
    """Create an OSS bucket if it doesn't exist.

    Args:
        token: APS access token.
        bucket_key: Bucket key (name).
    """
    r = requests.post(
        f"{APS_HOST}/oss/v2/buckets",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"bucketKey": bucket_key, "policyKey": "persistent"},
        timeout=30,
    )
    if r.status_code in (200, 409):  # 409 = already exists
        logger.info("Bucket '%s' ready", bucket_key)
    else:
        r.raise_for_status()


def upload_object(token, bucket_key, object_key, file_path):
    """Signed-S3 upload: get presigned URL → PUT to S3 → complete.

    Args:
        token: APS access token.
        bucket_key: Target bucket.
        object_key: Object name in the bucket.
        file_path: Local file path to upload.

    Returns:
        Base64-encoded URN of the uploaded object.
    """
    base = f"{APS_HOST}/oss/v2/buckets/{bucket_key}/objects/{object_key}"
    headers = {"Authorization": f"Bearer {token}"}
    file_size = os.path.getsize(file_path)

    logger.info("Uploading %s (%.1f KB) to %s/%s",
                file_path, file_size / 1024, bucket_key, object_key)

    # Step 1: Get signed upload URL
    r = requests.get(
        f"{base}/signeds3upload",
        headers=headers,
        params={"minutesExpiration": 10},
        timeout=30,
    )
    r.raise_for_status()
    signed = r.json()
    upload_url = signed["urls"][0]
    upload_key = signed["uploadKey"]

    # Step 2: PUT file data to S3
    with open(file_path, "rb") as f:
        data = f.read()

    r = requests.put(upload_url, data=data, timeout=120)
    r.raise_for_status()

    # Step 3: Complete the upload
    r = requests.post(
        f"{base}/signeds3upload",
        headers={**headers, "Content-Type": "application/json"},
        json={"uploadKey": upload_key},
        timeout=30,
    )
    r.raise_for_status()

    object_id = f"urn:adsk.objects:os.object:{bucket_key}/{object_key}"
    urn = base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")

    logger.info("Upload complete. URN: %s", urn)
    return urn
