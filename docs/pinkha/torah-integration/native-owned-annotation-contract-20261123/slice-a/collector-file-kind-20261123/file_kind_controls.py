#!/usr/bin/env python3
"""Three file-kind controls using the exact retained native fixture bytes."""
import hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, zipfile
sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[2]
DRIVER = ROOT / "slice-a/run_native_archive.py"
BASE = "9ae8a63521ddd988f01d9118b7128a26ad94acd9"
PREFIX = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123/"
ARCHIVE = ROOT / "slice-a/run-45139622096/original-native-archive.zip"
def sha(raw): return hashlib.sha256(raw).hexdigest()
old_result = subprocess.run(["git", "--git-dir=/mnt/development/projects/git-mirrors/anytype-swift.git", "show", BASE + ":" + PREFIX + "slice-a/run_native_archive.py"], capture_output=True, timeout=20)
assert old_result.returncode == 0
old = {"__name__": "previous_owned_collector", "__file__": str(DRIVER)}
exec(compile(old_result.stdout, "previous_owned_collector.py", "exec"), old)
spec = importlib.util.spec_from_file_location("candidate_owned_collector", DRIVER)
candidate = importlib.util.module_from_spec(spec); spec.loader.exec_module(candidate)
assert sha(ARCHIVE.read_bytes()) == "428f7c124649d7d40067b31704b63742a9da17e35425a9f8a3b1ab89839c9df9"
results = []
def refused(call, reason):
    try: call()
    except RuntimeError as error: assert str(error) == reason, str(error)
    else: raise AssertionError("Expected concrete file-kind refusal")
with tempfile.TemporaryDirectory(prefix="otzaria-collector-file-kind-") as directory:
    fixtures = pathlib.Path(directory)
    frozen = {}
    with zipfile.ZipFile(ARCHIVE) as zipped:
        for name in zipped.namelist():
            if not name.startswith("fixtures/"): continue
            leaf = name.removeprefix("fixtures/")
            assert "/" not in leaf and "\\" not in leaf
            raw = zipped.read(name); (fixtures / leaf).write_bytes(raw); frozen[leaf] = sha(raw)
    candidate.verify_fixture_inventory(fixtures)
    results.append({"case": "authentic_17_regular_files_accepted", "result": "PASS", "files": len(frozen)})
    target = fixtures / "schema-registration-00.json"
    original = target.read_bytes()
    target.unlink(); target.mkdir()
    try:
        old["verify_fixture_inventory"](fixtures)
        refused(lambda: candidate.verify_fixture_inventory(fixtures), "Specimen evidence must be a regular file")
        results.append({"case": "expected_phase_directory_rejected", "result": "PASS", "previous_collector_accepted": True})
    finally: target.rmdir(); target.write_bytes(original)
    target.unlink(); target.symlink_to("schema-registration-01.json")
    try:
        old["verify_fixture_inventory"](fixtures)
        refused(lambda: candidate.verify_fixture_inventory(fixtures), "Retained path contains a symlink")
        results.append({"case": "expected_phase_symlink_rejected", "result": "PASS", "previous_collector_accepted": True})
    finally: target.unlink(); target.write_bytes(original)
    assert {p.name for p in fixtures.iterdir()} == set(frozen)
    assert all(sha((fixtures / name).read_bytes()) == digest for name, digest in frozen.items())
report = {"schema": 1, "status": "THREE_NEW_ACTUAL_FILESYSTEM_CONTROLS_PASS", "cases": results, "base": BASE,
    "driver_sha256": sha(DRIVER.read_bytes()), "artifact_sha256": sha(ARCHIVE.read_bytes()), "native_cases_reexecuted": 0,
    "previous_four_controls_reexecuted": False, "workflow_conclusion": "failure",
    "global_after_all_tests_stability_gate_retroactively_completed": False, "owned_temporary_directory_removed": True}
pathlib.Path(__file__).with_name("RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"status": report["status"], "passed": len(results), "native_cases_reexecuted": 0}))
