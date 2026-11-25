"""Finite loopback transport fixture; no native-engine acceptance claim."""
import http.server
import json
import time

class Handler(http.server.BaseHTTPRequestHandler):
    account = "account"
    def log_message(self, *args):
        pass
    def reply(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path == "/v1/auth":
            self.reply(200, {"authorized": True, "accountId": Handler.account})
        else:
            self.reply(404, {"error": {"code": "test.route"}})
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= 4096 or self.path != "/v1/spaces/join":
            self.reply(400, {"error": {"code": "test.input"}})
            return
        value = json.loads(self.rfile.read(size))
        token = value.get("inviteToken")
        if token == "switch":
            Handler.account = "different-account"
        if token == "partial":
            self.reply(202, {"rejections": [{"code": "acl.forbidden"}]})
        else:
            self.reply(201 if token == "active" else 202, {"id": "space", "status": "active"})

server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
server.timeout = 0.25
print(server.server_port, flush=True)
deadline = time.monotonic() + 45
while time.monotonic() < deadline:
    server.handle_request()
server.server_close()
