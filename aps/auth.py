"""APS 2-legged OAuth2 authentication.

Uses Basic auth header with client_credentials grant,
matching the proven pattern from hackathonBuckets.
"""
import base64
import logging

import requests
from config import APS_HOST, APS_CLIENT_ID, APS_CLIENT_SECRET, APS_SCOPES

logger = logging.getLogger(__name__)


def basic_auth_header(client_id, client_secret):
    """Build a Basic Authorization header value."""
    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def get_token(scopes=APS_SCOPES):
    """2-legged client-credentials token.

    POST /authentication/v2/token with Basic auth header.

    Returns:
        Access token string.

    Raises:
        RuntimeError: If authentication fails.
    """
    if not APS_CLIENT_ID or not APS_CLIENT_SECRET:
        raise EnvironmentError(
            "APS_CLIENT_ID and APS_CLIENT_SECRET must be set in .env or environment."
        )

    logger.info("Authenticating with APS (client_id: %s...)", APS_CLIENT_ID[:8])

    r = requests.post(
        f"{APS_HOST}/authentication/v2/token",
        headers={
            "Authorization": basic_auth_header(APS_CLIENT_ID, APS_CLIENT_SECRET),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope": scopes,
        },
        timeout=30,
    )

    if r.status_code != 200:
        raise RuntimeError(
            f"APS auth failed: HTTP {r.status_code} — {r.text[:300]}"
        )

    token = r.json()["access_token"]
    expires_in = r.json().get("expires_in", "?")
    logger.info("Authenticated (expires in %ss)", expires_in)
    return token
