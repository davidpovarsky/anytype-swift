"""Real URLSession SSE boundary checks using local HTTP fixtures, not Any parity."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import subprocess
import threading
import time

parser = argparse.ArgumentParser()
parser.add_argument("--probe", required=True)
args = parser.parse_args()
checks = []

def frame(event, value):
    return ("event: " + event + "\ndata: " +
            json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n\n").encode("utf-8")

for scenario in ("normal", "utf8", "frame", "window", "eof", "redirect", "generation"):
    state = {"sink_hits": 0}
    cancelled = threading.Event()

    class Sink(BaseHTTPRequestHandler):
        def do_POST(self):
            state["sink_hits"] += 1
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass
    sink = ThreadingHTTPServer(("127.0.0.1", 0), Sink)

    class Origin(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/v1/auth":
                self.send_error(404)
                return
            data = b'{"authorized":true,"accountId":"sse-test-account"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if scenario == "redirect":
                self.send_response(307)
                self.send_header("Location", f"http://localhost:{sink.server_port}/forbidden")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(frame("ready", {}))
            if scenario == "utf8":
                self.wfile.write(b"event: snapshot\ndata: \xc3\x28\n\n")
            elif scenario == "frame":
                self.wfile.write(frame("snapshot", {"value": "a" * 2048}))
            else:
                first = {"id": "one", "value": "a" * 600 if scenario == "window" else "before"}
                self.wfile.write(frame("snapshot", {"records": [first], "total": 1, "hasNext": False}))
                self.wfile.flush()
                if scenario == "window":
                    self.wfile.write(frame("changes", [{"versionId": "", "added": [
                        {"id": "two", "doc": {"id": "two", "value": "b" * 600}}]}]))
                elif scenario == "normal":
                    self.wfile.write(frame("changes", [{"versionId": "", "updated": [
                        {"id": "one", "doc": {"id": "one", "value": "תורה"}, "ops": []}]}]))
                elif scenario == "generation":
                    try:
                        for _ in range(200):
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                            time.sleep(0.01)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        cancelled.set()
                        return
            self.wfile.flush()
        def log_message(self, *args):
            pass
    origin = ThreadingHTTPServer(("127.0.0.1", 0), Origin)
    for server in (origin, sink):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        result = subprocess.run([
            args.probe, "--endpoint", f"http://127.0.0.1:{origin.server_port}",
            "--account-id", "sse-test-account", "--space-id", "unused",
            "--mode", "check-sse", "--scenario", scenario
        ], capture_output=True, text=True, timeout=40)
        if result.returncode:
            raise RuntimeError(f"{scenario}: probe exit {result.returncode}: {result.stderr[:1500]}")
        proof = json.loads(result.stdout)
        expected = ("PASS_SSE_FULL_DOCUMENT" if scenario == "normal" else
                    "PASS_SSE_GENERATION_CANCEL" if scenario == "generation" else
                    "PASS_SSE_NEGATIVE_BOUNDARY")
        if proof.get("status") != expected:
            raise RuntimeError(f"{scenario}: unexpected result")
        if scenario == "redirect" and state["sink_hits"] != 0:
            raise RuntimeError("streaming POST followed its redirect")
        if scenario == "generation" and not cancelled.wait(3):
            raise RuntimeError("invalidating generation did not close the HTTP stream")
        checks.append(scenario)
    finally:
        origin.shutdown()
        sink.shutdown()
        origin.server_close()
        sink.server_close()

print(json.dumps({"status": "PASS_REAL_HTTP_SSE_BOUNDARIES", "checks": checks,
                  "scope": "actual URLSession with local fixture; not Any engine parity"}))
