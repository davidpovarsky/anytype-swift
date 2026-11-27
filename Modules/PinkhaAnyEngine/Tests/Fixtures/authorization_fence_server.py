"""Finite loopback HTTP fixture for consumer authorization fences, not native ACL proof."""
import http.server
import json
import pathlib
import signal
import sys
import time

directory = pathlib.Path(sys.argv[1])
marker = directory / "response-began"
journal = directory / "dispatch.json"
requests = []
running = True

def stop(signum, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, stop)
if hasattr(signal, "pthread_sigmask"):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM})

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def record(self):
        requests.append(self.command + " " + self.path)
        journal.write_text(json.dumps(requests))
        marker.write_text("consumer scope revoked after dispatch")

    def do_GET(self):
        if self.path == "/v1/auth":
            self.reply(200, {"authorized": True, "accountId": "account"})
        elif self.path == "/v1/spaces/space/objects/object":
            self.record()
            self.reply(200, {"objectId": "object", "text": "private fixture content"})
        else:
            self.reply(404, {"error": {"code": "test.route"}})

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 4096:
            self.reply(400, {"error": {"code": "test.input"}})
            return
        json.loads(self.rfile.read(size))
        if self.path == "/v1/spaces/join":
            self.record()
            self.reply(202, {"id": "space", "status": "joining"})
        elif self.path == "/v1/spaces/original-space/pinkha/objects":
            self.record()
            self.reply(201, {"objectId": "created-object"})
        else:
            self.reply(404, {"error": {"code": "test.route"}})

server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
server.timeout = 0.25
print(server.server_port, flush=True)
deadline = time.monotonic() + 45
while running and time.monotonic() < deadline:
    server.handle_request()
server.server_close()
