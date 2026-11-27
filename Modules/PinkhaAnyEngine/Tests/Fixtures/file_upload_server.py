#!/usr/bin/env python3
"""Owned loopback fixture for the ordinary upload component boundary.

It records every original POST before reading its bounded body. It is not a
native SDK substitute: native storage, cryptography and durability need their
separate actual-engine proof.
"""
import hashlib
import http.server
import json
import os
from pathlib import Path
import signal
import socket
import stat
import sys
import threading
import time
import urllib.parse


ROOT = Path(sys.argv[1])
CONFIG = json.loads((ROOT / "config.json").read_text())
LOCK = threading.Lock()
ROWS = []
POST_COUNT = 0
STOP_EVENT = threading.Event()
STOP_REASON = "not-stopped"


def save(name, value):
    path = ROOT / name
    temporary = ROOT / (name + ".tmp")
    data = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    if len(data) > 262_144:
        raise RuntimeError("fixture ledger bound")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def reply(self, status, body, chunked=False, advertised=None):
        raw = body if isinstance(body, bytes) else json.dumps(body, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Connection", "close")
        if chunked:
            self.send_header("Transfer-Encoding", "chunked")
        else:
            self.send_header("Content-Length", str(len(raw) if advertised is None else advertised))
        self.end_headers()
        self.close_connection = True
        try:
            if chunked:
                for offset in range(0, len(raw), 4_096):
                    part = raw[offset:offset + 4_096]
                    self.wfile.write(f"{len(part):x}\r\n".encode() + part + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
            else:
                self.wfile.write(raw)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def authenticated(self):
        expected = CONFIG.get("controlToken", "")
        if expected and self.headers.get("X-Any-Control-Token", "") != expected:
            self.reply(403, {"error": {"code": "control.forbidden"}})
            return False
        return True

    def do_GET(self):
        if not self.authenticated():
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/v1/auth":
            with LOCK:
                changed = CONFIG.get("switchAfterPost", False) and POST_COUNT > 0
            self.reply(200, {"authorized": True, "accountId": "different-account" if changed else CONFIG.get("account", "account")})
            return
        with LOCK:
            ROWS.append({"method": "GET", "path": parsed.path})
            save("dispatch.json", ROWS)
        if parsed.path == "/v1/spaces/space/files/file":
            save("info-responded.json", True)
            self.reply(CONFIG.get("infoStatus", 200), CONFIG.get("infoBody", CONFIG["body"]))
        else:
            self.reply(404, {"error": {"code": "fixture.unknown"}})

    def do_POST(self):
        global POST_COUNT
        if not self.authenticated():
            return
        parsed = urllib.parse.urlsplit(self.path)
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        with LOCK:
            POST_COUNT += 1
            index = len(ROWS)
            ROWS.append({"method": "POST", "path": parsed.path, "name": query.get("name", []),
                         "contentType": self.headers.get("Content-Type", ""),
                         "declaredBytes": length, "stage": "dispatched"})
            save("dispatch.json", ROWS)
        if not 0 <= length <= 512 * 1024 * 1024:
            self.reply(400, {"error": {"code": "fixture.length"}})
            return
        remaining = length
        digest = hashlib.sha256()
        while remaining:
            part = self.rfile.read(min(65_536, remaining))
            if not part:
                return
            digest.update(part)
            remaining -= len(part)
        with LOCK:
            ROWS[index].update(stage="body-read", byteCount=length, sha256=digest.hexdigest())
            save("dispatch.json", ROWS)
        save("body-accepted.json", True)
        mode = CONFIG.get("mode", "normal")
        if mode == "drop-ack":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if parsed.path == "/redirect-target":
            self.reply(500, {"error": {"code": "fixture.redirect-followed"}})
            return
        if parsed.path != "/v1/spaces/space/objects/object/files":
            self.reply(404, {"error": {"code": "fixture.unknown"}})
            return
        if mode == "redirect":
            self.send_response(307)
            self.send_header("Location", "/redirect-target")
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            return
        if mode == "hold-ack":
            for _ in range(1_000):
                if STOP_EVENT.is_set():
                    self.close_connection = True
                    return
                if (ROOT / "release-ack.json").exists():
                    break
                time.sleep(0.01)
            else:
                self.close_connection = True
                return
        body = CONFIG["body"]
        raw = json.dumps(body, separators=(",", ":")).encode()
        if mode == "invalid-json":
            raw = b"{incomplete"
        if mode in ("exact-cap", "chunked-over-cap", "advertised-over-cap"):
            size = 65_536 if mode == "exact-cap" else 65_537
            raw += b" " * (size - len(raw))
        save("post-responded.json", True)
        if mode == "advertised-over-cap":
            self.reply(CONFIG.get("status", 201), raw, advertised=65_537)
        else:
            self.reply(CONFIG.get("status", 201), raw, chunked=mode in ("exact-cap", "chunked-over-cap"))


if hasattr(signal, "pthread_sigmask"):
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})


def stop(signum, frame):
    global STOP_REASON
    STOP_REASON = "signal-" + str(signum)
    STOP_EVENT.set()
    raise SystemExit(0)


def owned_group():
    path = os.environ.get("PINKHA_FILE_UPLOAD_OWNER_RECORD")
    if not path:
        return {"controllerOwnedGroup": False}
    record = Path(path)
    if not record.is_absolute() or record.resolve() != record:
        raise RuntimeError("fixture owner record is not physical")
    fd = os.open(record, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(fd, "rb") as stream:
        attributes = os.fstat(stream.fileno())
        raw = stream.read(65_537)
    if not stat.S_ISREG(attributes.st_mode) or attributes.st_uid != os.geteuid() or stat.S_IMODE(attributes.st_mode) != 0o600 or len(raw) > 65_536:
        raise RuntimeError("fixture owner record custody")
    owner = json.loads(raw)
    pid = owner.get("pid")
    if type(pid) is not int or pid <= 1 or owner.get("cwd") != os.environ.get("PINKHA_FILE_UPLOAD_OWNER_CWD"):
        raise RuntimeError("fixture owner record identity")
    if os.getsid(pid) != pid or os.getpgid(pid) != pid or os.getsid(0) != pid:
        raise RuntimeError("fixture is outside the qualified owner session")
    # A same-session numeric ID alone is not ownership. Bind it to our actual
    # current ancestor chain while the original leader remains unreaped.
    ancestor = os.getppid()
    lineage = []
    for _ in range(64):
        raw_stat = Path(f"/proc/{ancestor}/stat").read_bytes()
        if len(raw_stat) > 8_192:
            raise RuntimeError("fixture owner ancestor bound")
        fields = raw_stat.rsplit(b")", 1)[1].split()
        if len(fields) < 20 or int(fields[3]) != pid:
            raise RuntimeError("fixture owner ancestor session")
        lineage.append({"pid": ancestor, "startTimeTicks": int(fields[19])})
        if ancestor == pid:
            break
        ancestor = int(fields[1])
        if ancestor <= 1:
            raise RuntimeError("fixture qualified leader is not an ancestor")
    else:
        raise RuntimeError("fixture owner ancestry exceeded bound")
    os.setpgid(0, pid)
    if os.getpgrp() != pid or os.getsid(0) != pid:
        raise RuntimeError("fixture did not join its original owned group")
    return {"controllerOwnedGroup": True, "ownerRecord": str(record),
            "ownerRecordSHA256": hashlib.sha256(raw).hexdigest(), "ownerPID": pid, "ownerAncestors": lineage}


signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
OWNER = owned_group()
with Server(("127.0.0.1", 0), Handler) as server:
    started = {"pid": os.getpid(), "pgid": os.getpgrp(), "sessionID": os.getsid(0),
               "parentPID": os.getppid(), "stopOwnership": "stdin-pipe-eof", **OWNER}
    if Path("/proc/self/stat").is_file():
        started["startTimeTicks"] = int(Path("/proc/self/stat").read_text().rsplit(")", 1)[1].split()[19])
        started["bootID"] = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    save("fixture-start.json", started)

    def stdin_owner():
        global STOP_REASON
        try:
            while os.read(0, 1_024):
                STOP_REASON = "unexpected-stdin-data"
            if STOP_REASON == "not-stopped":
                STOP_REASON = "stdin-eof"
        except OSError:
            STOP_REASON = "stdin-read-error"
        finally:
            STOP_EVENT.set()
            server.shutdown()

    threading.Thread(target=stdin_owner, name="owned-stdin-lifetime", daemon=True).start()
    save("port.json", server.server_port)
    try:
        server.serve_forever(poll_interval=0.05)
    finally:
        STOP_EVENT.set()
        server.server_close()
        save("fixture-exit.json", {**started, "stopReason": STOP_REASON, "postCount": POST_COUNT})
