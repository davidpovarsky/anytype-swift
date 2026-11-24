#!/usr/bin/env python3
"""Owned loopback HTTPS fixture. Requires only Python's stdlib and OpenSSL CLI.

All public output is explicitly allowlisted metadata. Private configuration,
TLS material and bodies must never be placed in an artifact upload directory.
This process has no Any credentials and never makes a request to the Any API.
"""
from __future__ import annotations

import argparse
import contextlib
import ctypes
import hashlib
import hmac
import http.client
import http.server
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import ssl
import stat
import subprocess
import sys
import threading
import time
import urllib.parse
import uuid

from protocol import CONTRACT, MODEL, MAX_BODY, FixtureError, Protocol, canonical, digest, require, strict_json

CONFIG_NAME = "private-config.json"
MAX_CONNECTIONS = 8
MAX_REQUESTS = 256
AUTHENTICATION_OBSERVATION_SCHEMA = "hanlin-authentication-rejection/v1"
PREFIX = "TEST_RUNNER_PINKHA_HANLIN_FIXTURE_"


def safe_output(value: dict) -> None:
    sys.stdout.write(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def atomic_json(path: Path, value: dict, *, private: bool = False) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not path.is_symlink(), "output_symlink")
    temporary = path.with_name(path.name + ".tmp-" + secrets.token_hex(6))
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(canonical(value) + b"\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        if private:
            os.chmod(path, 0o600)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()


def private_directory(value: str) -> Path:
    path = Path(value).absolute()
    require(not path.is_symlink(), "private_directory_symlink")
    if path.exists():
        require(path.is_dir() and not any(path.iterdir()), "private_directory_not_empty")
    else:
        path.mkdir(mode=0o700, parents=False)
    if os.name != "nt":
        info = path.stat()
        require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
                "private_directory_permissions")
    return path


def generate_identity(directory: Path, openssl: str) -> tuple[Path, str]:
    """No trust installation; root is consumed only by explicit client contexts."""
    config = directory / "certificate.cnf"
    config.write_text("""[req]
distinguished_name=dn
prompt=no
[dn]
CN=Pinkha owned loopback fixture server
[ca_ext]
basicConstraints=critical,CA:TRUE,pathlen:0
keyUsage=critical,keyCertSign,cRLSign
subjectKeyIdentifier=hash
[server_ext]
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=IP:127.0.0.1
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid:always
""", encoding="ascii")
    os.chmod(config, 0o600)
    commands = [
        [openssl, "req", "-new", "-x509", "-newkey", "rsa:2048", "-nodes", "-sha256",
         "-days", "1", "-config", str(config), "-extensions", "ca_ext",
         "-subj", "/CN=Pinkha owned loopback fixture CA",
         "-keyout", str(directory / "root-ca-key.pem"), "-out", str(directory / "root-ca.pem")],
        [openssl, "req", "-new", "-newkey", "rsa:2048", "-nodes", "-sha256",
         "-config", str(config), "-keyout", str(directory / "server-key.pem"),
         "-out", str(directory / "server.csr")],
        [openssl, "x509", "-req", "-in", str(directory / "server.csr"),
         "-CA", str(directory / "root-ca.pem"), "-CAkey", str(directory / "root-ca-key.pem"),
         "-CAcreateserial", "-days", "1", "-sha256", "-extfile", str(config),
         "-extensions", "server_ext", "-out", str(directory / "server-cert.pem")],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise FixtureError("certificate_command_failed") from None
        require(result.returncode == 0, "certificate_command_failed")
    for path in directory.iterdir():
        require(path.is_file() and not path.is_symlink(), "certificate_path")
        os.chmod(path, 0o600)
    root = directory / "root-ca.pem"
    der = ssl.PEM_cert_to_DER_cert(root.read_text(encoding="ascii"))
    return root, digest(der)


def load_config(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), "private_config_missing")
    require(path.stat().st_size <= 16384, "private_config_size")
    if os.name != "nt":
        require(path.stat().st_uid == os.getuid()
                and stat.S_IMODE(path.stat().st_mode) == 0o600, "private_config_permissions")
    value = strict_json(path.read_bytes(), 16384)
    require(isinstance(value, dict) and value.get("schemaVersion") == 1
            and value.get("contract") == CONTRACT, "private_config_contract")
    try:
        require(str(uuid.UUID(value["runID"])) == value["runID"], "private_config_run")
    except (KeyError, ValueError, TypeError, AttributeError):
        raise FixtureError("private_config_run") from None
    directory = path.parent.resolve()
    require(Path(value["privateDirectory"]).resolve() == directory, "private_config_directory")
    for key, basename in (("rootCAPath", "root-ca.pem"), ("serverCertificatePath", "server-cert.pem"),
                          ("serverKeyPath", "server-key.pem")):
        candidate = Path(value[key])
        require(candidate.parent.resolve() == directory and candidate.name == basename
                and candidate.is_file() and not candidate.is_symlink(), "private_config_tls_path")
    root_der = ssl.PEM_cert_to_DER_cert(Path(value["rootCAPath"]).read_text(encoding="ascii"))
    require(digest(root_der) == value["rootCAFingerprintSHA256"], "private_config_ca_changed")
    for key in ("modelKey", "controlToken"):
        require(isinstance(value.get(key), str) and 32 <= len(value[key]) <= 128
                and value[key].isascii(), "private_config_token")
    return value


def child_receipt(config_path: Path, config: dict, pid: int) -> dict:
    identity = process_identity(pid)
    require(identity is not None and identity["running"], "child_identity_unavailable")
    return {"schemaVersion": 1, "runID": config["runID"], "pid": pid,
            "configPath": str(config_path.resolve()), "entrypointPath": str(Path(__file__).resolve()),
            "entrypointSHA256": digest(Path(__file__).read_bytes()), "processBirth": identity["birth"]}


def process_identity(pid: int) -> dict | None:
    """Read-only status of a specific PID. Never os.kill on Windows."""
    require(type(pid) is int and pid > 0, "process_id")
    if os.name == "nt":
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        handle = kernel.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE | QUERY_LIMITED_INFORMATION
        if not handle:
            require(ctypes.get_last_error() == 87, "process_status_unavailable")  # invalid PID, not access denied
            return None
        try:
            created, exited, system, user = (wintypes.FILETIME() for _ in range(4))
            require(bool(kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                               ctypes.byref(system), ctypes.byref(user))), "process_birth_unavailable")
            wait = kernel.WaitForSingleObject(handle, 0)
            require(wait in (0, 258), "process_status_unavailable")
            return {"birth": str((created.dwHighDateTime << 32) | created.dwLowDateTime),
                    "running": wait == 258}
        finally:
            kernel.CloseHandle(handle)
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "stat="],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise FixtureError("process_status_unavailable") from None
    if result.returncode == 1 and not result.stdout.strip():
        return None
    require(result.returncode == 0 and len(result.stdout) < 256, "process_status_unavailable")
    fields = result.stdout.decode("ascii", errors="strict").strip().split()
    require(len(fields) == 6, "process_status_shape")
    return {"birth": " ".join(fields[:5]), "running": not fields[5].startswith("Z")}


def validate_child_receipt(config_path: Path, config: dict) -> dict:
    path = config_path.parent / "child-process.json"
    require(path.is_file() and not path.is_symlink(), "shutdown_child_identity")
    value = strict_json(path.read_bytes(), 4096)
    require(isinstance(value, dict) and set(value) == {"schemaVersion", "runID", "pid", "configPath",
                "entrypointPath", "entrypointSHA256", "processBirth"}
            and value["schemaVersion"] == 1 and value["runID"] == config["runID"]
            and value["pid"] == config["pid"] and value["configPath"] == str(config_path.resolve())
            and value["entrypointPath"] == str(Path(__file__).resolve())
            and value["entrypointSHA256"] == digest(Path(__file__).read_bytes())
            and isinstance(value["processBirth"], str) and 1 <= len(value["processBirth"]) <= 80,
            "shutdown_child_identity")
    return value


def listener_is_closed(port: int) -> bool:
    require(type(port) is int and 1 <= port <= 65535, "listener_port")
    if os.name == "nt":
        # Query-only authoritative TCP listener table. A connect attempt to a
        # closed port can time out under Windows filtering instead of refusing.
        # https://learn.microsoft.com/windows/win32/api/iphlpapi/nf-iphlpapi-getextendedtcptable
        from ctypes import wintypes
        class Row(ctypes.Structure):
            _fields_ = [(name, wintypes.DWORD) for name in (
                "state", "localAddress", "localPort", "remoteAddress", "remotePort", "pid")]
        class Table(ctypes.Structure):
            _fields_ = [("count", wintypes.DWORD), ("rows", Row * 1)]
        function = ctypes.WinDLL("iphlpapi", use_last_error=True).GetExtendedTcpTable
        function.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                             wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
        function.restype = wintypes.DWORD
        size = wintypes.DWORD(0)
        require(function(None, ctypes.byref(size), False, socket.AF_INET, 3, 0) == 122,
                "listener_table_size_query")
        for _ in range(3):
            require(Table.rows.offset <= size.value <= 1_048_576, "listener_table_size")
            allocated = size.value
            buffer = ctypes.create_string_buffer(allocated)
            status = function(buffer, ctypes.byref(size), False, socket.AF_INET, 3, 0)
            if status == 122:
                continue
            require(status == 0 and Table.rows.offset <= size.value <= allocated, "listener_table_query")
            count = wintypes.DWORD.from_buffer_copy(buffer).value
            require(count <= 32768 and Table.rows.offset + count * ctypes.sizeof(Row) <= size.value,
                    "listener_table_shape")
            for index in range(count):
                row = Row.from_buffer_copy(buffer, Table.rows.offset + index * ctypes.sizeof(Row))
                require(row.state == 2, "listener_table_state")
                if socket.ntohs(row.localPort & 0xffff) == port:
                    return False
            return True
        raise FixtureError("listener_table_changed_repeatedly")
    try:
        connection = socket.create_connection(("127.0.0.1", port), timeout=0.5)
    except (ConnectionRefusedError, ConnectionResetError):
        return True
    except OSError:
        raise FixtureError("owned_listener_status_unknown") from None
    else:
        connection.close()
        return False


def record_child(config_path: Path, config: dict, pid: int) -> None:
    # Starter and child write the same identity. No secret or body is included.
    value = child_receipt(config_path, config, pid)
    receipt = config_path.parent / "child-process.json"
    if receipt.is_file():
        require(strict_json(receipt.read_bytes(), 4096) == value, "child_receipt_mismatch")
    else:
        atomic_json(receipt, value, private=True)


def control_request(config: dict, route: str, *, method: str = "GET", body: dict | None = None,
                    timeout: float = 5.0) -> tuple[int, dict]:
    env = config.get("testRunnerEnvironment", {})
    url = urllib.parse.urlsplit(env.get(PREFIX + "CONTROL_URL", ""))
    require(url.scheme == "https" and url.hostname == "127.0.0.1"
            and url.port is not None and url.path == "/__fixture"
            and url.username is None and not url.query and not url.fragment, "control_origin")
    context = ssl.create_default_context(cafile=config["rootCAPath"])
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    connection = http.client.HTTPSConnection("127.0.0.1", url.port, timeout=timeout, context=context)
    data = canonical(body) if body is not None else None
    headers = {"Authorization": "Bearer " + config["controlToken"]}
    if data is not None:
        headers["Content-Type"] = "application/json"
    try:
        connection.request(method, "/__fixture" + route, data, headers)
        response = connection.getresponse()
        require(response.getheader("Transfer-Encoding") is None, "control_response_framing")
        length = response.getheader("Content-Length", "")
        require(length.isdecimal() and int(length) <= 65536, "control_response_length")
        payload = response.read(int(length) + 1)
        require(len(payload) == int(length), "control_response_truncated")
        return response.status, strict_json(payload, 65536)
    except FixtureError:
        raise
    except (OSError, ssl.SSLError, http.client.HTTPException):
        raise FixtureError("control_request_failed") from None
    finally:
        connection.close()


class FixtureServer(http.server.ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = True
    allow_reuse_address = False
    request_queue_size = MAX_CONNECTIONS

    def __init__(self, config: dict, config_path: Path):
        self.config = config
        self.config_path = config_path
        self.protocol_state = Protocol(config["runID"])
        self.report_lock = threading.Lock()
        self.first_authentication_rejection = None
        self.connection_slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        self.request_lock = threading.Lock()
        self.request_count = 0
        self.provider_lock = threading.Lock()
        self.handlers_lock = threading.Lock()
        self.owned_sockets = set()
        self.owned_threads = set()
        self.stopping = threading.Event()
        self.tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.tls.minimum_version = ssl.TLSVersion.TLSv1_2
        self.tls.set_alpn_protocols(["http/1.1"])
        self.tls.load_cert_chain(config["serverCertificatePath"], config["serverKeyPath"])
        # Exactly one bind, including port selection; this socket stays owned.
        super().__init__(("127.0.0.1", 0), Handler, bind_and_activate=True)

    def get_request(self):
        connection, address = super().get_request()
        try:
            require(address[0] == "127.0.0.1", "nonloopback_client")
            connection.settimeout(5)
            secured = self.tls.wrap_socket(connection, server_side=True)
            # Bound a partial HTTP request below the five-second shutdown join
            # budget. On Windows, closing another thread's SSLSocket does not
            # reliably wake an in-progress SSL read before its original timeout.
            secured.settimeout(3)
            return secured, address
        except BaseException:
            connection.close()
            raise

    def process_request(self, request, client_address):
        if not self.connection_slots.acquire(blocking=False):
            request.close()
            self.protocol_state.reject("connection_limit")
            self.persist()
            return
        try:
            thread = threading.Thread(target=self.process_request_thread, args=(request, client_address), daemon=True)
            with self.handlers_lock:
                self.owned_sockets.add(request)
                self.owned_threads.add(thread)
            thread.start()
        except BaseException:
            with self.handlers_lock:
                self.owned_sockets.discard(request)
            self.connection_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self.handlers_lock:
                self.owned_sockets.discard(request)
            self.connection_slots.release()

    def server_close(self):
        # Unlike ThreadingMixIn's daemon-thread policy, explicitly close and
        # join every accepted connection we own before a stopped receipt.
        http.server.HTTPServer.server_close(self)
        with self.handlers_lock:
            connections, threads = list(self.owned_sockets), list(self.owned_threads)
        for connection in connections:
            with contextlib.suppress(OSError): connection.shutdown(socket.SHUT_RDWR)
            with contextlib.suppress(OSError): connection.close()
        deadline = time.monotonic() + 5
        for thread in threads:
            if thread is not threading.current_thread() and thread.ident is not None:
                thread.join(timeout=max(0.0, deadline - time.monotonic()))
        require(not any(t.is_alive() for t in threads if t is not threading.current_thread()),
                "owned_handler_shutdown_deadline")

    def handle_error(self, request, client_address):
        self.protocol_state.reject("request_handler_failed")
        self.persist()  # Never print exception, request headers or peer input.

    def record_authentication_rejection(self, method: str, path: str, values: list[str]):
        # Fixed route classes and booleans only: never retain a header value,
        # token, token hash/length, body, URL query, or arbitrary request path.
        routes = {
            ("GET", "/__fixture/status"): "control_status",
            ("POST", "/__fixture/scenario"): "control_scenario",
            ("POST", "/__fixture/shutdown"): "control_shutdown",
            ("POST", "/v1/chat/completions"): "model_chat_completions",
        }
        observation = {
            "schema": AUTHENTICATION_OBSERVATION_SCHEMA,
            "routeClass": routes.get((method, path), "unrecognized"),
            "authorizationHeaderCount": len(values),
            "singleBearerPrefix": len(values) == 1 and values[0].startswith("Bearer "),
            "exactExpectedBearer": False,
            "credentialMaterialRecorded": False,
        }
        with self.report_lock:
            if self.first_authentication_rejection is None:
                self.first_authentication_rejection = observation

    def persist(self):
        with self.report_lock:
            value = self.protocol_state.summary()
            value["httpRequests"] = self.request_count
            value["rootCAFingerprintSHA256"] = self.config["rootCAFingerprintSHA256"]
            if self.first_authentication_rejection is not None:
                value["authenticationRejection"] = dict(self.first_authentication_rejection)
            atomic_json(Path(self.config["safeResultPath"]), value)

    def begin_request(self):
        with self.request_lock:
            self.request_count += 1
            require(self.request_count <= MAX_REQUESTS, "http_request_limit", 429)

    def stop_owned(self):
        if not self.stopping.is_set():
            self.stopping.set()
            threading.Thread(target=self.shutdown, name="fixture-owned-shutdown", daemon=True).start()


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "OwnedHanlinFixture/1"
    sys_version = ""

    def log_message(self, format, *args):
        pass

    def log_error(self, format, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        # BaseHTTPRequestHandler may otherwise reflect the request line.
        self.close_connection = True
        self._json(code, {"error": {"code": "invalid_http_request"}})

    def _json(self, status: int, value: dict):
        payload = canonical(value)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        if self.close_connection:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def _base(self):
        self.server.begin_request()
        require(self.request_version == "HTTP/1.1", "http_version")
        require(sum(len(k) + len(v) for k, v in self.headers.items()) <= 16384, "http_headers_size")
        require(self.headers.get_all("Host", []) == [f"127.0.0.1:{self.server.server_port}"], "http_host")
        require(self.headers.get("Transfer-Encoding") is None and self.headers.get("Expect") is None,
                "request_transfer_encoding")
        require("?" not in self.path and "#" not in self.path, "request_query")

    def _authorized(self, token: str):
        values = self.headers.get_all("Authorization", [])
        try:
            require(len(values) == 1 and hmac.compare_digest(values[0].encode("utf-8"), ("Bearer " + token).encode("ascii")),
                    "request_authentication", 401)
        except FixtureError:
            # Preserve the original authentication exception and rejection path.
            # The observation is in memory; the existing _failure/persist path
            # writes it to the same finite safe fixture report before cleanup.
            try:
                self.server.record_authentication_rejection(self.command, self.path, values)
            except Exception:
                pass  # Optional diagnostics cannot replace the original 401.
            raise

    def _body(self, maximum: int):
        lengths = self.headers.get_all("Content-Length", [])
        require(len(lengths) == 1 and lengths[0].isascii() and lengths[0].isdecimal()
                and 0 < int(lengths[0]) <= maximum, "request_content_length", 413)
        require(self.headers.get_content_type() == "application/json", "request_content_type", 415)
        data = self.rfile.read(int(lengths[0]))
        require(len(data) == int(lengths[0]), "request_body_truncated")
        return data

    def _failure(self, error: FixtureError):
        self.server.protocol_state.reject(error.code)
        self.server.persist()
        self.close_connection = True
        self._json(error.status, {"error": {"code": error.code}})

    def do_GET(self):
        try:
            self._base()
            require(self.headers.get("Content-Length") in (None, "0"), "get_with_body")
            if self.path == "/__fixture/ready":
                self._json(200, {"schema": 1, "contract": CONTRACT, "ready": True})
                return
            require(self.path == "/__fixture/status", "unknown_route", 404)
            self._authorized(self.server.config["controlToken"])
            self._json(200, self.server.protocol_state.summary())
        except FixtureError as error:
            self._failure(error)

    def do_POST(self):
        try:
            self._base()
            if self.path == "/v1/chat/completions":
                self._authorized(self.server.config["modelKey"])
                body = self._body(MAX_BODY)
                require(self.server.provider_lock.acquire(timeout=15), "provider_delivery_deadline", 409)
                try:
                    phase, chunks = self.server.protocol_state.accept(body)
                    self.server.persist()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Content-Length", str(sum(map(len, chunks))))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    for chunk in chunks:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    self.server.protocol_state.response_delivered(phase)
                    self.server.persist()
                finally:
                    self.server.provider_lock.release()
                return
            require(self.path in ("/__fixture/scenario", "/__fixture/shutdown"), "unknown_route", 404)
            self._authorized(self.server.config["controlToken"])
            data = self._body(16384)
            if self.path == "/__fixture/scenario":
                result = self.server.protocol_state.register(data)
                self.server.persist()
                self._json(201, result)
                return
            require(strict_json(data) == {}, "shutdown_body")
            self.close_connection = True
            self._json(200, {"schema": 1, "contract": CONTRACT, "shutdownAccepted": True})
            self.server.stop_owned()
        except FixtureError as error:
            self._failure(error)
        except (OSError, ssl.SSLError):
            self.server.protocol_state.reject("response_delivery_failed")
            self.server.persist()
            self.close_connection = True


def serve(config_path: Path) -> None:
    config = load_config(config_path)
    record_child(config_path, config, os.getpid())
    server = FixtureServer(config, config_path)
    origin = f"https://127.0.0.1:{server.server_port}"
    config.update({"pid": os.getpid(), "testRunnerEnvironment": {
        PREFIX + "URL": origin + "/v1", PREFIX + "MODEL": MODEL,
        PREFIX + "KEY": config["modelKey"], PREFIX + "CONTROL_URL": origin + "/__fixture",
        PREFIX + "CONTROL_TOKEN": config["controlToken"],
    }})
    server.config = config
    atomic_json(config_path, config, private=True)
    server.persist()

    def expired():
        if not server.protocol_state.summary()["complete"]:
            server.protocol_state.reject("fixture_deadline_expired")
        server.stop_owned()

    timer = threading.Timer(config["maxAgeSeconds"], expired)
    timer.daemon = True
    timer.start()

    def terminated(signum, frame):
        if not server.protocol_state.summary()["complete"]:
            server.protocol_state.reject("fixture_process_terminated")
        server.stop_owned()

    signal.signal(signal.SIGTERM, terminated)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, terminated)
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        timer.cancel()
        server.server_close()
        server.protocol_state.stopped = True
        server.persist()
        atomic_json(config_path.parent / "stopped.json", {
            "schema": 1, "runID": config["runID"], "pid": os.getpid(), "stopped": True}, private=True)


def start(args) -> None:
    directory = private_directory(args.private_dir)
    safe_path = Path(args.safe_result).absolute()
    require(not safe_path.is_relative_to(directory), "safe_report_inside_private_directory")
    require(60 <= args.max_age_seconds <= 7200, "fixture_deadline")
    openssl = args.openssl or shutil.which("openssl")
    require(openssl is not None, "openssl_unavailable")
    process = None
    try:
        root, fingerprint = generate_identity(directory, openssl)
        config = {
            "schemaVersion": 1, "contract": CONTRACT, "runID": str(uuid.uuid4()),
            "privateDirectory": str(directory), "safeResultPath": str(safe_path),
            "rootCAPath": str(root), "rootCAFingerprintSHA256": fingerprint,
            "serverCertificatePath": str(directory / "server-cert.pem"),
            "serverKeyPath": str(directory / "server-key.pem"),
            "modelKey": "fixture-" + secrets.token_urlsafe(32),
            "controlToken": "control-" + secrets.token_urlsafe(32),
            "maxAgeSeconds": args.max_age_seconds, "pid": None,
        }
        config_path = directory / CONFIG_NAME
        atomic_json(config_path, config, private=True)
        options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            options["start_new_session"] = True
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_serve",
                                    "--private-config", str(config_path)], **options)
        record_child(config_path, config, process.pid)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            require(process.poll() is None, "fixture_child_exited")
            current = load_config(config_path)
            if current.get("pid") == process.pid and "testRunnerEnvironment" in current:
                try:
                    status, reply = control_request(current, "/ready", timeout=2)
                    if status == 200 and reply == {"schema": 1, "contract": CONTRACT, "ready": True}:
                        safe_output({"schema": 1, "status": "FIXTURE_READY", "runID": current["runID"],
                                     "rootCAFingerprintSHA256": fingerprint,
                                     "explicitTemporaryCATLSVerified": True})
                        return
                except FixtureError:
                    pass
            time.sleep(0.05)
        raise FixtureError("fixture_start_deadline")
    except BaseException:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()  # Only the child Popen object created above.
                process.wait(timeout=5)
        if process is not None:
            atomic_json(directory / "start-failed.json", {
                "schemaVersion": 1, "runID": config["runID"], "pid": process.pid,
                "ownedChildReaped": process.poll() is not None}, private=True)
        raise


def inspect_or_verify(args, *, verify: bool):
    config = load_config(Path(args.private_config).absolute())
    status, result = control_request(config, "/status")
    require(status == 200 and result.get("contract") == CONTRACT
            and result.get("runID") == config["runID"], "status_contract")
    if args.safe_result:
        atomic_json(Path(args.safe_result).absolute(), result)
    safe_output(result)
    if verify:
        require(result.get("complete") is True and result.get("state") == "complete"
                and result.get("phase") == 6 and result.get("responsesDelivered") == 6,
                "fixture_protocol_incomplete", 409)


def stop(args):
    path = Path(args.private_config).absolute()
    config = load_config(path)
    initializing_deadline = time.monotonic() + 8
    while not config.get("testRunnerEnvironment") or config.get("pid") is None:
        failed = path.parent / "start-failed.json"
        if failed.is_file():
            failure = strict_json(failed.read_bytes(), 4096)
            require(failure.get("runID") == config["runID"] and failure.get("ownedChildReaped") is True,
                    "startup_failure_unproven")
            safe_output({"schema": 1, "status": "FIXTURE_STOPPED", "runID": config["runID"],
                         "startupFailedOwnedChildReaped": True, "privateMaterialRemoved": False,
                         "simulatorTrustRemoved": False})
            return
        require(time.monotonic() < initializing_deadline, "shutdown_startup_unresolved")
        time.sleep(0.05)
        config = load_config(path)
    identity = validate_child_receipt(path, config)
    stopped = path.parent / "stopped.json"
    if stopped.is_file():
        value = strict_json(stopped.read_bytes(), 4096)
        require(value.get("runID") == config["runID"] and value.get("pid") == config["pid"]
                and value.get("stopped") is True, "stop_receipt_mismatch")
    else:
        status, result = control_request(config, "/shutdown", method="POST", body={})
        require(status == 200 and result.get("shutdownAccepted") is True, "shutdown_refused")
        deadline = time.monotonic() + 8
        while not stopped.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        require(stopped.is_file(), "shutdown_deadline")
        value = strict_json(stopped.read_bytes(), 4096)
        require(value.get("runID") == config["runID"] and value.get("pid") == config["pid"]
                and value.get("stopped") is True, "stop_receipt_mismatch")
    deadline = time.monotonic() + 5
    while True:
        observed = process_identity(config["pid"])
        if observed is None or observed["birth"] != identity["processBirth"] or not observed["running"]:
            break
        require(time.monotonic() < deadline, "owned_child_exit_deadline")
        time.sleep(0.05)
    origin = urllib.parse.urlsplit(config["testRunnerEnvironment"][PREFIX + "CONTROL_URL"])
    require(listener_is_closed(origin.port), "owned_listener_still_accepting")
    safe_output({"schema": 1, "status": "FIXTURE_STOPPED", "runID": config["runID"],
                 "ownedChildExited": True, "ownedListenerClosed": True,
                 "listenerObservation": "windows_owner_pid_listener_table" if os.name == "nt" else "posix_connect_refused",
                 "privateMaterialRemoved": False, "simulatorTrustRemoved": False})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    begin = sub.add_parser("start")
    begin.add_argument("--private-dir", required=True)
    begin.add_argument("--safe-result", required=True)
    begin.add_argument("--openssl")
    begin.add_argument("--max-age-seconds", type=int, default=3600)
    for command in ("inspect", "verify", "stop", "_serve"):
        child = sub.add_parser(command)
        child.add_argument("--private-config", required=True)
        if command in ("inspect", "verify"):
            child.add_argument("--safe-result")
    args = parser.parse_args()
    previous_umask = os.umask(0o077) if os.name != "nt" else None
    try:
        if args.command == "start":
            start(args)
        elif args.command in ("inspect", "verify"):
            inspect_or_verify(args, verify=args.command == "verify")
        elif args.command == "stop":
            stop(args)
        else:
            serve(Path(args.private_config).absolute())
        return 0
    except FixtureError as error:
        if args.command != "_serve":
            safe_output({"schema": 1, "status": "FIXTURE_ERROR", "code": error.code})
        return 1
    except BaseException:
        if args.command != "_serve":
            safe_output({"schema": 1, "status": "FIXTURE_ERROR", "code": "unexpected_fixture_failure"})
        return 1
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())

