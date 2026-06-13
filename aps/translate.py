"""Submit and monitor APS Model Derivative translation jobs.

Translates uploaded objects to SVF2 format for the APS Viewer.
Supports ZIP input with compressedUrn/rootFilename for OBJ+MTL bundles.
Modeled on hackathonBuckets translate.py.
"""
import logging
import time

import requests
from config import APS_HOST

logger = logging.getLogger(__name__)


def start_translation(token, urn, root_filename=None):
    """Submit a translation job to the Model Derivative API.

    Args:
        token: APS access token.
        urn: Base64-encoded URN of the uploaded object.
        root_filename: If the upload is a ZIP, the root file inside it (e.g. "scene.obj").

    Returns:
        The URN passed in (for chaining).
    """
    inp = {"urn": urn}
    if root_filename:
        inp["compressedUrn"] = True
        inp["rootFilename"] = root_filename

    r = requests.post(
        f"{APS_HOST}/modelderivative/v2/designdata/job",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-ads-force": "true",
        },
        json={
            "input": inp,
            "output": {
                "formats": [{"type": "svf2", "views": ["2d", "3d"]}],
            },
        },
        timeout=30,
    )

    if r.status_code not in (200, 201):
        raise RuntimeError(
            f"Translation submission failed: HTTP {r.status_code} — {r.text[:300]}"
        )

    status = r.json().get("result", "unknown")
    logger.info("Translation submitted (status: %s)", status)
    return urn


def wait_until_done(token, urn, timeout=600, poll_start=5, poll_max=30):
    """Poll the translation manifest until success, failure, or timeout.

    Args:
        token: APS access token.
        urn: Base64-encoded URN.
        timeout: Maximum seconds to wait.
        poll_start: Initial poll interval in seconds.
        poll_max: Maximum poll interval in seconds.

    Returns:
        Final status string ("success").

    Raises:
        RuntimeError: On translation failure.
        TimeoutError: If translation doesn't complete in time.
    """
    url = f"{APS_HOST}/modelderivative/v2/designdata/{urn}/manifest"
    headers = {"Authorization": f"Bearer {token}"}

    start = time.time()
    interval = poll_start

    logger.info("Polling translation status (timeout: %ds)...", timeout)

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            raise TimeoutError(
                f"Translation timed out after {timeout}s. Check APS dashboard."
            )

        r = requests.get(url, headers=headers, timeout=30)

        if r.status_code == 200:
            manifest = r.json()
            status = manifest.get("status", "unknown")
            progress = manifest.get("progress", "unknown")

            logger.info("Status: %s (progress: %s, elapsed: %.0fs)",
                        status, progress, elapsed)

            if status == "success":
                logger.info("Translation complete!")
                return status
            elif status == "failed":
                messages = []
                for d in manifest.get("derivatives", []):
                    for m in d.get("messages", []):
                        messages.append(m.get("message", ""))
                raise RuntimeError(
                    f"Translation failed: {'; '.join(messages) or 'unknown error'}"
                )
            elif status in ("timeout", "cancelled"):
                raise RuntimeError(f"Translation {status}")
        elif r.status_code == 404:
            logger.info("Manifest not ready yet, waiting...")
        else:
            logger.warning("Poll response: HTTP %d", r.status_code)

        time.sleep(interval)
        interval = min(interval * 1.5, poll_max)
