#!/usr/bin/env python3
"""One actual current-controller preload control; no product or old test execution."""
from __future__ import annotations
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

PROTOCOL = "sdk06-preload-order-control-v1"
NAMESPACE = "docs/validation/20261123-sdk06-preload-order"
MANIFEST_REL = NAMESPACE + "/control-inputs.json"
WRAPPER_REL = NAMESPACE + "/run-control.py"
ENTRY_MODULE = "sdk06_original_native_continuation"
CONTRACT_REL = "Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
ORIGINAL_REL = NAMESPACE + "/control-data/original-controller-source.json"
PROFILE_REL = NAMESPACE + "/execution-profile.json"
METHODS = ("test_actual_preloader_refuses_original_order_and_loads_fixed_closure",)
CONTROL = {}
MIN_FREE = 1024**3
START_FREE = 1024**3
OUTPUT_LIMIT = 8 * 1024**2
FINAL_RECORD_RESERVE = 64 * 1024
OBSERVED_OUTPUT_PEAK = {"logicalBytes": 0, "allocatedBytes": 0}
MAX_INPUT = 4 * 1024**2

def require(value, message):
    if not value:
        raise RuntimeError(message)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def stamp():
    return datetime.now(timezone.utc).isoformat()

def raw_file(path, maximum=MAX_INPUT):
    observed = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(observed.st_mode)
            and observed.st_nlink == 1 and 0 <= observed.st_size <= maximum,
            "regular_bounded_single_link_input_required:" + str(path))
    raw = path.read_bytes()
    require(len(raw) == observed.st_size, "input_changed_while_reading:" + str(path))
    return raw, observed

def write(path, raw):
    require(not path.exists(), "exclusive_original_output_required:" + str(path))
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)

def write_json(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2) + "\n").encode())

def output_usage(output):
    logical, allocated, entries, vanished = 0, 0, 0, 0
    for path in (output, *output.rglob("*")):
        try:
            info = path.lstat()
        except FileNotFoundError:
            vanished += 1
            continue
        require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),
                "unexpected_control_output_type")
        logical += info.st_size
        allocated += info.st_blocks * 512
        entries += 1
    return {"logicalBytes": logical, "allocatedBytes": allocated,
            "observedEntries": entries, "concurrentlyRemovedEntries": vanished}

def capacity(root, output=None, *, start=False):
    free = shutil.disk_usage(root).free
    require(free >= (START_FREE if start else MIN_FREE), "capacity_reserve_not_available")
    usage = None
    if output is not None:
        usage = output_usage(output)
        budget = OUTPUT_LIMIT - FINAL_RECORD_RESERVE
        require(usage["logicalBytes"] <= budget and usage["allocatedBytes"] <= budget,
                "measured_control_output_budget_exceeded")
        for key in OBSERVED_OUTPUT_PEAK:
            OBSERVED_OUTPUT_PEAK[key] = max(OBSERVED_OUTPUT_PEAK[key], usage[key])
    return {"observedAt": stamp(), "freeBytes": free, "reserveBytes": MIN_FREE,
            "resourceProfile": "fixed-actual-preloader-1gib-8mib-v1",
            "currentUsage": usage, "observedOutputPeak": dict(OBSERVED_OUTPUT_PEAK),
            "finalRecordReserveBytes": FINAL_RECORD_RESERVE}

def git(root, argv, payload=None):
    return subprocess.check_output(["git", "-C", str(root), *argv], input=payload, timeout=30)

def source_rows(root, source, manifest):
    rows = manifest["inputs"]
    require(len({x["path"] for x in rows}) == len(rows), "duplicate_control_input")
    paths = [x["path"] for x in rows]
    require(all(isinstance(x, str) and x and not x.startswith("/") and
                all(y not in {".", ".."} for y in x.split("/")) and
                not any(y in x for y in ("\n", "\r", "\0", ":")) for x in paths),
            "unsafe_control_input")
    require(git(root, ["rev-parse", "HEAD"]).decode().strip() == source, "frozen_head_changed")
    require(not git(root, ["status", "--porcelain", "--untracked-files=no"]).strip(),
            "tracked_source_not_clean")
    tree = git(root, ["ls-tree", "-r", "--full-tree", "-z", source, "--", *paths])
    metadata = {}
    for item in tree.split(b"\0"):
        if not item:
            continue
        header, relative = item.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        require(kind == "blob" and mode in {"100644", "100755"}, "source_git_mode_not_regular")
        metadata[relative.decode()] = {"gitMode": mode, "gitBlob": oid}
    require(set(metadata) == set(paths), "frozen_git_input_set_mismatch")
    request = b"".join((source + ":" + path + "\n").encode() for path in paths)
    raw = git(root, ["cat-file", "--batch"], request)
    position = 0
    observed = {}
    for expected in rows:
        relative = expected["path"]
        line_end = raw.index(b"\n", position)
        oid, kind, size_raw = raw[position:line_end].decode().split()
        size = int(size_raw)
        require(kind == "blob" and 0 <= size <= MAX_INPUT, "bounded_git_blob_required")
        position = line_end + 1
        blob = raw[position:position + size]
        position += size
        require(raw[position:position + 1] == b"\n", "git_blob_frame_changed")
        position += 1
        physical, info = raw_file(root / relative)
        require(physical == blob and len(physical) == expected["bytes"]
                and sha(physical) == expected["sha256"]
                and stat.S_IMODE(info.st_mode) == expected["physicalMode"]
                and metadata[relative]["gitMode"] == expected["gitMode"]
                and oid == metadata[relative]["gitBlob"],
                "fixed_physical_git_input_mismatch:" + relative)
        observed[relative] = {
            "bytes": len(physical), "sha256": sha(physical),
            "physicalMode": stat.S_IMODE(info.st_mode),
            **metadata[relative], "inode": str(info.st_ino), "uid": info.st_uid,
        }
    require(position == len(raw), "extra_git_blob_output")
    return observed

def loaded_sources(root, fixed_rows):
    admitted = {x["path"]: x for x in fixed_rows if x["path"].endswith(".py")}
    names = {}
    for relative in admitted:
        names.setdefault(Path(relative).stem, set()).add(relative)
    observed = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not isinstance(filename, str) or not filename.endswith(".py"):
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            relative = path.relative_to(root).as_posix()
            require(relative in admitted, "unbound_loaded_repository_module:" + relative)
            require(not path.name.startswith("test_"), "old_test_module_loaded:" + relative)
            data, info = raw_file(path)
            row = admitted[relative]
            require(sha(data) == row["sha256"] and len(data) == row["bytes"]
                    and stat.S_IMODE(info.st_mode) == row["physicalMode"],
                    "loaded_repository_source_changed:" + relative)
            observed[name] = {"path": relative, "sha256": sha(data), "bytes": len(data)}
        elif name != "__main__" and name.rsplit(".", 1)[-1] in names:
            raise RuntimeError("foreign_repository_module_origin:" + name + ":" + str(path))
    return observed

def method_guard(root):
    def guard(frame, event, arg):
        if event == "call":
            name = frame.f_code.co_name
            filename = Path(frame.f_code.co_filename)
            if name.startswith("test_") and filename.is_absolute() and filename.resolve().is_relative_to(root):
                relative = filename.resolve().relative_to(root).as_posix()
                raise RuntimeError("old_repository_test_body_refused:" + relative + ":" + name)
        return guard
    return guard

class OriginalResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity, root, output, events):
        super().__init__(stream, descriptions, verbosity)
        self.root, self.output, self.events = root, output, events

    def event(self, outcome, test, **extra):
        value = {"at": stamp(), "outcome": outcome, "test": test.id(), **extra}
        self.events.append(value)
        with (self.output / "events.jsonl").open("ab") as stream:
            stream.write((json.dumps(value, sort_keys=True) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())

    def startTest(self, test):
        capacity(self.root, self.output)
        super().startTest(test)
        self.event("START", test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.event("PASS", test)

    def addError(self, test, err):
        super().addError(test, err)
        self.event("ERROR", test, exception=type(err[1]).__name__, message=str(err[1]))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.event("FAIL", test, exception=type(err[1]).__name__, message=str(err[1]))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.event("SKIP", test, reason=reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.event("SUBCASE_PASS" if err is None else "SUBCASE_FAIL", test,
                   subcase=str(subtest), exception=None if err is None else type(err[1]).__name__,
                   message=None if err is None else str(err[1]))

class PreloadOrderControl(unittest.TestCase):
    def test_actual_preloader_refuses_original_order_and_loads_fixed_closure(self):
        root, output = CONTROL["root"], CONTROL["output"]
        manifest, source = CONTROL["manifest"], CONTROL["source"]
        self.assertNotIn(ENTRY_MODULE, sys.modules)
        entry = importlib.import_module(ENTRY_MODULE)
        current_raw, _ = raw_file(root / CONTRACT_REL)
        original_raw, _ = raw_file(root / ORIGINAL_REL)
        current, original = json.loads(current_raw), json.loads(original_raw)
        head, admitted, imported_contract = entry._INITIAL_SOURCE
        self.assertEqual(head, source)
        self.assertEqual(imported_contract, current)
        self.assertEqual(set(admitted), set(current["inputs"]) | {CONTRACT_REL})
        self.assertEqual(len(admitted), 86)
        self.assertEqual(len(current["inputs"]), 85)
        self.assertEqual(original["inputs"], current["inputs"])
        self.assertEqual(original["modules"], current["modules"])
        old_without_order = {k: v for k, v in original.items() if k != "preload_modules"}
        new_without_order = {k: v for k, v in current.items() if k != "preload_modules"}
        self.assertEqual(old_without_order, new_without_order)
        expected = sorted(n for n in current["modules"]
                          if not n.startswith("test_") and n != ENTRY_MODULE)
        self.assertEqual(len(expected), 67)
        self.assertEqual(current["preload_modules"], expected)
        self.assertEqual(set(original["preload_modules"]), set(expected))
        self.assertEqual(original["preload_modules"].index("sdk06_compile_support"), 66)
        self.assertEqual(expected.index("sdk06_compile_support"), 33)
        self.assertEqual([n for n in original["preload_modules"] if n != "sdk06_compile_support"],
                         [n for n in expected if n != "sdk06_compile_support"])
        write_json(output / "actual-entry-admission.json", {
            "source": head, "actualPhysicalGitInputs": admitted,
            "originalContractSHA256": sha(original_raw), "currentContractSHA256": sha(current_raw),
            "inputRowsUnchanged": original["inputs"] == current["inputs"],
            "oldIndexZeroBased": 66, "newIndexZeroBased": 33,
        })
        before_refusal = entry.loaded_sources(root, current)
        write_json(output / "actual-loaded-after-entry-import.json", before_refusal)
        with self.subTest(scope="original-unsorted-list-refused-before-import-loop"):
            with self.assertRaisesRegex(
                ValueError, "^Current production preloads must equal the fixed declared closure$"
            ):
                entry.preload_current_sources(root, original)
            after_refusal = entry.loaded_sources(root, current)
            self.assertEqual(after_refusal, before_refusal)
            write_json(output / "original-list-refusal.json", {
                "expectedError": "Current production preloads must equal the fixed declared closure",
                "loadedBefore": before_refusal, "loadedAfter": after_refusal,
                "loadedSourcesUnchanged": after_refusal == before_refusal,
                "fixtureOrigin": manifest["originalContractOrigin"],
            })
        with self.subTest(scope="corrected-full-canonical-production-closure"):
            actual = entry.preload_current_sources(root, current)
            expected_paths = {
                relative: current["inputs"][relative]["sha256"]
                for name, relative in current["modules"].items() if not name.startswith("test_")
            }
            self.assertEqual(len(expected_paths), 68)
            self.assertEqual(actual, dict(sorted(expected_paths.items())))
            for name in manifest["productionModuleNames"]:
                self.assertIn(name, sys.modules)
                self.assertEqual(Path(sys.modules[name].__file__).resolve(),
                                 root / current["modules"][name])
            for name in manifest["oldTestModuleNames"]:
                self.assertNotIn(name, sys.modules)
            self.assertEqual(len(CONTROL["gitEvents"]), 3)
            write_json(output / "corrected-preloader-result.json", {
                "actualLoadedSources": actual, "expectedProductionModuleNames":
                    manifest["productionModuleNames"],
                "productionPreloadCount": len(expected), "productionModuleCountIncludingEntry": 68,
                "oldTestModulesImported": [], "gitEvents": CONTROL["gitEvents"],
                "scope": "actual source admission and imports only",
                "archiveRestoration": 0, "simulatorCommands": 0, "builds": 0, "productMethods": 0,
            })

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root, output = Path(args.root).resolve(), Path(args.output).absolute()
    require(len(args.source) == 40 and all(c in "0123456789abcdef" for c in args.source),
            "full_frozen_source_required")
    require(output.resolve() == output and not output.exists()
            and not output.is_relative_to(root) and output.parent.is_dir(),
            "fresh_outside_repository_output_required")
    initial_capacity = capacity(root, start=True)
    manifest_raw, _ = raw_file(root / MANIFEST_REL)
    require(manifest_raw == git(root, ["show", args.source + ":" + MANIFEST_REL]),
            "manifest_not_frozen_git_bytes")
    manifest = json.loads(manifest_raw)
    require(manifest["protocol"] == PROTOCOL and manifest["methods"] == list(METHODS)
            and manifest["outsideTestPath"] == WRAPPER_REL
            and manifest["oldMethodsToExecute"] == 0 and manifest["productTestsToExecute"] == 0
            and manifest["buildsToExecute"] == 0 and len(manifest["inputs"]) == 90,
            "exact_new_control_scope_required")
    wrapper_raw, _ = raw_file(Path(__file__).resolve())
    require(not Path(__file__).resolve().is_relative_to(root)
            and wrapper_raw == git(root, ["show", args.source + ":" + WRAPPER_REL]),
            "outside_wrapper_differs_from_frozen_original")
    profile_raw, _ = raw_file(root / PROFILE_REL)
    profile = json.loads(profile_raw)
    require(profile["profile"] == "fixed-actual-preloader-1gib-8mib-v1"
            and profile["minimumFreeBytes"] == MIN_FREE
            and profile["maximumOutputBytesLogicalAndAllocatedIncludingDirectories"] == OUTPUT_LIMIT
            and profile["maximumFileBytes"] == 256 * 1024
            and profile["executionSeconds"] == 60 and profile["ownedStopSeconds"] == 10,
            "fixed_execution_profile_changed")
    before = source_rows(root, args.source, manifest)
    output.mkdir(mode=0o700)
    output.chmod(0o700)
    write_json(output / "invocation.json", {
        "protocol": PROTOCOL, "source": args.source, "root": str(root),
        "outsideWrapper": str(Path(__file__).resolve()), "wrapperSHA256": sha(wrapper_raw),
        "manifestSHA256": sha(manifest_raw), "executionProfileSHA256": sha(profile_raw),
        "methods": list(METHODS), "initialCapacity": initial_capacity,
        "productTests": 0, "oldMethods": 0, "builds": 0,
        "sourceMode": "actual unchanged production loader; exact frozen outside control copy",
    })
    write_json(output / "source-before.json", before)
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(root / "Tools/PinkhaSimulatorGate")]
    result = None
    events, failure, before_loaded, after_loaded, after = [], None, None, None, None
    git_events = []
    CONTROL.update(root=root, output=output, source=args.source, manifest=manifest, gitEvents=git_events)
    started = time.monotonic()
    original_profile = sys.getprofile()
    pure_execution = {"active": False}
    admitted_paths = manifest["productionSourcePaths"]
    allowed_git = (
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        ["git", "-C", str(root), "ls-tree", "-r", "-z", args.source, "--", *admitted_paths],
        ["git", "-C", str(root), "cat-file", "--batch"],
    )
    def audit(event, event_args):
        if not pure_execution["active"]:
            return
        if event == "subprocess.Popen":
            executable, argv, cwd, _ = event_args
            require(executable == "git" and isinstance(argv, (list, tuple))
                    and list(argv) in allowed_git and cwd is None,
                    "nonadmitted_actual_loader_process_refused")
            git_events.append({"at": stamp(), "argv": list(argv), "cwd": cwd,
                               "GIT_OPTIONAL_LOCKS": os.environ.get("GIT_OPTIONAL_LOCKS")})
        elif event in {"os.system", "socket.connect", "socket.getaddrinfo", "os.exec", "os.posix_spawn"}:
            raise RuntimeError("nonadmitted_external_execution_refused:" + event)
        elif event == "open":
            path, _, flags = event_args
            if isinstance(path, (str, bytes, os.PathLike)) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                destination = Path(os.fsdecode(path)).absolute()
                require(destination.resolve() == destination and destination.is_relative_to(output),
                        "write_outside_owned_control_output_refused")
        elif event in {"os.mkdir", "os.remove", "os.rmdir", "os.rename", "os.link", "os.symlink"}:
            raise RuntimeError("unexpected_mutation_during_actual_preload:" + event)
    sys.addaudithook(audit)
    try:
        before_loaded = loaded_sources(root, manifest["inputs"])
        require(not before_loaded, "repository_module_loaded_before_control")
        write_json(output / "loaded-before.json", before_loaded)
        require([n for n in vars(PreloadOrderControl) if n.startswith("test_")] == list(METHODS),
                "exact_one_new_method_required")
        sys.setprofile(method_guard(root))
        pure_execution["active"] = True
        suite = unittest.TestSuite(PreloadOrderControl(name) for name in METHODS)
        with (output / "original-tests.log").open("x", encoding="utf-8") as stream:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                result = unittest.TextTestRunner(
                    stream=stream, verbosity=2,
                    resultclass=lambda s, d, v: OriginalResult(s, d, v, root, output, events),
                ).run(suite)
            stream.flush()
            os.fsync(stream.fileno())
        require(result.testsRun == 1 and not result.skipped and result.wasSuccessful(),
                "new_actual_preloader_control_not_successful")
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error),
                   "traceback": traceback.format_exc()}
    finally:
        pure_execution["active"] = False
        sys.setprofile(original_profile)
        write_json(output / "actual-git-events.json", git_events)
        for name, callable_ in (
            ("loaded-after", lambda: loaded_sources(root, manifest["inputs"])),
            ("source-after", lambda: source_rows(root, args.source, manifest)),
        ):
            try:
                value = callable_()
                write_json(output / (name + ".json"), value)
                if name == "loaded-after":
                    after_loaded = value
                else:
                    after = value
            except BaseException as error:
                record = {"phase": name, "type": type(error).__name__, "message": str(error),
                          "traceback": traceback.format_exc()}
                write_json(output / (name + "-failure.json"), record)
                if failure is None:
                    failure = record
        try:
            require(after == before, "physical_git_source_changed_during_control")
            require(before_loaded == {} and after_loaded is not None
                    and set(after_loaded) == set(manifest["productionModuleNames"]),
                    "actual_production_import_set_differs_from_fixed_closure")
            require(all(not name.startswith("test_") for name in after_loaded),
                    "old_test_module_imported")
            require(len(git_events) == 3, "unexpected_actual_loader_git_call_count")
            final_capacity = capacity(root, output)
        except BaseException as error:
            final_capacity = {"observedAt": stamp(), "freeBytes": shutil.disk_usage(root).free}
            if failure is None:
                failure = {"phase": "final_admission", "type": type(error).__name__,
                           "message": str(error), "traceback": traceback.format_exc()}
        evidence = {
            "protocol": PROTOCOL, "source": args.source, "status": "PASS" if failure is None else "FAIL",
            "failure": failure, "elapsedSeconds": time.monotonic() - started,
            "actualMethodsStarted": [x["test"] for x in events if x["outcome"] == "START"],
            "actualMethodsPassed": [x["test"] for x in events if x["outcome"] == "PASS"],
            "actualSubcasesPassed": sum(x["outcome"] == "SUBCASE_PASS" for x in events),
            "actualSubcasesFailed": sum(x["outcome"] == "SUBCASE_FAIL" for x in events),
            "testResult": None if result is None else {
                "methods": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
                "skips": len(result.skipped), "wasSuccessful": result.wasSuccessful()},
            "sourceInputs": len(before), "sourceUnchanged": after == before,
            "loadedBefore": None if before_loaded is None else len(before_loaded),
            "loadedAfter": None if after_loaded is None else len(after_loaded),
            "actualReadonlyGitCalls": len(git_events), "finalCapacity": final_capacity,
            "oldMethods": 0, "productTests": 0, "builds": 0, "archiveRestoration": 0,
            "claim": "One new actual-preloader control; no restore, simulator, compile, product or CI acceptance",
        }
        write_json(output / "receipt.json", evidence)
        originals = {}
        for path in sorted(output.iterdir()):
            if path.is_file():
                raw = path.read_bytes()
                originals[path.name] = {"bytes": len(raw), "sha256": sha(raw)}
        write_json(output / "original-files.json", originals)
        print(json.dumps(evidence, sort_keys=True))
    return 0 if failure is None else 1

if __name__ == "__main__":
    raise SystemExit(main())
