#!/usr/bin/env python3
"""Current import admission only; retain original method PASS and wrapper FAIL."""
import argparse
import ast
import contextlib
import hashlib
import importlib
import importlib.machinery
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
DOC = Path(__file__).resolve().parent
ORIGINAL_HEAD = "97563de533579b0705eed0ad0028bdaa944ff470"
SOURCE = "c853f6b68860f037d014c17cb2d268b8e9c1631a"
TEST = "test_coherent_selection_order.ReleaseSelectionOrderTests.test_final_editor_plan_precedes_owned_seal_and_native_admission"
PAIR = "Tools/PinkhaSimulatorGate/run_t5_apple_pair.py"
PAIR_SHA = "11e11ec19eca11d506f56b37ad8ff76bcdbc40a28a4c233b4e57cb86432b1340"
ORIGINAL_EXECUTION_SHA = "72cbce55797bc58517a7091352634485d38adb450d18b3742ecf807c10278c98"
OUT = Path("/mnt/development/projects/diagnostics/release-selection-order-controls-20261123/admission-only1")
RESERVE = 2500000000
MARGIN = 16 * 1024 * 1024
META = ("admission-inputs.json", "audit-admission-only.py")


def need(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def guard(margin=0):
    free = shutil.disk_usage(ROOT).free
    need(free >= RESERVE + margin, "Owned capacity guard failed: " + str(free))
    return free


def git(*args):
    return subprocess.check_output(["git", "--no-optional-locks", "-C", str(ROOT), *args], timeout=30)


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    need(len(raw) <= 2 * 1024 * 1024, "Bounded audit metadata required")
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o400)
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def observe_sources(manifest):
    fixed = {row["path"]: row for row in manifest["inputs"]}
    metadata = [(DOC / name).relative_to(ROOT).as_posix() for name in META]
    paths = sorted([*fixed, *metadata])
    need(len(paths) == len(set(paths)) == 118, "Exact supplemental input inventory required")
    tree = {}
    for line in git("ls-tree", "-rz", "HEAD", "--", *paths).split(b"\0"):
        if line:
            header, name = line.split(b"\t", 1)
            mode, kind, blob = header.split()
            need(kind == b"blob", "Source is not a regular Git blob")
            tree[name.decode()] = {"git_mode": mode.decode(), "git_blob": blob.decode()}
    need(set(tree) == set(paths), "Git input inventory differs")
    result = []
    for name in paths:
        path = ROOT / name
        info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and path.resolve() == path,
             "Source path is not one regular current file: " + name)
        data = path.read_bytes()
        need(data == git("cat-file", "blob", tree[name]["git_blob"]), "Physical/Git input differs: " + name)
        row = {"path": name, "bytes": len(data), "mode": stat.S_IMODE(info.st_mode),
               "sha256": digest(data), **tree[name],
               "inode": info.st_ino, "mtime_ns": info.st_mtime_ns, "uid": info.st_uid}
        if name in fixed:
            need(all(row[k] == v for k, v in fixed[name].items()), "Frozen input differs: " + name)
        result.append(row)
    return result


def original_evidence(manifest, current):
    root = DOC / "original-attempt1"
    old = json.loads((root / "execution.json").read_bytes())
    need(digest((root / "execution.json").read_bytes()) == ORIGINAL_EXECUTION_SHA, "Original execution changed")
    need(old["status"] == "FAIL" and old["checked_head"] == ORIGINAL_HEAD and old["source_commit"] == SOURCE
         and old["tests_run"] == 1 and old["subcase_passes"] == 3 and old["named_passes"] == [TEST]
         and old["named_failures"] == [] and old["selected_tests"] == [TEST]
         and old["actual_local_modules"] == 33 and old["old_tests_run"] == 0
         and old["actual_simulator_commands"] == 0 and old["actual_native_or_product_methods"] == 0
         and old["inputs_unchanged"] is False and old["loaded_unchanged"] is False
         and old["failure"] == {"type": "RuntimeError", "message": "Unadmitted repository module: " + PAIR},
         "Original named PASS / wrapper FAIL boundary differs")
    events = [json.loads(line) for line in (root / "events.jsonl").read_text().splitlines()]
    need([v["action"] for v in events] == ["START", "SUBCASE_PASS", "SUBCASE_PASS", "SUBCASE_PASS", "PASS"]
         and all(v["test"] == TEST for v in events)
         and all(isinstance(v["time_ns"], int) for v in events)
         and all(a["time_ns"] <= b["time_ns"] for a, b in zip(events, events[1:])),
         "Original actual named event sequence differs")
    for event, scenario in zip(events[1:4], ("successful_language_then_guard",
            "language_failure_before_seal", "post_seal_plan_drift")):
        expected = ("test_final_editor_plan_precedes_owned_seal_and_native_admission "
                    "(test_coherent_selection_order.ReleaseSelectionOrderTests."
                    "test_final_editor_plan_precedes_owned_seal_and_native_admission) "
                    "(scenario='" + scenario + "')")
        need(event["subcase"] == expected and event["error_type"] is None, "Original subcase differs")
    stderr = (root / "original.stderr").read_text()
    need("\nRan 1 test in " in stderr and "\nOK\nTraceback (most recent call last):\n" in stderr
         and stderr.endswith("RuntimeError: Unadmitted repository module: " + PAIR + "\n"),
         "Original method success and subsequent admission failure must remain visible")
    need((root / "original.stdout").read_bytes() == b"", "Original stdout differs")
    declared = old["original_outputs"]
    # Nested control execution.json files are original outputs; exclude only the top receipt.
    actual = {p.relative_to(root).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
              for p in root.rglob("*") if p.is_file() and p != root / "execution.json"}
    need(len(declared) == 62 and actual == declared, "Original output inventory differs")
    old_before = json.loads((root / "source-before.json").read_bytes())
    by_path = {row["path"]: row for row in current}
    need(len(old_before) == 44 and all(by_path[row["path"]] == row for row in old_before),
         "Current original inputs differ from available original before metadata")
    for row in old_before:
        need(git("show", ORIGINAL_HEAD + ":" + row["path"]) == (ROOT / row["path"]).read_bytes(),
             "Original frozen Git input differs")
    need(by_path[PAIR] == manifest["late_input"], "Current late input differs from its post-run observation")
    need(git("show", ORIGINAL_HEAD + ":" + PAIR) == (ROOT / PAIR).read_bytes()
         and digest((ROOT / PAIR).read_bytes()) == PAIR_SHA, "Late input is not exact frozen Git")
    old_manifest = json.loads((DOC / "control-inputs.json").read_bytes())
    need(manifest["python_modules"] == dict(old_manifest["python_modules"], run_t5_apple_pair=PAIR),
         "Supplemental module map must add only the exact late pair")
    old_loaded = json.loads((root / "loaded-before.json").read_bytes())
    need(len(old_loaded) == 33 and old_loaded == manifest["original_loaded_before"], "Original loaded-before differs")
    expected = dict(old_loaded, run_t5_apple_pair={"path": PAIR, "sha256": PAIR_SHA})
    need(manifest["expected_current_loaded"] == expected and len(expected) == 34, "Current loaded inventory differs")
    original_external = Path(manifest["original_attempt_directory"])
    need(not (root / "source-after.json").exists() and not (root / "loaded-after.json").exists()
         and not (original_external / "source-after.json").exists()
         and not (original_external / "loaded-after.json").exists(), "Missing historical after cannot be relabelled")
    copied = manifest["preserved_originals"]
    need(len(copied) == 69, "Exact original copy inventory required")
    for row in copied:
        source = Path(row["source"])
        info = source.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and source.resolve() == source
             and stat.S_IMODE(info.st_mode) == row["original_mode"] == 0o400
             and info.st_uid == row["original_uid"] and info.st_ino == row["original_inode"]
             and info.st_mtime_ns == row["original_mtime_ns"], "Original immutable identity differs")
        raw = source.read_bytes()
        need(len(raw) == row["bytes"] and digest(raw) == row["sha256"]
             and raw == (ROOT / row["path"]).read_bytes(), "Original/copy bytes differ")
    return {"original_status": "FAIL", "retained_named_passes": [TEST], "retained_subcase_passes": 3,
            "original_before_rows": 44, "original_loaded_before_count": 33,
            "original_loaded_after_available": False, "original_source_after_available": False,
            "historical_loaded_hashes_reconstructed": False, "preserved_originals": 69}


def loaded(manifest):
    allowed = set(manifest["python_modules"].values())
    result = {}
    for name, module in sorted(sys.modules.items()):
        value = getattr(module, "__file__", None)
        if value is None:
            continue
        path = Path(value).resolve()
        if name in manifest["python_modules"]:
            need(path == ROOT / manifest["python_modules"][name], "Required module is foreign: " + name)
        try:
            relative = path.relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if path == Path(__file__).resolve():
            continue
        need(relative in allowed and path.suffix == ".py", "Unadmitted current repository module: " + relative)
        result[name] = {"path": relative, "sha256": digest(path.read_bytes())}
    return result


def source_trace(manifest):
    review = json.loads((DOC / "late-import-source-review.json").read_bytes())
    need(review["late_input"] == manifest["late_input"]
         and review["historical_loaded_after_available"] is False
         and review["historical_source_after_available"] is False, "Source trace scope differs")
    for row in review["call_path"]:
        raw = (ROOT / row["path"]).read_bytes()
        tree = ast.parse(raw)
        nodes = [v for v in ast.walk(tree) if isinstance(v, ast.FunctionDef) and v.name == row["function"]]
        need(len(nodes) == 1 and digest(raw) == row["source_sha256"]
             and ast.get_source_segment(raw.decode(), nodes[0]) == row["source"],
             "Exact late import call-path source differs")
    tree = ast.parse((ROOT / PAIR).read_bytes())
    eager = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    local = set(manifest["python_modules"])
    for node in eager:
        names = [a.name.split(".")[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split(".")[0]]
        need(all(name not in local and name in sys.stdlib_module_names for name in names), "Unexpected eager pair import")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            need(not node.decorator_list and all(v is None or isinstance(v, ast.Constant)
                 and v.value in (None, True, False) for v in [*node.args.defaults, *node.args.kw_defaults]),
                 "Unexpected pair definition-time operation")
        elif isinstance(node, ast.If):
            need(ast.dump(node.test, include_attributes=False) ==
                 "Compare(left=Name(id='__name__', ctx=Load()), ops=[Eq()], comparators=[Constant(value='__main__')])",
                 "Unexpected eager pair branch")
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.Expr)):
            need(not any(isinstance(v, ast.Call) for v in ast.walk(node)), "Unexpected eager pair data read/call")
        else:
            need(isinstance(node, (ast.Import, ast.ImportFrom)), "Unexpected pair top-level shape")


def import_only(manifest):
    for relative in ("Tools/Hanlin", "Tools/PinkhaNativeDerived", "Tools/PinkhaSimulatorGate"):
        sys.path.insert(0, str(ROOT / relative))
    for name, relative in manifest["python_modules"].items():
        spec = importlib.machinery.PathFinder.find_spec(name, sys.path)
        need(spec is not None and Path(spec.origin).resolve() == ROOT / relative, "Current import origin differs: " + name)
    need(loaded(manifest) == {}, "Fresh process already loaded repository modules")
    permitted_definitions = {}
    for name in ("test_coherent_selection_order", "test_coherent_owned_continuation"):
        path = ROOT / manifest["python_modules"][name]
        tree = ast.parse(path.read_bytes())
        permitted_definitions[str(path)] = {"<module>"} | {v.name for v in ast.walk(tree) if isinstance(v, ast.ClassDef)}
    state = {"active": False, "blocked_calls": 0}
    def audit(event, args):
        if not state["active"]:
            return
        prohibited = event == "subprocess.Popen" or event == "os.system" or event.startswith(("os.exec", "os.spawn", "os.fork"))
        prohibited = prohibited or event in {"socket.connect", "socket.bind", "os.mkdir", "os.rmdir",
            "os.remove", "os.rename", "os.unlink", "os.chmod", "os.truncate", "os.utime", "os.link", "os.symlink"}
        if event == "open" and len(args) >= 3 and isinstance(args[2], int):
            prohibited = prohibited or bool(args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if prohibited:
            state["blocked_calls"] += 1
            raise RuntimeError("Process/network/write operation forbidden during import-only admission: " + event)
    def profile(frame, event, arg):
        if event == "call" and frame.f_code.co_filename in permitted_definitions:
            if frame.f_code.co_name not in permitted_definitions[frame.f_code.co_filename]:
                state["blocked_calls"] += 1
                raise RuntimeError("Fixture or test body forbidden in import-only admission: " + frame.f_code.co_name)
    need(sys.getprofile() is None, "Unexpected existing profiling callback")
    sys.dont_write_bytecode = True
    sys.pycache_prefix = str(OUT / "unused-bytecode")
    sys.addaudithook(audit)
    try:
        state["active"] = True
        sys.setprofile(profile)
        importlib.import_module("test_coherent_selection_order")
        first = loaded(manifest)
        need(first == manifest["original_loaded_before"], "Current base import closure differs")
        importlib.import_module("run_t5_apple_pair")
        final = loaded(manifest)
        need(final == manifest["expected_current_loaded"], "Current supplemental import closure differs")
    finally:
        sys.setprofile(None)
        state["active"] = False
    need(state["blocked_calls"] == 0 and not (OUT / "unused-bytecode").exists(), "Import-only scope was violated")
    return first, final, state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()
    start_free = guard(MARGIN)
    head = git("rev-parse", "HEAD").decode().strip()
    need(head == args.expected_head and len(head) == 40 and head != ORIGINAL_HEAD, "Exact new audit freeze required")
    need(git("status", "--porcelain=v1", "--untracked-files=all") == b"", "Clean audit checkout required")
    need(not OUT.exists() and OUT.parent.is_dir(), "Fresh fixed audit output required")
    manifest = json.loads((DOC / META[0]).read_bytes())
    need(manifest["protocol"] == "release-selection-order-supplemental-admission-v1"
         and manifest["original_head"] == ORIGINAL_HEAD and manifest["source_commit"] == SOURCE
         and len(manifest["python_modules"]) == 40 and manifest["test_methods_to_run"] == 0,
         "Exact supplemental audit manifest required")
    OUT.mkdir(mode=0o700)
    before = after = base_loaded = current_loaded = original = None
    failure = None
    import_state = None
    started = time.time()
    with (OUT / "original.stdout").open("x") as stdout, (OUT / "original.stderr").open("x") as stderr:
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                before = observe_sources(manifest)
                save(OUT / "current-source-before.json", before)
                original = original_evidence(manifest, before)
                save(OUT / "retained-original-boundary.json", original)
                source_trace(manifest)
                guard()
                base_loaded, current_loaded, import_state = import_only(manifest)
                save(OUT / "current-loaded-base.json", base_loaded)
                save(OUT / "current-loaded-supplemental.json", current_loaded)
                guard()
                after = observe_sources(manifest)
                need(after == before, "Current audit inputs changed")
                need(original_evidence(manifest, after) == original, "Original evidence changed during current audit")
                need(loaded(manifest) == current_loaded, "Current loaded closure changed")
                need(git("status", "--porcelain=v1", "--untracked-files=all") == b"", "Audit checkout changed")
                save(OUT / "current-source-after.json", after)
                guard()
        except BaseException as error:
            failure = {"type": type(error).__name__, "message": str(error)}
            traceback.print_exc(file=stderr)
        finally:
            stdout.flush()
            stderr.flush()
            os.fsync(stdout.fileno())
            os.fsync(stderr.fileno())
    outputs = {p.relative_to(OUT).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
               for p in sorted(OUT.rglob("*")) if p.is_file()}
    receipt = {"protocol": "release-selection-order-current-import-admission-only-v1",
        "status": "PASS" if failure is None else "FAIL", "checked_head": head, "source_commit": SOURCE,
        "original_head": ORIGINAL_HEAD, "original_qualification_status": "FAIL",
        "original_execution_sha256": ORIGINAL_EXECUTION_SHA, "retained_original_boundary": original,
        "historical_loaded_after_available": False, "historical_source_after_available": False,
        "historical_after_reconstructed": False, "actual_test_methods_executed": 0,
        "actual_native_or_product_methods": 0, "actual_simulator_commands": 0,
        "current_source_inputs": len(before or []), "current_inputs_unchanged": before is not None and after == before,
        "current_base_loaded_modules": len(base_loaded or {}), "current_loaded_modules": len(current_loaded or {}),
        "import_only_guard": import_state, "failure": failure, "start_free": start_free,
        "final_free": shutil.disk_usage(ROOT).free, "elapsed_seconds": time.time() - started,
        "manifest_sha256": digest((DOC / META[0]).read_bytes()),
        "runner_sha256": digest(Path(__file__).read_bytes()),
        "python_executable": sys.executable, "python_version": sys.version, "original_outputs": outputs}
    # Retain an admission failure even if a later capacity/source guard failed.
    saved = save(OUT / "execution.json", receipt)
    for path in OUT.rglob("*"):
        if path.is_file():
            path.chmod(0o400)
    print(json.dumps({"status": receipt["status"], "receipt": saved, "failure": failure,
                      "tests_run": 0, "current_loaded_modules": receipt["current_loaded_modules"]}))
    return 0 if failure is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
