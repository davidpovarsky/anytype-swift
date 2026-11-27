"""Finite loopback fixture: native file-contract and lifetime checks, not native quota proof."""
import http.server
import json
import pathlib
import signal
import sys
import time

directory = pathlib.Path(sys.argv[1])
config = json.loads((directory / "config.json").read_text())
requests = []
running = True
account_changed = False

def stop(*_):
    global running
    running = False

signal.signal(signal.SIGTERM, stop)
if hasattr(signal, "pthread_sigmask"):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM})

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, value=None):
        body = b"" if status == 204 else json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def record(self, action):
        global account_changed
        requests.append(self.command + " " + self.path)
        (directory / "dispatch.json").write_text(json.dumps(requests))
        (directory / (action + "-responded")).write_text("response boundary")
        if config.get("switchAfter") == action:
            account_changed = True

    def do_GET(self):
        if self.path == "/v1/auth":
            self.reply(200, {"authorized": True, "accountId": "different" if account_changed else config["authorizedAccount"]})
        elif self.path == "/v1/spaces/space/files/file/status":
            self.record("status")
            self.reply(200, config["statusBody"])
        else:
            self.reply(404, {"error": {"code": "test.route"}})

    def do_POST(self):
        if self.path == "/v1/spaces/space/files/file/retry":
            self.record("retry")
            mode = config.get("rawRetryMode", "")
            if mode:
                body = b"{" if mode == "invalid-json" else b'"' + b"x" * 65536 + b'"'
                self.send_response(config["retryStatus"])
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self.reply(config["retryStatus"], config["retryBody"])
        else:
            self.reply(404, {"error": {"code": "test.route"}})

server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
server.timeout = 0.25
print(server.server_port, flush=True)
deadline = time.monotonic() + 45
while running and time.monotonic() < deadline:
    server.handle_request()
server.server_close()
