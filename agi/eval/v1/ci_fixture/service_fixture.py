"""Private-network HTTP service used only to exercise provider isolation mechanics."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

EXPECTED = os.environ.get("EXPECTED_TOKEN", "")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"ready": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/check":
            self.send_error(404)
            return
        auth = self.headers.get("Authorization", "")
        if not EXPECTED or auth != f"Bearer {EXPECTED}":
            self.send_error(403)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        body = json.dumps({"authorized": True, "probe": payload.get("probe")}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
