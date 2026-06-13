"""Minimal token server for local APS Viewer development.

Serves viewer/index.html and provides /api/token endpoint
with a data:read scoped token.

Usage:
    python viewer/token_server.py
    # Then open http://localhost:8000
"""
import http.server
import json
import os
import sys

# Add project root to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PORT = int(os.environ.get("PORT", 8000))


class TokenHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        viewer_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=viewer_dir, **kwargs)

    def do_GET(self):
        if self.path == "/api/token":
            self._serve_token()
        else:
            super().do_GET()

    def _serve_token(self):
        try:
            from aps.auth import get_token
            token = get_token(scopes="data:read")
            body = json.dumps({
                "access_token": token,
                "expires_in": 3600,
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    print(f"Serving viewer at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    with http.server.HTTPServer(("", PORT), TokenHandler) as httpd:
        httpd.serve_forever()
