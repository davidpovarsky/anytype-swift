#!/usr/bin/env python3
"""Portable failure-boundary controls only; no Apple/native/runtime acceptance."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import sys
import tempfile
import time
import types
import unittest
from unittest import mock
import uuid

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent


def load(name):
    path = ROOT / name
    spec = importlib.util.spec_from_file_location(name.replace(".", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Core:
    @staticmethod
    def require(value, reason):
        if not value:
            raise RuntimeError(reason)

    @staticmethod
    def sha(raw):
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def raw(path, limit=8 * 1024**2):
        raw = Path(path).read_bytes()
        Core.require(len(raw) <= limit, "synthetic fixture bound")
        return raw

    @staticmethod
    def digest(path):
        return Core.sha(Path(path).read_bytes())

    @staticmethod
    def decode(raw):
        return json.loads(raw)


R = load("native_styled_runtime.py")


def invocation():
    return {"schema": "native-accessibility-invocation/v1", "runID": str(uuid.uuid4()).upper(),
            "appSourceCommit": "a" * 40, "uiSourceCommit": "a" * 40,
            "simulatorUDID": str(uuid.uuid4()).upper(), "ownedScope": str(uuid.uuid4()).upper(),
            "method": R.STAGES["styled-live-type"][0].split("/")[1], "appLanguage": "he",
            "osLanguage": "en", "contentSize": "large", "appearance": "dark", "deviceFamily": "ipad",
            "settingsReadbackSHA256": "f" * 64}


def native():
    value = {"schema": "any-semantic-anchor-native-rendered/v1", "state": "MATCHED", "mode": "read-only",
             "nativeReadOrigin": "AnyDocumentPresentation.read", "engineCalls": 0, "mutations": 0,
             "selectionChanges": 0, "nativeMarkCount": 0, "renderedMarkCount": 0, "pid": 111,
             "spaceSHA256": "1" * 64, "objectSHA256": "2" * 64, "nativeVersionSHA256": "3" * 64,
             "generation": str(uuid.uuid4()).upper(), "blocks": []}
    for index in range(3):
        value["blocks"].append({"blockSHA256": str(index + 4) * 64, "sourceSHA256": "8" * 64,
            "textSHA256": "8" * 64, "utf16Length": 0, "nativeMarks": [], "renderedMarks": [],
            "isFirstResponder": False, "selectionLocation": 0, "selectionLength": 0,
            "textPresentation": {"schema": "native-mounted-text-presentation/v1", "assignedUIFontOnly": True,
                "fontReadOrigin": "mounted-UITextView-attributedText-and-typingAttributes",
                "nativeReadOrigin": "AnyDocumentPresentation.read.snapshot.blocks",
                "nativeType": "paragraph", "nativeStyleJSON": "{}"}})
    return value


class SyntheticRun:
    """Retained synthetic ledgers, explicitly not subprocess or device results."""
    def __init__(self, fail_expanded=False):
        self.calls = []
        self.fail_expanded = fail_expanded
        self.size = "large"

    def __call__(self, argv, out, label, **kwargs):
        self.calls.append((label, argv, kwargs))
        failed = self.fail_expanded and label == "styled-expanded-set"
        if len(argv) == 6:
            self.size = argv[-1]
        raw = (self.size + "\n").encode() if len(argv) == 5 else b""
        command = {"argv": argv, "pid": 222, "pgid": 222, "started": time.time(), "syntheticControlOnly": True}
        record = dict(command, status="FAIL" if failed else "PASS", exitCode=1 if failed else 0,
                      stopped=None, ownedProcessGroup="ABSENT_ESRCH", cleanupErrors=[], termination=[], logSHA256=Core.sha(raw))
        for suffix, value in ((".command.json", command), (".process-exit.json", record), (".result.json", record)):
            (out / (label + suffix)).write_bytes(R.encoded(value))
        (out / (label + ".log")).write_bytes(raw)
        if failed:
            raise RuntimeError("synthetic setter failed after possible application")
        return record, raw


class Controls(unittest.TestCase):
    def session(self, root, command=None):
        ctx = invocation()
        R.exclusive(Core, root / "styled-invocation.json", R.encoded(ctx))
        run = command or SyntheticRun()
        helpers = {"actual_setting": lambda raw, expected, label: raw.strip()}
        session = R.LiveSession(Core, helpers, run, root, ctx["simulatorUDID"], ctx,
            {"bundleIdentifier": "synthetic.tests.runner", "builtApplication": str(root / "Synthetic.app"),
             "builtExecutable": "Synthetic", "builtCodeCarriersSHA256": "9" * 64})
        directory = root / "runner-rendezvous"
        directory.mkdir(mode=0o700)
        return session, directory

    def write_request(self, session, directory, phase="expanded", size="accessibility-extra-extra-extra-large", *, scope=None, observed=None):
        raw_native = R.encoded(observed or native())
        context = dict(session.invocation)
        if scope is not None:
            context["ownedScope"] = scope
        value = {"schema": "native-typography-live-request/v1", "phase": phase, "requestNonce": str(uuid.uuid4()).upper(),
                 "invocation": context, "requestedContentSize": size, "runnerProcessID": 222,
                 "runnerBundleID": "synthetic.tests.runner", "appPIDFromOriginalObserver": 111,
                 "nativeObservationJSON": raw_native.decode(), "nativeObservationSHA256": Core.sha(raw_native)}
        raw = R.encoded(value)
        R.exclusive(Core, directory / (phase + "-request.json"), raw)
        return raw

    def test_closed_profile_refuses_before_any_input_read_or_output(self):
        profile = load("native16_profile_closed.py")
        self.assertIs(profile.READY_FOR_EXECUTION, False)
        self.assertEqual((profile.FUTURE_SOURCE_COMMIT, profile.FUTURE_SHARED_CONTROLLER_SHA256,
                          profile.FUTURE_CANONICAL_ADMISSION_SHA256), (None, None, None))
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("unexpected input read")), \
             mock.patch.object(Path, "mkdir", side_effect=AssertionError("unexpected output")):
            with self.assertRaisesRegex(RuntimeError, "CLOSED_STYLED_FUTURE_PRODUCT"):
                profile.configure(types.SimpleNamespace())
        self.assertIsNone(profile._state)

    def test_foreign_scope_and_malformed_request_are_retained_before_no_mutation(self):
        for label in ("foreign-scope", "malformed-json"):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                session, directory = self.session(root)
                if label == "foreign-scope":
                    original = self.write_request(session, directory, scope=str(uuid.uuid4()).upper())
                else:
                    original = b'{"schema": broken'
                    R.exclusive(Core, directory / "expanded-request.json", original)
                with self.assertRaises(Exception):
                    session.request(directory, *R.PHASES[0])
                self.assertEqual((session.private / "expanded-request.json").read_bytes(), original)
                self.assertEqual(session.run.calls, [])
                self.assertFalse(session.may_have_changed)
                self.assertFalse((directory / "expanded-response.json").exists())

    def test_possible_failed_write_still_restores_and_retains_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            session, directory = self.session(root, SyntheticRun(fail_expanded=True))
            self.write_request(session, directory)
            try:
                session.request(directory, *R.PHASES[0])
            except RuntimeError as error:
                session.error("live-rendezvous", error)
            else:
                self.fail("failed setter was accepted")
            self.assertTrue(session.may_have_changed)
            with self.assertRaisesRegex(RuntimeError, "coordination or final restoration failed"):
                session.finish()
            result = Core.decode((root / "styled-live-control.json").read_bytes())
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual([row[0] for row in session.run.calls],
                             ["styled-expanded-set", "styled-final-restore-set", "styled-final-restore-read"])
            self.assertTrue(result["finalRestore"]["attempted"])
            self.assertEqual(result["finalRestore"]["actual"], "large")
            self.assertIn("synthetic setter failed", result["errors"][0]["reason"])
            self.assertFalse((directory / "expanded-response.json").exists())

    def test_original_execution_exception_remains_primary_after_service_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            first = RuntimeError("original execution failure sentinel")
            def fail(*args, **kwargs):
                raise first
            session, _ = self.session(root, fail)
            def service_failure():
                raise ValueError("secondary runner lookup failure")
            session.runner_directory = service_failure
            with self.assertRaises(RuntimeError) as caught:
                session.execute(["synthetic-no-process"], 1, {})
            self.assertIs(caught.exception, first)
            self.assertTrue(session.worker_finished.is_set())
            self.assertEqual(session.errors[0]["reason"], "secondary runner lookup failure")

    def test_original_reader_specialization_retains_root_identity_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / "source"
            target = source / "Tools/PinkhaSimulatorGate/run_ui27.py"
            target.parent.mkdir(parents=True)
            target.write_bytes((ROOT.parent / "native-rtl/run_ui27.py").read_bytes())
            reader, proof = R.runner_reader(Core, source)
            bundle = root / "Synthetic-Runner.app"
            bundle.mkdir()
            (bundle / "Info.plist").write_bytes(plistlib.dumps({"CFBundleExecutable": "Synthetic-Runner"}))
            (bundle / "Synthetic-Runner").write_bytes(bytes.fromhex("cffaedfe") + b"synthetic-control-only")
            self.assertTrue(proof["inverseRestoresEveryOriginalByte"])
            self.assertEqual(list(reader(bundle, "Synthetic-Runner")["manifest"]["carriers"]), ["Synthetic-Runner"])
            with self.assertRaisesRegex(RuntimeError, "Unexpected actual application executable"):
                reader(bundle, "Another-Runner")


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {"schema": "native-styled-portable-control/v1", "status": "PASS" if result.wasSuccessful() else "FAIL",
              "scope": "PORTABLE_SYNTHETIC_AND_REAL_SOURCE_CONTROL_ONLY", "methods": result.testsRun,
              "failures": len(result.failures), "errors": len(result.errors), "elapsedSeconds": time.monotonic() - started,
              "files": {name: Core.digest(ROOT / name) for name in (
                  "native_styled_runtime.py", "native16_profile_closed.py", "validate_styled_preparation.py")},
              "processesDispatched": 0, "AppleBuilds": 0, "simulatorsCreated": 0, "settingsChanged": 0,
              "nativeCalls": 0, "UIAcceptance": "NOT_RUN"}
    output = ROOT / "portable-controls1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(record, sort_keys=True, indent=2) + "\n").encode())
    sys.exit(0 if result.wasSuccessful() else 1)
