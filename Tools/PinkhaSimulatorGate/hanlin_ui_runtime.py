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
DIAGNOSTIC_STAGES = frozenset({
    "prepare_data_container", "prepare_installed_source", "poll_data_container",
    "read_native_phase_before", "validate_native_phase_before", "save_partial_phase_before",
    "map_installed_source", "map_running_process", "after_mapping_data_container",
    "read_native_phase_after", "export_final_data_container", "export_final_native_result",
    "verify_ui_process_boundaries",
})
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
        self.diagnostic_lock = threading.Lock()
        self.diagnostic_stages = {}
        self.diagnostic_failure = None
        self.partial_observations = {}
        self.finalization_receipt = None

    def diagnostic_operation(self, stage, operation, *, transient=()):
        """Record bounded metadata without retrying or changing an operation's result.

        The elapsed value covers this named stage, which may contain several
        commands. TimeoutExpired supplies the exact failing argv and command
        timeout; its stdout/stderr and arbitrary exception text are never copied.
        Repeated polling updates one fixed-size stage record.
        """
        require(stage in DIAGNOSTIC_STAGES, "Unknown runtime diagnostic stage")
        started = time.monotonic()
        with self.diagnostic_lock:
            record = self.diagnostic_stages.setdefault(stage, {"stage": stage, "attempts": 0})
            record.update(attempts=record["attempts"] + 1, status="STARTED",
                          started_at=datetime.now(timezone.utc).timestamp())
        status, failure = "RETURNED", None
        try:
            return operation()
        except BaseException as error:
            status = "TRANSIENT_READ" if isinstance(error, transient) else "FAILED"
            if status == "FAILED":
                failure = {"stage": stage, "error_type": type(error).__name__}
                if isinstance(error, (subprocess.TimeoutExpired, subprocess.CalledProcessError)):
                    command = error.cmd
                    if (isinstance(command, (list, tuple)) and 0 < len(command) <= 32
                            and all(isinstance(arg, str) and len(arg) <= 2048 for arg in command)):
                        failure["command"] = list(command)
                    else:
                        failure["command"] = "UNAVAILABLE_OR_OUTSIDE_DIAGNOSTIC_BOUND"
                    if isinstance(error, subprocess.TimeoutExpired):
                        failure["command_timeout_seconds"] = error.timeout
                    else:
                        failure["command_exit_code"] = error.returncode
            raise
        finally:
            elapsed = max(0, time.monotonic() - started)
            with self.diagnostic_lock:
                record.update(status=status, stage_elapsed_seconds=elapsed,
                              finished_at=datetime.now(timezone.utc).timestamp())
                if failure is not None and self.diagnostic_failure is None:
                    self.diagnostic_failure = {**failure, "stage_elapsed_seconds": elapsed}

    def retain_partial(self, key, value):
        with self.diagnostic_lock:
            self.partial_observations[key] = value

    def diagnostic_summary(self):
        with self.diagnostic_lock:
            return json.loads(json.dumps({"diagnostic_only": True,
                "stage_duration_scope": "ENTIRE_NAMED_OPERATION_NOT_INDIVIDUAL_SUBPROCESS",
                "stages": list(self.diagnostic_stages.values()),
                "first_failure": self.diagnostic_failure,
                "partial_observations": self.partial_observations}))

    def persist_summary(self, *, write_file=True):
        snapshot = self.summary()
        if self.finalization_receipt is not None:
            self.finalization_receipt["actual_ui_runtime_observation"] = snapshot
        if write_file:
            self.shared.write(self.directory / "observation.json", snapshot)
        return snapshot

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
        container = self.diagnostic_operation("prepare_data_container", lambda: self.container(self.timeout))
        require(not (container / SUPPORT / RESULT).exists(), "Refuse a pre-existing native UI result")
        before_directory = self.directory / "before-ui"
        before_directory.mkdir()
        self.before_source = self.diagnostic_operation("prepare_installed_source", lambda:
            self.shared.installed_runtime_source(self.udid, before_directory, self.built,
                self.source_identity, command_timeout=self.timeout))
        self.thread = threading.Thread(target=self.observe, name="sdk06-runtime-observer", daemon=True)
        self.thread.start()

    def observe(self):
        try:
            while True:
                self.timeout()
                container = self.diagnostic_operation("poll_data_container", lambda: self.container(self.timeout))
                try:
                    before_raw = self.diagnostic_operation("read_native_phase_before",
                        lambda: stable_bytes(container / SUPPORT / RESULT),
                        transient=(FileNotFoundError, ReceiptReplaced))
                except (FileNotFoundError, ReceiptReplaced):
                    self.stop_event.wait(0.25)
                    continue
                before = decode(before_raw)
                identity = self.diagnostic_operation("validate_native_phase_before", lambda:
                    receipt_identity(before, self.fixture, self.started_at,
                        datetime.now(timezone.utc).timestamp(), inflight=True))
                self.deadline = min(self.deadline, time.monotonic() + MAPPING_SECONDS)
                partial_before = self.directory / "partial-native-phase-before.json"
                self.diagnostic_operation("save_partial_phase_before", lambda: partial_before.write_bytes(before_raw))
                self.retain_partial("native_phase_before", {"file": partial_before.name,
                    "sha256": digest(before_raw), "identity": identity,
                    "status": "OBSERVED_IDENTITY_RUNTIME_NOT_YET_BOUND"})
                source = self.diagnostic_operation("map_installed_source", lambda:
                    self.shared.installed_runtime_source(self.udid, self.directory, self.built,
                        self.source_identity, command_timeout=self.timeout))
                self.retain_partial("installed_source_returned", {"file": "installed-app-source.json",
                    "installed_app_executable_sha256": source["installed_app_executable_sha256"],
                    "built_app_executable_sha256": source["built_app_executable_sha256"],
                    "installed_code_carriers_sha256": source["installed_code_carriers"]["sha256"],
                    "built_code_carriers_sha256": source["built_code_carriers"]["sha256"]})
                installed = Path(source["installed_app"])
                require(installed.is_absolute() and self.udid.lower() in {p.lower() for p in installed.parts},
                        "Mapped application is outside the owned simulator")
                require(all(source[key] == self.before_source[key] for key in
                    ("installed_app_executable_sha256", "built_app_executable_sha256"))
                    and all(source[key]["sha256"] == self.before_source[key]["sha256"]
                            for key in ("installed_code_carriers", "built_code_carriers")),
                    "Application executable bytes changed between pre-UI validation and actual process mapping")
                mapped = self.diagnostic_operation("map_running_process", lambda:
                    self.shared.observe_running_runtime(identity["processID"], self.directory, self.built,
                        source, command_timeout=self.timeout,
                        metadata={"observation_source": "ACTUAL_NATIVE_UI_RECEIPT_NO_LAUNCH"}))
                self.retain_partial("runtime_mapping_returned", {"file": "live-runtime.json",
                    "pid": mapped["pid"], "runtime_sha256": mapped["runtime_sha256"],
                    "process_start_identity": mapped["process_start_identity"],
                    "status": "MAPPING_RETURNED_FINAL_NATIVE_BINDING_NOT_YET_VERIFIED"})
                after_container = self.diagnostic_operation("after_mapping_data_container",
                    lambda: self.container(self.timeout))
                require(after_container == container, "Actual UI container changed during process mapping")
                while True:
                    self.timeout()
                    try:
                        after_raw = self.diagnostic_operation("read_native_phase_after",
                            lambda: stable_bytes(container / SUPPORT / RESULT),
                            transient=(FileNotFoundError, ReceiptReplaced))
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
        result = dict(self.observation or {"status": "FAIL_ACTUAL_UI_RUNTIME_NOT_BOUND",
            "error_type": type(self.error).__name__ if self.error else "ObservationIncomplete",
            "extra_app_launches": 0, "every_launch_verified": False})
        result["diagnostics"] = self.diagnostic_summary()
        return result

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
        path = self.diagnostic_operation("export_final_data_container", lambda: self.container(timeout)) / SUPPORT / RESULT
        return self.diagnostic_operation("export_final_native_result", lambda: stable_bytes(path))

    def finalize(self, receipt, result_path, export_console, active_error):
        # A secondary evidence error must neither hide the UI/start failure nor
        # prevent the remaining original evidence from being attempted.
        self.finalization_receipt = receipt
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
            self.error = self.error or failures[0][1]
            self.observation = None
        # Export can itself discover a bounded command failure. Capture those
        # diagnostics after all exports, and update the execution receipt too.
        # A failed stop write is not retried; its in-memory receipt can still be
        # refreshed without hiding the original stop/selection exception.
        write_final_file = not any(stage == "observer_stop" for stage, _ in failures)
        attempt("final_observer_snapshot", lambda: self.persist_summary(write_file=write_final_file))
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
        primary_error = None
        try:
            continuity = self.diagnostic_operation("verify_ui_process_boundaries", lambda:
                self.shared.verify_ui_process_continuity(ui_evidence, prefix,
                    self.observation["live_runtime"], methods, scope="ACTUAL_COLD_LAUNCH_UI_METHOD_BOUNDARIES",
                    command_timeout=lambda: COMMAND_SECONDS))
        except BaseException as error:
            primary_error = error
            raise
        finally:
            try:
                self.persist_summary()
            except BaseException:
                # Persisted metadata must not replace the actual boundary error.
                # With no primary failure a failed diagnostic write still fails
                # closed before a qualification receipt can be written.
                if primary_error is None:
                    raise
        result = {**self.observation, "status": "PASS_ACTUAL_UI_PROCESS_RUNTIME",
                  "ui_process_continuity": continuity,
                  "final_native_receipt_sha256": digest(raw_value),
                  "full_sdk_acceptance": False}
        self.shared.write(self.directory / "qualification.json", result)
        return result
