"""Tests for aps/ package — auth, upload, translate (mocked)."""
import base64
from unittest.mock import MagicMock, patch

import pytest


class TestApsAuth:
    @patch("aps.auth.requests.post")
    @patch("aps.auth.APS_CLIENT_ID", "test_id")
    @patch("aps.auth.APS_CLIENT_SECRET", "test_secret")
    def test_get_token_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "abc123token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_resp

        from aps.auth import get_token
        token = get_token()

        assert token == "abc123token"
        mock_post.assert_called_once()

        # Verify Basic auth header
        call_args = mock_post.call_args
        auth_header = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert "Basic" in auth_header.get("Authorization", "")

    @patch("aps.auth.requests.post")
    @patch("aps.auth.APS_CLIENT_ID", "test_id")
    @patch("aps.auth.APS_CLIENT_SECRET", "test_secret")
    def test_get_token_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        from aps.auth import get_token
        with pytest.raises(RuntimeError, match="APS auth failed"):
            get_token()


class TestApsUpload:
    @patch("aps.upload.requests")
    def test_ensure_bucket_already_exists(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 409
        mock_requests.post.return_value = mock_resp

        from aps.upload import ensure_bucket
        ensure_bucket("token123", "test-bucket")  # should not raise

    @patch("aps.upload.requests")
    def test_ensure_bucket_created(self, mock_requests):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_requests.post.return_value = mock_resp

        from aps.upload import ensure_bucket
        ensure_bucket("token123", "new-bucket")


class TestApsTranslate:
    @patch("aps.translate.requests.post")
    def test_start_translation(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "created"}
        mock_post.return_value = mock_resp

        from aps.translate import start_translation
        urn = start_translation("token", "test_urn")

        assert urn == "test_urn"
        call_args = mock_post.call_args
        headers = call_args.kwargs.get("headers", call_args[1].get("headers", {}))
        assert headers.get("x-ads-force") == "true"

    @patch("aps.translate.requests.post")
    def test_start_translation_with_root_filename(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"result": "created"}
        mock_post.return_value = mock_resp

        from aps.translate import start_translation
        start_translation("token", "test_urn", root_filename="scene.obj")

        call_json = mock_post.call_args.kwargs.get("json", mock_post.call_args[1].get("json", {}))
        assert call_json["input"]["compressedUrn"] is True
        assert call_json["input"]["rootFilename"] == "scene.obj"

    @patch("aps.translate.requests.post")
    def test_start_translation_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.text = "Bad request"
        mock_post.return_value = mock_resp

        from aps.translate import start_translation
        with pytest.raises(RuntimeError, match="Translation submission failed"):
            start_translation("token", "bad_urn")
