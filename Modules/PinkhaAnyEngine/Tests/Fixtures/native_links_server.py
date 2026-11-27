#!/usr/bin/env python3
"""Loopback consumer-contract fixture. It does not emulate or accept native ACL."""
import json
import pathlib
import sys
import signal
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

root = pathlib.Path(sys.argv[1])
config = json.loads((root / "config.json").read_text())
sent = False
journal = []
running = True

def stop(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, stop)
if hasattr(signal, "pthread_sigmask"):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM})

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        global sent
        if urlparse(self.path).path == "/v1/auth":
            account = "different-account" if sent and config.get("switchAccount") else "account"
            body = {"authorized": True, "accountId": account}
            status = 200
        else:
            journal.append(self.path)
            (root / "dispatch.json").write_text(json.dumps(journal))
            (root / "response-began").write_text("response")
            sent = True
            body = config["body"]
            status = config.get("status", 200)
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass

server = HTTPServer(("127.0.0.1", 0), Handler)
server.timeout = 0.25
print(server.server_address[1], flush=True)
deadline = time.monotonic() + 45
while running and time.monotonic() < deadline:
    server.handle_request()
server.server_close()
