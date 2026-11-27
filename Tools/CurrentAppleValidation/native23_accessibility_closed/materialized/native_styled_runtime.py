"""Owned NativeUI typography rendezvous; the original runner owns execution.

This helper never admits products, builds, selects a different device, or calls
the native engine. It services exactly two requests from the admitted XCTest
runner while the unchanged original `run` function owns xcodebuild and its
process group. Every command still goes through that function. Actual XCTest
and typed observation acceptance remain separate from coordination receipts.
"""
from __future__ import annotations

import copy
import ast
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import subprocess
import threading
import time
import types
import uuid

TARGET = "PinkhaAnyNativeUITests"
STAGES = {
    "styled-blocks": ("NativeLaunchTests/testTypedBlockMenusPersistAllNineKindsAndColdReopen", 1800),
    "styled-live-type": ("NativeLaunchTests/testNativeStyledTypographyRefreshesLiveAtAccessibilitySize", 900),
}
ENVIRONMENT = ("PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_JSON", "PINKHA_NATIVE_ACCESSIBILITY_CONTEXT_SHA256")
CONTEXT_KEYS = {"schema", "runID", "appSourceCommit", "uiSourceCommit", "simulatorUDID", "ownedScope",
                "method", "appLanguage", "osLanguage", "contentSize", "appearance", "deviceFamily",
                "settingsReadbackSHA256"}
PHASES = (("expanded", "accessibility-extra-extra-extra-large"), ("restored", "large"))
CONTROL_SCHEMA = "native-styled-live-control/v1"
CONTROL_PASS = "PASS_REQUESTS_AND_RESTORED_NOT_UI_ACCEPTANCE"
ORIGINAL_RUN_SHA256 = "5ea092b2a4d7159e8dec45b264224811e24e64265493a1e4958e4937b5fecaad"
ORIGINAL_LIFECYCLE_SHA256 = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"


def original_execution_binding(c, run):
    c.require(isinstance(run, types.FunctionType) and run.__closure__ is None,
              "Exact original top-level run function required")
    path = Path(run.__globals__["__file__"])
    c.require(path.is_absolute() and path.resolve() == path and not path.is_symlink()
              and str(path) == run.__code__.co_filename, "Original runner code filename must remain bound")
    raw = c.raw(path, 128 * 1024)
    text = raw.decode()
    nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == "run"]
    c.require(len(nodes) == 1 and c.sha(ast.get_source_segment(text, nodes[0]).encode()) == ORIGINAL_RUN_SHA256,
              "Original run function body changed")
    materialization = c.decode(c.raw(path.with_name("nativeui16-materialization.json"), 128 * 1024))
    c.require(materialization["controllers"][path.name]["candidateSHA256"] == c.sha(raw)
              and materialization["files"][path.name]["sha256"] == c.sha(raw),
              "Actual original runner must match its reviewed materialization")
    lifecycle = run.__globals__["LIFECYCLE"]
    c.require(lifecycle is not None and run.__globals__["subprocess"] is subprocess,
              "Actual original owned lifecycle and standard subprocess module required")
    lifecycle_path = Path(lifecycle._terminate_owned_process.__func__.__globals__["__file__"])
    c.require(lifecycle_path == Path(lifecycle._observe_exited_group.__func__.__globals__["__file__"])
              and lifecycle_path.resolve() == lifecycle_path and not lifecycle_path.is_symlink()
              and c.digest(lifecycle_path) == ORIGINAL_LIFECYCLE_SHA256,
              "Actual unmodified original73bb lifecycle helper required")
    return lifecycle, {"originalRunController": pin(c, path, 128 * 1024),
        "originalRunDeclarationSHA256": ORIGINAL_RUN_SHA256, "originalLifecycleSHA256": ORIGINAL_LIFECYCLE_SHA256,
        "runtimeAdapterSHA256": c.digest(Path(__file__)),
        "scope": "Isolated run globals capture the exact Popen and add post-exception owned cleanup; original function body is preserved, executed behavior is adapted"}


class OwnedExecutionBoundary:
    """Capture one exact Popen before the original function can fail to log it."""
    def __init__(self, c, lifecycle, argv, binding):
        self.c, self.lifecycle, self.argv, self.binding = c, lifecycle, list(argv), binding
        self.process = None
        self.observations = []
        self.absent = self.closed = False
        self.finished = self.failure_started = False
        self.record = {"schema": "native-styled-owned-execution-closure/v1", "status": "NOT_STARTED",
                       "binding": binding, "argv": self.argv, "cleanupErrors": [], "termination": [],
                       "groupObservations": self.observations, "childReaped": False, "ownedProcessGroup": None}

    def add_error(self, phase, error):
        self.record["cleanupErrors"].append({"phase": phase, "type": type(error).__name__, "reason": str(error)})

    def observe(self, group):
        self.c.require(self.process is not None and group == self.process.pid and not self.absent,
                       "Only this captured owned group may be observed before positive absence")
        result = self.lifecycle._observe_exited_group(group)
        if result.get("status") == "ABSENT_ESRCH" and result.get("present") is False:
            self.absent = True
        self.observations.append(copy.deepcopy(result))
        return result

    def adapted(self, run):
        boundary = self
        class SubprocessCapture:
            def __getattr__(self, key):
                return getattr(subprocess, key)
            def Popen(self, argv, *args, **kwargs):
                boundary.c.require(boundary.process is None and argv == boundary.argv
                                   and kwargs.get("start_new_session") is True,
                                   "Exactly one original owned process/session may be created")
                process = subprocess.Popen(argv, *args, **kwargs)
                boundary.process = process  # Before any original log/receipt/disk-sample I/O.
                boundary.record.update(pid=process.pid, pgid=process.pid, capturedAt=time.time(),
                                       status="CAPTURED_PENDING_CLOSURE")
                return process
        class LifecycleCapture:
            def _terminate_owned_process(self, process, outcome):
                boundary.c.require(process is boundary.process, "Original cleanup must target the exact captured Popen")
                return boundary.lifecycle._terminate_owned_process(process, outcome)
            def _observe_exited_group(self, group):
                return boundary.observe(group)
        namespace = dict(run.__globals__, subprocess=SubprocessCapture(), LIFECYCLE=LifecycleCapture())
        value = types.FunctionType(run.__code__, namespace, run.__name__, run.__defaults__, run.__closure__)
        value.__kwdefaults__ = run.__kwdefaults__
        self.c.require(value.__code__ is run.__code__ and value.__globals__ is not run.__globals__
                       and run.__globals__["subprocess"] is subprocess,
                       "Runtime adapter must preserve original code and avoid shared-global monkeypatches")
        return value

    def finish(self, original_result, original_error):
        process = self.process
        if process is None:
            self.closed = True
            self.record.update(status="NO_PROCESS_SPAWNED", closureVerified=True)
        else:
            # Never re-observe an already absent historical PGID. The proxy retained
            # positive absence even if a later original receipt/log read raised.
            if not self.absent:
                try:
                    self.lifecycle._terminate_owned_process(process, self.record)
                except BaseException as error:
                    self.add_error("post-exception-original-owned-termination", error)
            try:
                self.record["exitCode"] = process.wait(timeout=1)
                self.record["childReaped"] = True
            except BaseException as error:
                self.add_error("post-exception-original-owned-reap", error)
            if not self.absent:
                try:
                    self.observe(process.pid)
                except BaseException as error:
                    self.add_error("post-exception-original-owned-observation", error)
            self.closed = self.record["childReaped"] is True and self.absent
            self.record.update(status="CLOSED_OWNED_PROCESS_AND_GROUP" if self.closed else "UNRESOLVED_OWNED_PROCESS_CUSTODY",
                               closureVerified=self.closed, ownedProcessGroup="ABSENT_ESRCH" if self.absent else "UNRESOLVED")
        # Capture diagnostic text only after the owned process has crossed the
        # cleanup boundary; formatting a first error cannot bypass that cleanup.
        self.record["originalException"] = None if original_error is None else {
            "type": type(original_error).__name__, "reason": str(original_error)}
        self.record["originalCommandStatus"] = None if original_result is None else original_result[0].get("status")
        return self.record


class OwnedCommands:
    """One registry for every original command in the two new styled lanes."""
    def __init__(self, c, run, out):
        self.c, self.original, self.out = c, run, out
        self.lifecycle, self.binding = original_execution_binding(c, run)
        self.entries, self.errors = [], []
        self.lock = threading.Lock()

    @property
    def closed(self):
        with self.lock:
            return all(row["boundary"].finished and row["boundary"].closed for row in self.entries)

    def record_error(self, label, phase, error):
        self.errors.append({"label": label, "phase": phase, "type": type(error).__name__, "reason": str(error)})

    def run(self, argv, directory, label, **options):
        c = self.c
        c.require(directory == self.out and isinstance(label, str) and re.fullmatch(r"[a-z0-9-]+", label),
                  "Original styled command must retain its exact owned output/label")
        with self.lock:
            c.require(not any((row["boundary"].failure_started and not row["boundary"].finished)
                              or (row["boundary"].finished and not row["boundary"].closed) for row in self.entries),
                      "Further commands withheld while captured process custody is unresolved")
            boundary = OwnedExecutionBoundary(c, self.lifecycle, argv, self.binding)
            entry = {"label": label, "boundary": boundary, "proof": None}
            self.entries.append(entry)
        original_result, first = None, None
        try:
            original_result = boundary.adapted(self.original)(argv, directory, label, **options)
        except BaseException as error:
            first = error
            boundary.failure_started = True
        finally:
            try:
                closure = boundary.finish(original_result, first)
                for row in closure["cleanupErrors"]:
                    self.errors.append(dict(row, label=label))
                if not boundary.closed:
                    self.record_error(label, "unresolved-owned-custody", RuntimeError("Exact captured process/group closure is unresolved"))
            except BaseException as error:
                self.record_error(label, "owned-closure", error)
            try:
                name = "styled-execute-closure.json" if label == "execute" else "styled-owned-" + label + "-closure.json"
                entry["proof"] = exclusive(c, self.out / name, encoded(boundary.record))
            except BaseException as error:
                self.record_error(label, "owned-closure-retention", error)
            boundary.finished = True
        if first is not None:
            raise first
        c.require(original_result is not None, "Original command result is unavailable")
        if original_result[0].get("status") == "PASS":
            c.require(boundary.closed and not any(row["label"] == label for row in self.errors),
                      "Additional owned command closure or retention failed: " + label)
        # Preserve an original failed result supplied with allow_failure=True;
        # later custody errors remain in the registry and cannot yield PASS.
        return original_result

    def proof(self, label):
        rows = [row for row in self.entries if row["label"] == label]
        self.c.require(len(rows) <= 1, "Original command label was reused")
        return rows[0]["proof"] if rows else None

    def final_receipt(self):
        self.c.require(self.c.digest(Path(self.binding["originalRunController"]["path"])) == self.binding["originalRunController"]["sha256"]
                       and self.c.digest(Path(__file__)) == self.binding["runtimeAdapterSHA256"],
                       "Owned command adapter/original controller source changed during execution")
        value = {"schema": "native-styled-owned-commands/v1", "status": "CLOSED_ALL_OWNED_COMMANDS" if self.closed and not self.errors else "FAIL",
                 "binding": self.binding, "closed": self.closed, "errors": self.errors,
                 "commands": [{"label": row["label"], "finished": row["boundary"].finished,
                               "closed": row["boundary"].closed, "closure": row["proof"]} for row in self.entries],
                 "actualXCTestAcceptance": False}
        result = exclusive(self.c, self.out / "styled-owned-commands.json", encoded(value))
        self.c.require(value["status"] == "CLOSED_ALL_OWNED_COMMANDS", "Owned styled command custody or retention failed")
        return result


def runner_reader(c, source):
    """Specialize only the original Anytype-name guard for the actual test host.

    The original app helper must keep rejecting a different executable. This
    separate reader retains all of its Mach-O, declaration, alias and digest
    rules while requiring the descriptor-selected runner executable instead.
    """
    path = source / "Tools/PinkhaSimulatorGate/run_ui27.py"
    raw = c.raw(path, 128 * 1024)
    c.require(c.sha(raw) == "87e0972ee6852d1fdb34d82afa5dde346baf836afaa8419203b647e7d3e21ca7",
              "Exact original executable carrier reader file required")
    text = raw.decode()
    nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == "code_carriers"]
    c.require(len(nodes) == 1, "One original carrier reader required")
    original = ast.get_source_segment(text, nodes[0])
    c.require(c.sha(original.encode()) == "9173ba8198b3ae2a47ecb8f9be33cc2d015f31fe0a5315fb7d88c0cdf1225fcb",
              "Exact original executable carrier reader body required")
    before = ("def code_carriers(bundle):", "if info.get('CFBundleExecutable') != 'Anytype':")
    after = ("def code_carriers(bundle, expected_executable):", "if info.get('CFBundleExecutable') != expected_executable:")
    candidate = original
    for old, new in zip(before, after):
        c.require(candidate.count(old) == 1, "Exact runner executable guard specialization required")
        candidate = candidate.replace(old, new)
    inverse = candidate
    for old, new in reversed(list(zip(before, after))):
        inverse = inverse.replace(new, old)
    c.require(inverse == original, "Every original carrier-reader byte must be recoverable")
    namespace = {"Path": Path, "plistlib": plistlib, "digest": c.digest, "json": json, "hashlib": hashlib}
    exec(compile(candidate, str(path) + "[descriptor-runner-guard]", "exec"), namespace)
    return namespace["code_carriers"], {"originalFileSHA256": c.sha(raw), "originalFunctionSHA256": c.sha(original.encode()),
            "runnerFunctionSHA256": c.sha(candidate.encode()), "inverseRestoresEveryOriginalByte": True,
            "onlyChange": "Expected root executable derives from admitted TestHostPath/Info.plist; app helper is unchanged"}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def exclusive(c, path, raw):
    c.require(path.is_absolute() and path.parent.resolve() == path.parent and path.parent.is_dir(),
              "Canonical existing private output parent required")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "sha256": c.sha(raw), "bytes": len(raw)}


def regular(c, path, limit):
    """Read bounded runner bytes without following aliases or racing replacement."""
    c.require(path.is_absolute() and path.resolve() == path and not path.is_symlink(),
              "Canonical private runner file required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        c.require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid() and before.st_nlink == 1
                  and stat.S_IMODE(before.st_mode) & 0o077 == 0 and 0 < before.st_size <= limit,
                  "Private regular bounded runner file required")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        c.require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                  == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                  and len(raw) == before.st_size and path.stat(follow_symlinks=False).st_ino == before.st_ino,
                  "Runner file changed during retained read")
    return raw


def private_directory(c, path):
    c.require(path.is_absolute() and path.resolve() == path and not path.is_symlink() and path.is_dir(),
              "Canonical owned runner rendezvous required")
    info = path.stat()
    c.require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) & 0o077 == 0,
              "Runner rendezvous must remain private")


def pin(c, path, limit=2 * 1024**2):
    raw = c.raw(path, limit)
    return {"path": str(path), "sha256": c.sha(raw), "bytes": len(raw)}


def command_pins(c, out, label):
    return {key: pin(c, out / (label + suffix)) for key, suffix in (
        ("command", ".command.json"), ("result", ".result.json"),
        ("processExit", ".process-exit.json"), ("log", ".log"))}


def context(c, configuration, out, udid, source, stage):
    c.require(stage in STAGES and re.fullmatch(r"[0-9a-f]{40}", source),
              "Exact admitted styled source and method required")
    observed = out / "rtl-before-environment.json"
    value = c.decode(c.raw(observed, 16384))
    language = "en" if configuration["appLanguage"] == "he" else "he"
    c.require(value["ownedUDID"] == udid
              and value["language"]["app_language"] == configuration["appLanguage"]
              and value["language"]["device_language"] == language
              and value["presentation"]["appearance"] == configuration["appearance"]
              and value["presentation"]["content_size"] == "large",
              "Actual original language/appearance/size readbacks must precede invocation")
    result = {"schema": "native-accessibility-invocation/v1", "runID": str(uuid.uuid4()).upper(),
              "appSourceCommit": source, "uiSourceCommit": source, "simulatorUDID": udid,
              "ownedScope": str(uuid.uuid4()).upper(), "method": STAGES[stage][0].split("/")[1],
              "appLanguage": configuration["appLanguage"], "osLanguage": language,
              "contentSize": "large", "appearance": configuration["appearance"],
              "deviceFamily": configuration["deviceFamily"], "settingsReadbackSHA256": c.digest(observed)}
    c.require(set(result) == CONTEXT_KEYS and all(isinstance(x, str) for x in result.values()),
              "Exact original thirteen-string invocation required")
    exclusive(c, out / "styled-invocation.json", encoded(result))
    return result


def bind(c, original, invocation, stage, out, products, helpers):
    c.require(stage in STAGES and set(original) == {TARGET, "__xctestrun_metadata__"},
              "Original single-target styled descriptor required")
    target = original[TARGET]
    c.require(target["OnlyTestIdentifiers"] == [STAGES[stage][0]]
              and target["EnvironmentVariables"].get("PINKHA_NATIVE_UI_UNIFIED_HOST") == "1"
              and target["EnvironmentVariables"].get("PINKHA_SIMULATOR_UI_DISPOSABLE") == "1",
              "Original source-qualified owned NativeUI descriptor required")
    for key in ENVIRONMENT:
        c.require(key not in os.environ and "TEST_RUNNER_" + key not in os.environ
                  and all(key not in target.get(group, {}) and "TEST_RUNNER_" + key not in target.get(group, {})
                          for group in ("EnvironmentVariables", "TestingEnvironmentVariables", "UITargetAppEnvironmentVariables")),
                  "Ambient or prebound styled invocation overrides are forbidden")
    raw = c.raw(out / "styled-invocation.json", 16384)
    c.require(c.decode(raw) == invocation, "Actual retained invocation changed")
    additions = dict(zip(ENVIRONMENT, (raw.decode(), c.sha(raw))))
    value = copy.deepcopy(original)
    value[TARGET]["EnvironmentVariables"].update(additions)
    inverse = copy.deepcopy(value)
    for key in additions:
        del inverse[TARGET]["EnvironmentVariables"][key]
    c.require(inverse == original, "Only the two exact original invocation variables may be added")
    host = Path(target["TestHostPath"])
    candidates = [path for path in (host, *host.parents) if path.suffix == ".app"]
    c.require(len(candidates) == 1, "One actual descriptor-selected runner application required")
    app = candidates[0]
    c.require(app.is_absolute() and app.resolve() == app and app.is_relative_to(products)
              and app.is_dir() and host.resolve().is_relative_to(app),
              "Runner executable must remain in the admitted original copied products")
    info = plistlib.loads(c.raw(app / "Info.plist", 1024**2))
    bundle = info.get("CFBundleIdentifier")
    executable = info.get("CFBundleExecutable")
    c.require(isinstance(bundle, str) and re.fullmatch(r"[A-Za-z0-9.-]+", bundle)
              and isinstance(executable, str) and Path(executable).name == executable
              and (app / executable).is_file() and host in (app, app / executable),
              "Actual original XCTest runner bundle/executable identity required")
    runner = {"bundleIdentifier": bundle, "builtApplication": str(app), "builtExecutable": executable,
              "builtCodeCarriersSHA256": helpers["runner_code_carriers"](app, executable)["sha256"]}
    proof = {"environmentKeys": list(ENVIRONMENT), "invocationSHA256": c.sha(raw),
             "selector": TARGET + "/" + STAGES[stage][0], "methodBudgetSeconds": STAGES[stage][1],
             "inverseRestoresOriginalBoundDescriptor": True, "runner": runner}
    return value, proof, {"TEST_RUNNER_" + key: val for key, val in additions.items()}, runner


def native_identity(c, value):
    c.require(value.get("schema") == "any-semantic-anchor-native-rendered/v1"
              and value.get("state") == "MATCHED" and value.get("mode") == "read-only"
              and value.get("nativeReadOrigin") == "AnyDocumentPresentation.read"
              and all(type(value.get(key)) is int and value[key] == 0 for key in
                      ("engineCalls", "mutations", "selectionChanges", "nativeMarkCount", "renderedMarkCount"))
              and type(value.get("pid")) is int and value["pid"] > 0,
              "Actual original read-only matched native observation required")
    keys = ("spaceSHA256", "objectSHA256", "nativeVersionSHA256")
    c.require(all(re.fullmatch(r"[0-9a-f]{64}", value.get(key, "")) for key in keys)
              and str(uuid.UUID(value["generation"])).upper() == value["generation"].upper()
              and isinstance(value.get("blocks"), list) and len(value["blocks"]) == 3,
              "Exact original live fixture identity and three mounted blocks required")
    blocks = []
    for block in value["blocks"]:
        c.require(all(re.fullmatch(r"[0-9a-f]{64}", block.get(key, "")) for key in
                      ("blockSHA256", "sourceSHA256", "textSHA256"))
                  and block.get("nativeMarks") == block.get("renderedMarks") == []
                  and block.get("isFirstResponder") is False
                  and type(block.get("selectionLocation")) is int and block["selectionLocation"] >= 0
                  and type(block.get("selectionLength")) is int and block["selectionLength"] >= 0,
                  "Actual unchanged native identity and inactive selection required")
        presentation = block["textPresentation"]
        c.require(presentation.get("schema") == "native-mounted-text-presentation/v1"
                  and presentation.get("assignedUIFontOnly") is True
                  and presentation.get("fontReadOrigin") == "mounted-UITextView-attributedText-and-typingAttributes"
                  and presentation.get("nativeReadOrigin") == "AnyDocumentPresentation.read.snapshot.blocks",
                  "Actual mounted UIKit presentation origin required")
        blocks.append({key: block[key] for key in ("blockSHA256", "sourceSHA256", "textSHA256", "utf16Length",
                       "selectionLocation", "selectionLength", "isFirstResponder")}
                      | {"nativeType": presentation["nativeType"], "nativeStyleJSON": presentation["nativeStyleJSON"]})
    c.require(len({row["blockSHA256"] for row in blocks}) == 3, "Distinct actual live fixture blocks required")
    return {key: value[key] for key in ("pid", *keys, "generation")} | {"blocks": blocks}


class LiveSession:
    def __init__(self, c, helpers, run, out, udid, invocation, runner):
        self.c, self.helpers, self.run = c, helpers, run
        self.out, self.udid, self.invocation = out, udid, invocation
        self.commands = getattr(run, "__self__", None)
        c.require(isinstance(self.commands, OwnedCommands) and self.commands.out == out and self.commands.c is c,
                  "Both styled journeys must use the one source-qualified owned command registry")
        self.live = invocation["method"] == STAGES["styled-live-type"][0].split("/")[1]
        c.require(self.live or invocation["method"] == STAGES["styled-blocks"][0].split("/")[1],
                  "Only the two original styled methods are supported")
        self.runner = dict(runner)
        self.private = out / "private-styled-rendezvous"
        c.require(not self.private.exists() and not self.private.is_symlink(), "Fresh private coordination custody required")
        self.private.mkdir(mode=0o700)
        self.errors, self.requests = [], []
        self.native = self.runner_pid = None
        self.may_have_changed = False
        self.finalized = False
        # Python return and positive owned-process closure are separate facts.
        self.worker_returned = threading.Event()
        self.worker_result = self.worker_error = None

    @property
    def process_closed(self):
        return self.commands.closed

    @property
    def execution_closure_pin(self):
        return self.commands.proof("execute")

    def error(self, phase, error):
        self.errors.append({"phase": phase, "type": type(error).__name__, "reason": str(error)})

    def runner_directory(self):
        c, out, udid = self.c, self.out, self.udid
        owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
        deadline = time.monotonic() + 120
        for attempt in range(60):
            if self.worker_returned.is_set() or time.monotonic() >= deadline:
                break
            record, raw = self.run(["xcrun", "simctl", "get_app_container", udid,
                                   self.runner["bundleIdentifier"], "app"], out,
                                  "styled-runner-app-%02d" % attempt, timeout=5, allow_failure=True)
            c.require(record.get("stopped") is None and record.get("ownedProcessGroup") == "ABSENT_ESRCH"
                      and not record.get("cleanupErrors"), "Runner lookup ownership/termination failed")
            if record["status"] != "PASS":
                self.worker_returned.wait(1)
                continue
            c.require(len(raw) <= 4096, "Bounded actual runner application path required")
            app = Path(raw.decode().strip())
            c.require(app.is_absolute() and app.resolve() == app and app.is_dir() and app.is_relative_to(owner),
                      "Installed XCTest runner escaped the actual owned simulator")
            info = plistlib.loads(c.raw(app / "Info.plist", 1024**2))
            actual = self.helpers["runner_code_carriers"](app, self.runner["builtExecutable"])
            c.require(info["CFBundleIdentifier"] == self.runner["bundleIdentifier"]
                      and actual["sha256"] == self.runner["builtCodeCarriersSHA256"],
                      "Installed XCTest code differs from admitted original runner")
            _, raw = self.run(["xcrun", "simctl", "get_app_container", udid,
                               self.runner["bundleIdentifier"], "data"], out, "styled-runner-data", timeout=10)
            c.require(len(raw) <= 4096, "Bounded actual runner data path required")
            data = Path(raw.decode().strip())
            c.require(data.is_absolute() and data.resolve() == data and data.is_dir() and data.is_relative_to(owner),
                      "Actual XCTest data container escaped its owned simulator")
            self.runner.update(installedApplication=str(app), installedCodeCarriersSHA256=actual["sha256"],
                               dataContainer=str(data), installedLookupCommand="styled-runner-app-%02d" % attempt)
            return data / "Library/Application Support/PinkhaNativeTypographyAcceptance" / self.invocation["ownedScope"]
        raise RuntimeError("Actual admitted XCTest runner was not observed within its finite lookup budget")

    def request(self, directory, phase, size):
        c = self.c
        private_directory(c, directory)
        source = directory / (phase + "-request.json")
        raw = regular(c, source, 65536)
        retained = exclusive(c, self.private / source.name, raw)  # Preserve even malformed bounded bytes first.
        row = {"phase": phase, "contentSize": size, "request": retained}
        self.requests.append(row)
        value = c.decode(raw)
        keys = {"schema", "phase", "requestNonce", "invocation", "requestedContentSize", "runnerProcessID",
                "runnerBundleID", "appPIDFromOriginalObserver", "nativeObservationJSON", "nativeObservationSHA256"}
        c.require(isinstance(value, dict) and set(value) == keys
                  and value["schema"] == "native-typography-live-request/v1" and value["phase"] == phase
                  and value["invocation"] == self.invocation and value["requestedContentSize"] == size
                  and value["runnerBundleID"] == self.runner["bundleIdentifier"]
                  and type(value["runnerProcessID"]) is int and value["runnerProcessID"] > 0
                  and type(value["appPIDFromOriginalObserver"]) is int and value["appPIDFromOriginalObserver"] > 0,
                  "Exact scoped request from the admitted XCTest runner required")
        c.require(str(uuid.UUID(value["requestNonce"])).upper() == value["requestNonce"].upper()
                  and all(item.get("requestNonce") != value["requestNonce"] for item in self.requests[:-1]),
                  "Fresh unique original runner request nonce required")
        native_raw = value["nativeObservationJSON"].encode()
        c.require(0 < len(native_raw) <= 24576 and c.sha(native_raw) == value["nativeObservationSHA256"],
                  "Exact bounded original native observation bytes required")
        native = native_identity(c, c.decode(native_raw))
        c.require(native["pid"] == value["appPIDFromOriginalObserver"], "Original App PID witness differs")
        if self.native is None:
            self.native, self.runner_pid = native, value["runnerProcessID"]
        else:
            c.require(native == self.native and value["runnerProcessID"] == self.runner_pid,
                      "Live size request changed App/runner/native identity or selection")
        row.update(requestNonce=value["requestNonce"], runnerProcessID=value["runnerProcessID"],
                   appPIDFromOriginalObserver=value["appPIDFromOriginalObserver"],
                   nativeObservationSHA256=value["nativeObservationSHA256"])
        destination = directory / (phase + "-response.json")
        c.require(not destination.exists() and not destination.is_symlink(), "Response must not overwrite runner bytes")
        c.require(not self.worker_returned.is_set(), "Original XCTest execution already returned")
        self.may_have_changed = True  # A failed setter may still have changed the owned preference.
        label = "styled-" + phase
        self.run(["xcrun", "simctl", "ui", self.udid, "content_size", size], self.out, label + "-set", timeout=15)
        row["set"] = command_pins(c, self.out, label + "-set")
        _, readback_raw = self.run(["xcrun", "simctl", "ui", self.udid, "content_size"],
                                   self.out, label + "-read", timeout=15)
        c.require(0 < len(readback_raw) <= 4096, "Bounded actual simulator size readback required")
        readback = readback_raw.decode()
        c.require(self.helpers["actual_setting"](readback, size, "content_size") == size,
                  "Actual requested owned simulator size was not read back")
        row.update(read=command_pins(c, self.out, label + "-read"), readback=readback,
                   readbackSHA256=c.sha(readback_raw))
        response = {"schema": "native-typography-live-response/v1", "phase": phase,
                    "requestNonce": value["requestNonce"], "requestSHA256": c.sha(raw),
                    "simulatorUDID": self.udid, "contentSize": size, "readback": readback,
                    "readbackSHA256": c.sha(readback_raw), "status": "APPLIED_AND_READ_BACK"}
        response_raw = encoded(response)
        row["response"] = exclusive(c, self.private / destination.name, response_raw)
        private_directory(c, directory)
        c.require(not self.worker_returned.is_set(), "Original XCTest returned before response delivery")
        temporary = directory / (value["requestNonce"] + ".controller-response.tmp")
        exclusive(c, temporary, response_raw)
        try:
            os.link(temporary, destination, follow_symlinks=False)  # Atomic, exclusive, never replaces another file.
        finally:
            temporary.unlink()
        row["responsePublished"] = True

    def execute(self, argv, timeout, environment):
        def original_execution():
            try:
                self.worker_result = self.run(argv, self.out, "execute", timeout=timeout,
                                              environment=environment, allow_failure=True)
            except BaseException as error:
                self.worker_error = error
            finally:
                self.worker_returned.set()
        worker = threading.Thread(target=original_execution, name="owned-original-NativeUI-execute")
        worker.start()
        try:
            directory = self.runner_directory()
            for phase, size in PHASES if self.live else ():
                path = directory / (phase + "-request.json")
                while not path.exists() and not path.is_symlink() and not self.worker_returned.wait(0.2):
                    pass  # The original run function owns the finite XCTest process/deadline.
                if self.worker_returned.is_set():
                    raise RuntimeError("Original XCTest ended before both live-size requests completed")
                self.request(directory, phase, size)
        except BaseException as error:
            self.error("live-rendezvous", error)
        finally:
            # Never detach the original owned process or substitute a service error
            # for its actual exception/result. Its existing timeout still applies.
            while not self.worker_returned.wait(0.2):
                pass
            worker.join()
        if self.worker_error is not None:
            raise self.worker_error
        self.c.require(self.worker_result is not None, "Original owned execution result is missing")
        return self.worker_result

    def finish(self):
        c = self.c
        c.require(not self.finalized, "Live-size finalization must run exactly once")
        self.finalized = True
        if not self.live:
            self.c.require(self.process_closed and not self.errors, "Catalog owned execution or runner custody failed")
            return {"schema": "native-styled-catalog-execution/v1", "ownedExecutionClosure": self.execution_closure_pin,
                    "ownedExecutionClosed": True, "runner": self.runner, "actualXCTestAcceptance": False}
        restored = {"attempted": False, "target": "large"}
        if not self.process_closed:
            restored["withheldReason"] = "UNRESOLVED_OWNED_EXECUTION_CUSTODY"
            self.error("finally-restore-withheld", RuntimeError("No settings or shutdown action is authorized before positive owned closure"))
        elif self.may_have_changed:
            restored["attempted"] = True
            try:
                self.run(["xcrun", "simctl", "ui", self.udid, "content_size", "large"], self.out,
                         "styled-final-restore-set", timeout=15, cleanup=True)
                restored["set"] = command_pins(c, self.out, "styled-final-restore-set")
            except BaseException as error:
                self.error("finally-restore-set", error)
            try:
                _, raw = self.run(["xcrun", "simctl", "ui", self.udid, "content_size"], self.out,
                                  "styled-final-restore-read", timeout=15, cleanup=True)
                c.require(0 < len(raw) <= 4096, "Bounded final content-size readback required")
                actual = self.helpers["actual_setting"](raw.decode(), "large", "content_size")
                c.require(actual == "large", "Original owned size was not restored")
                restored.update(read=command_pins(c, self.out, "styled-final-restore-read"), actual=actual,
                                readback=raw.decode(), readbackSHA256=c.sha(raw))
            except BaseException as error:
                self.error("finally-restore-read", error)
        execute = {}
        for key, suffix in (("command", ".command.json"), ("result", ".result.json"), ("processExit", ".process-exit.json")):
            try:
                path = self.out / ("execute" + suffix)
                execute[key] = pin(c, path) if path.exists() else None
            except BaseException as error:
                self.error("retain-original-execute-" + key, error)
                execute[key] = None
        if not (len(self.requests) == 2 and all(row.get("responsePublished") is True for row in self.requests)):
            self.error("finite-request-completion", RuntimeError("Both original requests were not completed"))
        value = {"schema": CONTROL_SCHEMA, "stage": "styled-live-type", "status": "FAIL" if self.errors else CONTROL_PASS,
                 "invocationSHA256": c.sha(c.raw(self.out / "styled-invocation.json", 16384)),
                 "ownedUDID": self.udid, "sourceCommit": self.invocation["appSourceCommit"],
                 "initialContentSize": "large", "runner": dict(self.runner, processIDFromRequest=self.runner_pid),
                 "execute": execute, "requests": self.requests, "finalRestore": restored, "errors": self.errors,
                 "actualXCTestAcceptance": False, "visualReview": "PENDING", "nativeCalls": 0,
                 "mutationScope": "owned simulator content_size only"}
        exclusive(c, self.out / "styled-live-control.json", encoded(value))
        c.require(not self.errors and restored.get("actual") == "large", "Live-size coordination or final restoration failed")
        return value
