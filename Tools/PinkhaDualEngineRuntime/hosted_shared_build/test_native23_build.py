"""Portable controls for the added Native23 boundary; never launch Apple tools."""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.dont_write_bytecode = True
import native23_build as subject

SOURCE = CONTROL = ORIGINAL_RETAINER = None


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Process:
    pid = 427131
    def __init__(self):
        self.waits = []
    def poll(self):
        return 0
    def wait(self, timeout):
        self.waits.append(timeout)
        return 0


class Lifecycle:
    def __init__(self, status="ABSENT_ESRCH"):
        self.status = status
        self.terminations = []
        self.observations = []
    def _terminate_owned_process(self, process, outcome):
        self.terminations.append(process)
    def _observe_exited_group(self, group):
        self.observations.append(group)
        return {"status": self.status, "present": self.status != "ABSENT_ESRCH",
                "observations": [{"status": self.status}]}


class Native23BoundaryControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = subject.contract()
        row = cls.contract["originalLifecycle"]
        cls.lifecycle = subject.original_module(CONTROL / row["path"], row["sha256"], "native23_control_original_lifecycle")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="native23-portable-control-")
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def output(self, name):
        output = self.root / name
        (output / "evidence").mkdir(parents=True)
        return output

    def test_original_projection_and_compiler_argv_are_reused(self):
        output = self.output("projection")
        projection, project, before = subject.projected_source(SOURCE, output, self.contract, self.lifecycle)
        argv, declaration = subject.original_argv(SOURCE, output, project, projection, self.contract)
        proof = json.loads((output / "evidence/projection.json").read_bytes())
        self.assertEqual(proof["exactOriginalProjectProjection"]["selectedObjectInverse"], "EXACT_ORIGINAL_BYTES")
        self.assertEqual((proof["applicationBuildTargets"], proof["targetDependencies"], proof["packageReferences"]), (0, 0, 0))
        self.assertEqual(argv[:2], ["xcodebuild", "build-for-testing"])
        self.assertEqual(argv[argv.index("-project") + 1], str(project))
        self.assertEqual(argv[argv.index("-scheme") + 1], "PinkhaAnyNativeTransitionUI")
        self.assertEqual(argv[argv.index("-destination") + 1], "generic/platform=iOS Simulator")
        self.assertEqual(argv[argv.index("-jobs") + 1], "4")
        self.assertEqual(declaration["source"]["sha256"], self.contract["originalUIBuilder"]["sha256"])
        self.assertEqual(before, self.lifecycle.inventory(output / "source"))
        swift = {name for name, row in before.items() if row["kind"] == "file" and name.endswith(".swift")}
        self.assertEqual(swift, {"UITests/NativeLaunchTests.swift", "UITests/NativeHistoryTests.swift"})
        self.assertEqual(subject.declared_plan()["resourcePolicy"]["phaseTimeoutSeconds"], 1200)
        self.assertFalse(subject.declared_plan()["runtimeAdmission"])

    def compiler_fixture(self, name, *, auxiliary=False, wrong_module=False, extra=False):
        output = self.output(name)
        paths = []
        for relative in self.contract["swiftSources"]:
            destination = output / "source/UITests" / Path(relative).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / relative, destination)
            paths.append(str(destination))
        if extra:
            paths.append(paths[0])
        filelist = output / "derived/Build/Intermediates.noindex/Native.build/Debug-iphonesimulator/PinkhaAnyNativeUITests.build/Objects-normal/arm64/Native.SwiftFileList"
        filelist.parent.mkdir(parents=True)
        filelist.write_text("\n".join(paths) + "\n")
        log = output / "evidence" / subject.PHASE / "original.log"
        log.parent.mkdir()
        if auxiliary:
            text = "WriteAuxiliaryFile " + str(filelist) + "\n"
        else:
            module = "WrongModule" if wrong_module else subject.TARGET
            text = "builtin-SwiftDriver -- /Synthetic/Xcode/usr/bin/swiftc -module-name " + module + " @" + str(filelist) + "\n"
        log.write_text(text)
        return output, {"logSHA256": subject.sha(log), "logBytes": log.stat().st_size}

    def test_real_command_witness_requires_exact_two_source_target(self):
        output, phase = self.compiler_fixture("exact")
        proof = subject.compiler_proof(SOURCE, output, self.contract, phase, self.lifecycle)
        self.assertEqual(len(proof["compiledSources"]), 2)
        self.assertEqual(len(proof["declaredLaunchMethods"]), 23)
        self.assertEqual(len(proof["declaredHistoryMethods"]), 1)
        self.assertEqual(len(proof["actualCompilerFileLists"]), 1)
        self.assertFalse(proof["compiledMethodEnumerationExecuted"])
        for name, options in (("auxiliary", {"auxiliary": True}), ("module", {"wrong_module": True}),
                              ("duplicate", {"extra": True})):
            with self.subTest(name=name):
                output, phase = self.compiler_fixture(name, **options)
                with self.assertRaises(ValueError):
                    subject.compiler_proof(SOURCE, output, self.contract, phase, self.lifecycle)
                self.assertFalse((output / "evidence/compiler-inputs.json").exists())

    def custody(self, status="ABSENT_ESRCH"):
        original = Lifecycle(status)
        facade = SimpleNamespace(Commands=lambda directory, source: original)
        custody = subject.PhaseCustody(facade, self.root / "custody", self.root)
        return original, custody

    def test_original_supervisor_write_failure_drains_only_its_actual_child(self):
        output = self.output("phase")
        original, custody = self.custody()
        owner = SimpleNamespace(DEVELOPER="/Synthetic/Developer")
        worker = subject.supervisor(owner, CONTROL, SOURCE, self.root, output,
                                    {"appSourceSHA": "a" * 40}, self.contract, self.lifecycle, custody, {})
        row = json.loads((output / "evidence/original-supervisor-declarations.json").read_bytes())
        self.assertEqual(row["source"]["sha256"], self.contract["originalSupervisor"]["sha256"])
        self.assertEqual({x["name"] for x in row["declarations"]}, {"write", "sha", "git", "source_state", "run_phase"})
        first = OSError("controlled-original-command-receipt-failure")
        worker["write"] = mock.Mock(side_effect=first)
        worker["shutil"] = SimpleNamespace(disk_usage=lambda _: SimpleNamespace(free=10 * 1024**3))
        process = Process()
        with mock.patch.object(subject.subprocess, "Popen", return_value=process) as popen:
            with self.assertRaises(OSError) as captured:
                worker["run_phase"](subject.PHASE, ["CONTROL_ONLY_NOT_XCODE"], 1200)
        self.assertIs(captured.exception, first)
        self.assertIs(custody.process, process)
        self.assertEqual(popen.call_count, 1)
        record = {"status": "FAIL_OR_NOT_RUN"}
        returned = subject.finish_record(custody, record, output / "evidence", first)
        self.assertIs(returned, first)
        self.assertEqual(original.terminations, [process])
        self.assertEqual(process.waits, [1])
        self.assertEqual(original.observations, [process.pid])
        self.assertEqual(record["ownedCompilerCustody"]["status"], "ABSENT_ESRCH")
        self.assertEqual(record["firstFailure"]["message"], str(first))
        custody.finish()
        self.assertEqual(original.observations, [process.pid], "A positively absent historical PGID must not be probed again")

    def test_unresolved_group_blocks_commands_and_absence_is_latched(self):
        original, custody = self.custody("EPERM")
        process = Process()
        custody.process = process
        self.assertEqual(custody.finish()["status"], "UNRESOLVED")
        with mock.patch.object(subject.subprocess, "run") as command:
            with self.assertRaises(ValueError):
                custody.readonly_run(["git", "status"])
            command.assert_not_called()
        original.status = "ABSENT_ESRCH"
        custody._observe_exited_group(process.pid)
        count = len(original.observations)
        custody._observe_exited_group(process.pid)
        custody.finish()
        self.assertEqual(len(original.observations), count)

    def test_first_failure_survives_cleanup_and_receipt_errors(self):
        output = self.output("first-failure")
        first = RuntimeError("original-compiler-error")
        cleanup = SimpleNamespace(finish=mock.Mock(side_effect=RuntimeError("cleanup-error")))
        record = {"status": "FAIL_OR_NOT_RUN"}
        with mock.patch.object(subject, "write", side_effect=OSError("receipt-disk-full")):
            self.assertIs(subject.finish_record(cleanup, record, output / "evidence", first), first)
        self.assertEqual(record["firstFailure"]["message"], "original-compiler-error")
        self.assertEqual(len(first.__notes__), 2)
        path = output / "evidence/receipt.json"
        path.write_bytes(b"ORIGINAL_EXISTING_RESULT\n")
        absent = SimpleNamespace(finish=lambda: {"status": "NOT_SPAWNED", "cleanupErrors": []})
        other = RuntimeError("separate-original-failure")
        self.assertIs(subject.finish_record(absent, {}, output / "evidence", other), other)
        self.assertEqual(path.read_bytes(), b"ORIGINAL_EXISTING_RESULT\n")
        self.assertEqual(len(other.__notes__), 1)

    def roots_from_source(self, path, root, source):
        text = path.read_text()
        main = next(node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == "main")
        start = next(i for i, node in enumerate(main.body) if isinstance(node, ast.Assign)
                     and any(isinstance(x, ast.Name) and x.id == "roots" for x in node.targets))
        nodes = [main.body[start]]
        for node in main.body[start + 1:]:
            if not isinstance(node, ast.For):
                break
            nodes.append(node)
        namespace = {"source": source, "root": root}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
        return namespace["roots"]

    def test_retention_adds_only_native23_originals_and_products(self):
        native = load(CONTROL / "Tools/PinkhaDualEngineRuntime/hosted_shared_build/native_inputs.py", "native_inputs")
        retainer = load(Path(__file__).with_name("retain.py"), "native23_control_retainer")
        source, root = self.root / "source", self.root / "build"
        source.mkdir(); root.mkdir()
        original = self.roots_from_source(ORIGINAL_RETAINER, root, source)
        actual = self.roots_from_source(Path(__file__).with_name("retain.py"), root, source)
        self.assertTrue(set(original).issubset(actual))
        self.assertEqual({k: actual[k] for k in original}, original)
        added = set(actual) - set(original)
        self.assertEqual(added, {"original-build/native23-ui/" + n for n in
                                ("evidence", "source", "Build.xcresult", "derived/Build/Products")})
        for prefix, directory in actual.items():
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "owned-original").write_bytes(prefix.encode())
        omitted = root / "native23-ui/derived/Build/Intermediates.noindex"
        omitted.mkdir(parents=True)
        (omitted / "must-not-be-retained").write_bytes(b"compiler scratch")
        before = retainer.snapshot(original)
        after = retainer.snapshot(actual)
        self.assertEqual({k: after[k] for k in before}, before)
        self.assertFalse(any("Intermediates.noindex" in key for key in after))
        self.assertTrue(all(any(key == prefix or key.startswith(prefix + "/") for prefix in added)
                            for key in set(after) - set(before)))
        self.assertIsNotNone(native)


def main():
    global SOURCE, CONTROL, ORIGINAL_RETAINER
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-source", type=Path, required=True)
    parser.add_argument("--original-controls", type=Path, required=True)
    parser.add_argument("--original-retainer", type=Path, required=True)
    args = parser.parse_args()
    SOURCE, CONTROL, ORIGINAL_RETAINER = (p.resolve() for p in
                                         (args.original_source, args.original_controls, args.original_retainer))
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Native23BoundaryControls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
