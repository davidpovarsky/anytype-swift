"""Real loopback HTTP transport check, separate from Any engine acceptance."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import threading

parser = argparse.ArgumentParser()
parser.add_argument("--probe", required=True)
args = parser.parse_args()
state = {"redirect_hits": 0, "sink_hits": 0}

class Sink(BaseHTTPRequestHandler):
    def do_GET(self):
        state["sink_hits"] += 1
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")
    def log_message(self, *args):
        pass

sink = ThreadingHTTPServer(("127.0.0.1", 0), Sink)

class Origin(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/auth":
            data = json.dumps({"authorized": True, "accountId": "redirect-test-account"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif self.path == "/v1/probe-redirect":
            state["redirect_hits"] += 1
            self.send_response(307)
            self.send_header("Location", f"http://localhost:{sink.server_port}/must-not-follow")
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_error(404)
    def log_message(self, *args):
        pass

origin = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
for server in (origin, sink):
    threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    result = subprocess.run(
        [args.probe, "--endpoint", f"http://127.0.0.1:{origin.server_port}",
         "--account-id", "redirect-test-account", "--space-id", "unused",
         "--mode", "check-redirect"], capture_output=True, text=True, timeout=40)
    if result.returncode:
        raise RuntimeError(f"probe exit {result.returncode}: {result.stderr[:1000]}")
    proof = json.loads(result.stdout)
    if proof.get("status") != "PASS_REDIRECT_REFUSED" or state != {"redirect_hits": 1, "sink_hits": 0}:
        raise RuntimeError(f"redirect boundary failed: {state}")
    print(json.dumps({"status": "PASS_REAL_HTTP_REDIRECT_BOUNDARY", **state,
                      "scope": "local transport boundary; not Any engine parity"}))
finally:
    origin.shutdown()
    sink.shutdown()
    origin.server_close()
    sink.server_close()
