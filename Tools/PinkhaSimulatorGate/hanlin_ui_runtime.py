"""Read-only runtime mapping of the process executing the original SDK06 UI journey.

The native driver already atomically publishes source-bound phase receipts. Observe
one while the real UI method is running; never launch a substitute probe process.
The independent native validator and all 22 existing checks remain mandatory.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
import time

import hanlin_acceptance_evidence as native

FIXTURE = "pinkha-hanlin-native-fixture.json"
RESULT = "pinkha-hanlin-native-result.json"
SUPPORT = Path("Library/Application Support")
MAX_BYTES = 65_536
COMMAND_SECONDS = 10
OBSERVATION_SECONDS = 420
MAPPING_SECONDS = 45
IDENTITY_KEYS = ("fixtureID", "sourceSHA", "runID", "runAttempt", "processID", "startedAt",
                 "sessionID", "navigationContext")
INFLIGHT_PHASES = frozenset({
    "AWAIT_READ_CONSENT", "AWAIT_CANCEL_CREATE", "AWAIT_CONFIRM_CREATE", "READY_TO_CLOSE",
    "AWAIT_BACKGROUND_PRESENTATION", "AWAIT_BACKGROUND_READ_CONSENT", "READY_FOR_BACKGROUND",
    "AWAIT_STALE_CONSENT_PRESENTATION", "AWAIT_STALE_READ_CONSENT", "READY_TO_LEAVE_WITH_PENDING_CONSENT",
    "AWAIT_FRESH_PRESENTATION", "AWAIT_FRESH_READ_CONSENT", "READY_TO_CLOSE_FRESH", "CHECKING_NATIVE_AUTHORITY",
})


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class ReceiptReplaced(Exception):
    """An atomic phase update crossed this read. No partial snapshot qualifies."""


def stable_bytes(path):
    require(path.resolve(strict=True) == path.absolute(), "Native runtime evidence contains a symlink")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= MAX_BYTES,
            "Native runtime evidence is not one bounded regular file")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if not all(getattr(before, k) == getattr(opened, k) == getattr(after, k) == getattr(current, k)
               for k in fields):
        raise ReceiptReplaced()
    require(stat.S_ISREG(current.st_mode) and len(raw) == before.st_size,
            "Native runtime evidence changed while read")
    return raw


def decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "Duplicate native runtime receipt key")
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs)
    require(isinstance(value, dict), "Native runtime receipt is not an object")
    return value


def receipt_identity(value, fixture, started_after, now, *, inflight):
    require(all(value.get(key) == fixture[key] for key in ("fixtureID", "sourceSHA", "runID", "runAttempt")),
            "Runtime receipt belongs to another fixture/source/run")
    require(type(value.get("processID")) is int and value["processID"] > 1,
            "Actual native UI process identity is missing")
    started = native.apple_timestamp(value.get("startedAt"), "runtime receipt start")
    require(started_after <= started <= now, "Runtime receipt predates this UI selection")
    native.uuid_text(value.get("sessionID"), "runtime receipt session")
    context = value.get("navigationContext")
    require(isinstance(context, dict) and set(context) == native.NAVIGATION_CONTEXT_KEYS
            and context.get("app") == "anytype" and context.get("account") == fixture["accountID"]
            and context.get("space") == context.get("workspace") == fixture["spaceID"]
            and context.get("objectReference") == fixture["sourceObjectID"]
            and context.get("selectionReferences") == [], "Runtime receipt has another native document/account")
    require(value.get("failure") is None and value.get("providerConfigured") is False,
            "Failed or provider-configured runtime receipt cannot qualify")
    if inflight:
        require(value.get("phase") in INFLIGHT_PHASES and value.get("finishedAt") is None,
                "Runtime mapping requires a live unfinished native UI phase")
    return {key: value[key] for key in IDENTITY_KEYS}


class NativeUIRuntimeObserver:
    def __init__(self, udid, evidence, built, fixture, raw_fixture, source_identity, shared):
        self.udid, self.evidence, self.built = udid, evidence, built
        self.fixture = json.loads(json.dumps(fixture))
        self.fixture_bytes = raw_fixture.encode("utf-8")
        require(decode(self.fixture_bytes) == self.fixture, "Original runtime fixture bytes differ")
        self.source_identity, self.shared = dict(source_identity), shared
        require(all(self.fixture[key] == self.source_identity[field] for key, field in
                    (("sourceSHA", "source_sha"), ("runID", "run_id"), ("runAttempt", "run_attempt"))),
                "Runtime observer source differs from the actual native fixture")
        self.directory = evidence / "actual-ui-runtime"
        require(not self.directory.exists(), "Refuse stale actual UI runtime observations")
        self.directory.mkdir()
        self.stop_event = threading.Event()
        self.thread = None
        self.error = None
        self.observation = None

    def timeout(self):
        require(not self.stop_event.is_set(), "Actual UI runtime observation cancelled")
        available = self.deadline - time.monotonic()
        require(available > 0, "Actual UI runtime observation timed out")
        return min(COMMAND_SECONDS, available)

    def container(self, timeout):
        raw = subprocess.check_output(["xcrun", "simctl", "get_app_container", self.udid,
                                       "io.anytype.app", "data"], text=True, timeout=timeout()).strip()
        path = Path(raw)
        require("\n" not in raw and path.is_absolute() and path.is_dir() and not path.is_symlink(),
                "Actual UI data container is unavailable")
        path = path.resolve(strict=True)
        require(self.udid.lower() in {part.lower() for part in path.parts},
                "Actual UI data container is outside the owned simulator")
        require(stable_bytes(path / SUPPORT / FIXTURE) == self.fixture_bytes,
                "Actual UI no longer has its original native fixture bytes")
        return path

    def start(self):
        require(self.thread is None, "Actual UI runtime observer was already started")
        self.started_at = datetime.now(timezone.utc).timestamp()
        self.deadline = time.monotonic() + OBSERVATION_SECONDS
        container = self.container(self.timeout)
        require(not (container / SUPPORT / RESULT).exists(), "Refuse a pre-existing native UI result")
        before_directory = self.directory / "before-ui"
        before_directory.mkdir()
        self.before_source = self.shared.installed_runtime_source(self.udid, before_directory, self.built,
            self.source_identity, command_timeout=self.timeout)
        self.thread = threading.Thread(target=self.observe, name="sdk06-runtime-observer", daemon=True)
        self.thread.start()

    def observe(self):
        try:
            while True:
                self.timeout()
                container = self.container(self.timeout)
                try:
                    before_raw = stable_bytes(container / SUPPORT / RESULT)
                except (FileNotFoundError, ReceiptReplaced):
                    self.stop_event.wait(0.25)
                    continue
                before = decode(before_raw)
                identity = receipt_identity(before, self.fixture, self.started_at,
                    datetime.now(timezone.utc).timestamp(), inflight=True)
                self.deadline = min(self.deadline, time.monotonic() + MAPPING_SECONDS)
                source = self.shared.installed_runtime_source(self.udid, self.directory, self.built,
                    self.source_identity, command_timeout=self.timeout)
                installed = Path(source["installed_app"])
                require(installed.is_absolute() and self.udid.lower() in {p.lower() for p in installed.parts},
                        "Mapped application is outside the owned simulator")
                require(all(source[key] == self.before_source[key] for key in
                    ("installed_app_executable_sha256", "built_app_executable_sha256"))
                    and all(source[key]["sha256"] == self.before_source[key]["sha256"]
                            for key in ("installed_code_carriers", "built_code_carriers")),
                    "Application executable bytes changed between pre-UI validation and actual process mapping")
                mapped = self.shared.observe_running_runtime(identity["processID"], self.directory, self.built,
                    source, command_timeout=self.timeout,
                    metadata={"observation_source": "ACTUAL_NATIVE_UI_RECEIPT_NO_LAUNCH"})
                after_container = self.container(self.timeout)
                require(after_container == container, "Actual UI container changed during process mapping")
                while True:
                    self.timeout()
                    try:
                        after_raw = stable_bytes(container / SUPPORT / RESULT)
                        break
                    except (FileNotFoundError, ReceiptReplaced):
                        # The driver atomically replaces this file for each
                        # phase. Retry only the incomplete read, never identity.
                        self.stop_event.wait(0.01)
                after = decode(after_raw)
                require(receipt_identity(after, self.fixture, self.started_at,
                        datetime.now(timezone.utc).timestamp(), inflight=False) == identity,
                        "Native receipt changed process/session while its runtime was mapped")
                self.timeout()
                (self.directory / "native-phase-before.json").write_bytes(before_raw)
                (self.directory / "native-phase-after.json").write_bytes(after_raw)
                self.observation = {"status": "MAPPED_ACTUAL_UI_PROCESS_FINAL_BINDING_PENDING",
                    "identity": identity, "live_runtime": mapped,
                    "before_receipt_sha256": digest(before_raw), "after_receipt_sha256": digest(after_raw),
                    "selection_started_at": self.started_at,
                    "mapping_completed_at": datetime.now(timezone.utc).timestamp(),
                    "extra_app_launches": 0, "every_launch_verified": False}
                break
        except BaseException as error:
            self.error = error
        finally:
            self.shared.write(self.directory / "observation.json", self.summary())

    def summary(self):
        return self.observation or {"status": "FAIL_ACTUAL_UI_RUNTIME_NOT_BOUND",
            "error_type": type(self.error).__name__ if self.error else "ObservationIncomplete",
            "extra_app_launches": 0, "every_launch_verified": False}

    def stop(self):
        self.stop_event.set()
        # Thread.start() may raise before starting or after creating its worker.
        # A created worker keeps its ident after exit; an unstarted Thread cannot
        # be joined. A delayed worker sees stop_event before its first command.
        if self.thread is not None and self.thread.ident is not None:
            self.thread.join(COMMAND_SECONDS + 5)
            if self.thread.is_alive():
                self.error = RuntimeError("Actual UI runtime observer did not finish within its stop bound")
                self.observation = None
        self.shared.write(self.directory / "observation.json", self.summary())

    def final_bytes(self):
        # This read is separate from the stopped observer and cannot extend its
        # lifetime. The original fixture and current owned root are checked again.
        timeout = lambda: COMMAND_SECONDS
        path = self.container(timeout) / SUPPORT / RESULT
        return stable_bytes(path)

    def finalize(self, receipt, result_path, export_console, active_error):
        # A secondary evidence error must neither hide the UI/start failure nor
        # prevent the remaining original evidence from being attempted.
        failures = []
        def attempt(stage, action):
            try:
                return action()
            except BaseException as error:
                failures.append((stage, error))
                return None
        attempt("observer_stop", self.stop)
        observation = attempt("observer_summary", self.summary)
        if observation is not None:
            receipt["actual_ui_runtime_observation"] = observation
        attempt("console_export", export_console)
        def export_result():
            try:
                raw = self.final_bytes()
            except FileNotFoundError:
                return
            result_path.write_bytes(raw)
        attempt("native_receipt_export", export_result)
        if failures:
            receipt["actual_ui_runtime_finalizer"] = {"status": "FAIL", "errors": [
                {"stage": stage, "error_type": type(error).__name__} for stage, error in failures]}
            self.error = self.error or failures[0][1]
            self.observation = None
            if active_error is None:
                raise failures[0][1]

    def qualify(self, value, raw_value, ui_evidence, prefix, methods):
        require(self.thread is not None and not self.thread.is_alive()
                and self.error is None and self.observation is not None,
                "Actual UI runtime observer did not complete successfully")
        identity = receipt_identity(value, self.fixture, self.started_at,
            datetime.now(timezone.utc).timestamp(), inflight=False)
        require(decode(raw_value) == value, "Final native receipt bytes differ from the qualified value")
        require(identity == self.observation["identity"], "Final native receipt belongs to another process/session")
        require(value.get("phase") == "NATIVE_ACCEPTANCE_PASS", "Native acceptance did not pass")
        finished = native.apple_timestamp(value.get("finishedAt"), "runtime receipt finish")
        require(native.apple_timestamp(value["startedAt"], "runtime receipt start")
                <= self.observation["mapping_completed_at"] <= finished,
                "Runtime mapping did not finish during the actual native UI journey")
        continuity = self.shared.verify_ui_process_continuity(ui_evidence, prefix,
            self.observation["live_runtime"], methods, scope="ACTUAL_COLD_LAUNCH_UI_METHOD_BOUNDARIES",
            command_timeout=lambda: COMMAND_SECONDS)
        result = {**self.observation, "status": "PASS_ACTUAL_UI_PROCESS_RUNTIME",
                  "ui_process_continuity": continuity,
                  "final_native_receipt_sha256": digest(raw_value),
                  "full_sdk_acceptance": False}
        self.shared.write(self.directory / "qualification.json", result)
        return result
