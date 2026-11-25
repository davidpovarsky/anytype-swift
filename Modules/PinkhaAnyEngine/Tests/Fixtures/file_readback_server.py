"""Adversarial HTTP component fixture; this is not a native engine."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import signal

# Foundation Process can inherit a dispatch worker signal mask on Linux.
# Unblock this fixture signal mask so explicit cleanup terminates it.
signal.pthread_sigmask(signal.SIG_SETMASK, [])

CONTENT = bytes((i * 31 + 17) % 251 for i in range(2 * 1024 * 1024 + 17))

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *_):
        pass

    def reply(self, status, body, mime="application/json", **headers):
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Type", mime)
        for key, value in headers.items():
            self.send_header(key.replace("_", "-"), value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get("X-Any-Control-Token") != "b" * 64:
            self.reply(401, b'{"error":{"code":"auth.invalid"}}')
            return
        if self.path == "/v1/auth":
            self.reply(200, json.dumps({"authorized": True,
                "accountId": "changed" if self.server.changed else "account"}).encode())
            return
        match = re.fullmatch(r"/v1/spaces/space/files/([a-z-]+)/content", self.path)
        if not match:
            self.reply(404, b"{}")
            return
        fault = match.group(1)
        if fault == "large-header":
            self.send_response(206)
            self.send_header("Content-Length", str(1 << 30))
            self.send_header("Content-Type", "application/x-pinkha-test")
            self.end_headers()
            self.close_connection = True
            return
        if fault == "chunked-overflow":
            self.send_response(206)
            self.send_header("Transfer-Encoding", "chunked")
            self.send_header("Content-Type", "application/x-pinkha-test")
            self.end_headers()
            data = b"x" * 65537
            self.wfile.write(("%x\\r\\n" % len(data)).encode().replace(b"\\r\\n", b"\r\n"))
            self.wfile.write(data + b"\r\n0\r\n\r\n")
            self.close_connection = True
            return
        if fault == "redirect":
            self.reply(302, b"", Location="/v1/auth")
            return
        if fault == "empty":
            if self.headers.get("Range"):
                self.reply(416, b"{}")
            else:
                self.reply(200, b"", "application/x-pinkha-test")
            return
        parsed = re.fullmatch(r"bytes=(\d+)-(\d+)", self.headers.get("Range", ""))
        if not parsed:
            self.reply(416, b"{}")
            return
        start, end = map(int, parsed.groups())
        # Test cases with one short range request deliberately describe 8192.
        total = len(CONTENT) if end >= 8192 or start else 8192
        data = CONTENT[start:end + 1]
        if fault == "short": data = data[:-1]
        if fault == "oversize": data += b"x"
        if fault == "account-switch": self.server.changed = True
        native_range = f"bytes {start}-{end}/{total}"
        if fault == "wrong-range": native_range = f"bytes {start + 1}-{end + 1}/{total}"
        self.reply(200 if fault == "ignored-range" else 206, data,
            "text/plain" if fault == "wrong-mime" else "application/x-pinkha-test",
            Content_Range=native_range)

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
server.daemon_threads = True
server.changed = False
print(server.server_port, flush=True)
server.serve_forever()
