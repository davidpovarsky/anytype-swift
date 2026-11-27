"""Controlled loopback replies for the real Swift Host apply/readback path.

This is not a native engine, account, ACL or storage acceptance fixture.
Lifecycle follows the existing Engine HTTP fixtures: one owned process,
private evidence, loopback port, bounded lifetime and original-owner stdin EOF.
"""
import http.server
import json
import os
import pathlib
import select
import signal
import sys
import time

directory = pathlib.Path(sys.argv[1])
config = json.loads((directory / "config.json").read_bytes())
assert set(config) == {"before", "requested", "reply"}
assert all(isinstance(value, str) and 0 < len(value.encode("utf-8")) <= 4096 for value in config.values())
requests = []
patched = False
running = True
stop_reason = "deadline"


def write(name, value):
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    temporary = directory / (name + ".tmp")
    temporary.write_bytes(data)
    os.chmod(temporary, 0o600)
    os.replace(temporary, directory / name)


def stop(signum, frame):
    global running, stop_reason
    running, stop_reason = False, "signal"


signal.signal(signal.SIGTERM, stop)
if hasattr(signal, "pthread_sigmask"):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM})


def text():
    return config["reply"] if patched else config["before"]


def version():
    return "editor-v2" if patched else "editor-v1"


def block():
    return {"id": "block", "type": "paragraph", "text": text(),
            "nav": {"parentId": "", "pos": "A"},
            "_ver": {"id": "create-block", "text": version()}}


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *args):
        pass

    def reply(self, status, value):
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def record(self, body=None):
        assert len(requests) < 256
        row = {"method": self.command, "path": self.path, "afterPatch": patched}
        if body is not None:
            row["body"] = body
            value = body.get("set", {}).get("text")
            if isinstance(value, str):
                row["textUTF8"] = list(value.encode("utf-8"))
        requests.append(row)
        write("dispatch.json", requests)

    def body(self):
        length = int(self.headers.get("Content-Length", "0"))
        assert 0 < length <= 16384
        data = self.rfile.read(length)
        assert len(data) == length
        value = json.loads(data)
        assert isinstance(value, dict)
        return value

    def do_GET(self):
        self.record()
        if self.path == "/v1/auth":
            self.reply(200, {"authorized": True, "accountId": "account"})
        elif self.path == "/v1/spaces/space/members/me":
            self.reply(200, {"identity": "account", "status": "active", "permission": "owner"})
        elif self.path == "/v1/spaces/space/objects/object":
            self.reply(200, {"objectId": "object", "record": {"id": "object", "spaceId": "space",
                "any": {"name": "Unicode Host fixture", "type": "page", "collections": []}}})
        elif self.path == "/v1/spaces/space/objects/object/editor/editor_blocks/markdown":
            value = {"content": text(), "version": version()}
            write("last-markdown-response.json", value)
            self.reply(200, value)
        else:
            self.reply(404, {"error": {"code": "fixture.route"}})

    def do_POST(self):
        value = self.body()
        self.record(value)
        if (self.path != "/v1/spaces/space/query" or value.get("objectId") != "object"
                or value.get("dataset") != "editor_blocks" or value.get("includeTotal") is not True
                or value.get("limit") != 10001):
            self.reply(400, {"error": {"code": "fixture.query"}})
            return
        response = {"records": [block()], "total": 1, "hasNext": False}
        write("last-query-response.json", response)
        self.reply(200, response)

    def do_PATCH(self):
        global patched
        value = self.body()
        self.record(value)
        requested = value.get("set", {}).get("text")
        if (patched or self.path != "/v1/spaces/space/objects/object/editor/editor_blocks/blocks/block"
                or set(value) != {"set", "unset", "ifVersion", "ifStartedAt"}
                or not isinstance(value.get("set"), dict) or set(value["set"]) != {"text"}
                or value.get("unset") != [] or value.get("ifVersion") != "editor-v1"
                or value.get("ifStartedAt") != "run1" or not isinstance(requested, str)
                or requested.encode("utf-8") != config["requested"].encode("utf-8")):
            self.reply(400, {"error": {"code": "fixture.patch"}})
            return
        patched = True
        response = {"recordIds": ["block"], "versionId": "native-write-v2",
                    "engineStartedAt": "run1", "editorVersion": "editor-v2"}
        write("patch-acknowledgement.json", response)
        self.reply(200, response)


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
server.timeout = 0.25
write("dispatch.json", [])
write("fixture-start.json", {"pid": os.getpid(), "scope": "controlled-loopback-not-native"})
write("port.json", server.server_port)
deadline = time.monotonic() + 45
try:
    while running and time.monotonic() < deadline:
        readable, _, _ = select.select([sys.stdin, server], [], [], 0.25)
        if sys.stdin in readable and os.read(sys.stdin.fileno(), 1) == b"":
            stop_reason = "stdin-eof"
            break
        if server in readable:
            server.handle_request()
finally:
    server.server_close()
    write("fixture-exit.json", {"pid": os.getpid(), "stopReason": stop_reason,
                                "patches": sum(row["method"] == "PATCH" for row in requests)})
