"""Run only impacted controller controls and preserve actual original outputs."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[3]
evidence = Path(__file__).resolve().parent
paths = [
    "Tools/PinkhaNativeDerived/heart_runtime_profile.py",
    "Tools/PinkhaNativeDerived/download_heart_runtime.py",
    "Tools/PinkhaNativeDerived/install_verified_heart.py",
    "Tools/PinkhaNativeDerived/test_heart_runtime_profile.py",
    "Tools/PinkhaNativeDerived/attachment_runtime.py",
    "Tools/PinkhaNativeDerived/build_t5_r15_runtime.py",
    "Tools/PinkhaNativeDerived/run_t5_native_attachment.py",
    "Tools/PinkhaSimulatorGate/run_ui27.py",
    "Tools/PinkhaSimulatorGate/run_wave15_acceptance.py",
    "Tools/PinkhaSimulatorGate/wave15_batch.py",
    "Tools/PinkhaSimulatorGate/test_wave15_batch.py",
    "Tools/PinkhaSimulatorGate/test_heart_runtime_binding.py",
    "Tools/PinkhaSimulatorGate/test_hanlin_ui_runtime.py",
    "Tools/Hanlin/run_host_tests.py",
    ".github/workflows/pinkha-simulator-ui27.yml",
    ".github/workflows/pinkha-sdk06-tests.yml",
    ".github/workflows/torah-inspector-ipados27.yml",
]
def hashes():
    return {p: hashlib.sha256((root / p).read_bytes().replace(b"\r\n", b"\n")).hexdigest() for p in paths}
before = hashes()
commands = [
    ("admission", 11, "Tools/PinkhaNativeDerived/test_heart_runtime_profile.py", []),
    ("corrected-observer", 6, "Tools/PinkhaSimulatorGate/test_heart_runtime_binding.py", []),
    ("legacy-observer", 3, "Tools/PinkhaSimulatorGate/test_hanlin_ui_runtime.py", [
        "ExistingProcessMappingControls.test_existing_process_mapping_has_no_launch_and_each_command_is_bounded",
        "ExistingProcessMappingControls.test_legacy_probe_wrapper_retains_its_single_launch_and_mapping",
        "ExistingProcessMappingControls.test_changed_main_or_missing_runtime_marker_is_rejected"]),
    ("worker-propagation", 2, "Tools/PinkhaSimulatorGate/test_wave15_batch.py", [
        "BatchControls.test_corrected_runtime_profile_and_original_producer_survive_each_fresh_worker_lane",
        "BatchControls.test_retained_heart_worker_shares_only_build_with_three_fresh_devices"]),
]
results = []
for name, expected, script, methods in commands:
    log = evidence / (name + ".log")
    argv = [sys.executable, "-B", str(root / script), *methods, "-v"]
    started = time.time()
    with log.open("wb") as output:
        try:
            completed = subprocess.run(argv, cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"), timeout=180)
            code = completed.returncode
        except subprocess.TimeoutExpired:
            code = None
    raw = log.read_bytes()
    counts = re.findall(rb"Ran ([0-9]+) tests? in ", raw)
    passed = code == 0 and counts == [str(expected).encode()] and raw.rstrip().endswith(b"OK")
    item = dict(name=name, command=argv, expected_methods=expected, exit_code=code,
                status="PASS" if passed else "FAIL_OR_TIMEOUT", wall_seconds=time.time()-started,
                log_sha256=hashlib.sha256(raw).hexdigest())
    results.append(item)
    (evidence / "progress.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf8")
    if not passed:
        break
after = hashes()
passed = len(results) == len(commands) and all(r["status"] == "PASS" for r in results) and before == after
receipt = dict(status="PASS_CONTROLLER_CONTROLS" if passed else "FAIL_OR_INCOMPLETE",
               platform=platform.platform(), python=sys.version, results=results,
               methods=22 if passed else None, sources_unchanged=before == after,
               source_hash_normalization="Git LF text bytes", source_before=before, source_after=after,
               synthetic_fixture_scope="DOWNLOAD_ADMISSION_AND_PROCESS_OBSERVER_CONTROLS",
               native_test_executions=0, simulator_executions=0)
(evidence / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf8")
print(json.dumps(dict(status=receipt["status"], methods=receipt["methods"], sources_unchanged=before == after,
                     commands=[dict(name=x["name"],status=x["status"],exit_code=x["exit_code"]) for x in results])))
raise SystemExit(0 if passed else 1)
