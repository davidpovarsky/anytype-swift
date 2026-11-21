"""Independent real-SIGTERM control of the frozen controller, not native acceptance."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
CONTROL = ROOT / "validation/control/Tools/TorahNativeOperations"
HARNESS = r'''
import json, os, signal, sys
from pathlib import Path
from unittest import mock
import run_account_rpc_space_close as lane

original_run_owned = lane.run_owned
def send_actual_cancel(command, cwd, env, log, timeout, entry, checkpoint):
    child = "import os,signal,time; print('owned-ready',flush=True); time.sleep(.05); os.kill(os.getppid(),signal.SIGTERM); time.sleep(60)"
    return original_run_owned([sys.executable, '-c', child], cwd, env, log, 5, entry, checkpoint)

def exercise_sequence(args, receipt, run):
    binary = Path(sys.executable).resolve()
    identity = {'binary': str(binary), 'binary_sha256': lane.digest(binary)}
    with mock.patch.object(lane, 'run_owned', send_actual_cancel), mock.patch.object(lane.base, 'RESERVE', 0):
        lane.run_sequence(identity, args.work, args.evidence, set())
    raise AssertionError('A real cancellation unexpectedly returned as success')

old = {s: signal.getsignal(s) for s in [signal.SIGINT, signal.SIGTERM]}
with mock.patch.object(lane, 'execute', exercise_sequence):
    code = lane.main(sys.argv[1:])
assert all(signal.getsignal(s) == h for s, h in old.items())
sys.exit(code)
'''

with tempfile.TemporaryDirectory(prefix="space-close-independent-cancel-") as temporary:
    directory = Path(temporary)
    unrelated = directory / "unrelated.txt"
    unrelated.write_bytes(b"preserve unrelated ownership")
    args = []
    for name in ["approved-source", "heart-legacy", "heart-new", "work", "evidence"]:
        args += ["--" + name, str(directory / name)]
    process = subprocess.run(
        [sys.executable, "-B", "-c", HARNESS, *args, "--expected-app-sha", "a" * 40],
        cwd=CONTROL, capture_output=True, text=True, timeout=20,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    assert process.returncode == 1, process.stderr
    evidence = directory / "evidence"
    receipt = json.loads((evidence / "space-close-receipt.json").read_text())
    sequence = json.loads((evidence / "space-close-sequence/result.json").read_text())
    cleanup = json.loads((evidence / "space-close-cleanup.json").read_text())
    copied = json.loads((evidence / "space-close-evidence-copy.json").read_text())
    assert receipt["status"] == sequence["status"] == "CANCELLED"
    assert receipt["finished_at"]
    assert sequence["actual_counts"] == {"native_processes": 1, "passing_test_invocations": 0}
    assert len(sequence["phases"]) == 1
    phase = sequence["phases"][0]
    assert phase["launch_requested"] is True and type(phase["pid"]) is int and phase["pid"] > 0
    assert phase["status"] == "CANCELLED" and phase["error_type"] == "KeyboardInterrupt"
    assert phase["process_exit_observed"] is True and phase["exit_code"] != 0
    assert phase["report_qualification"] == "NOT_RUN"
    assert cleanup["status"] == "PASS_REMOVED_OWNED_DISPOSABLE_ACCOUNT"
    assert cleanup["all_started_process_exits_observed"] is True
    assert not (directory / "work").exists()
    assert unrelated.read_bytes() == b"preserve unrelated ownership"
    assert copied["secret_scan"] == "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY"
    assert set(copied["files_sha256"]) == {"ownership.json", "result.json"}
    try:
        os.kill(phase["pid"], 0)
    except ProcessLookupError:
        pass
    else:
        raise AssertionError("Owned cancelled subprocess was not reaped")
    output = {
        "status": "PASS_REAL_SIGTERM_OWNED_PYTHON_PROCESS_CONTROL",
        "scope": "CONTROLLER_ONLY_NO_NATIVE_GO_COMPILE_OR_EXECUTION",
        "controller_sha256": hashlib.sha256((CONTROL / "run_account_rpc_space_close.py").read_bytes()).hexdigest(),
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "root_receipt_status": receipt["status"], "phase": phase,
        "actual_control_counts": sequence["actual_counts"],
        "owned_pid_no_longer_exists": True, "signal_handlers_restored": True,
        "owned_account_removed": True, "unrelated_file_preserved": True,
        "native_phase_output_withheld_without_secret_inventory": True,
        "native_go_tests": "NOT_RUN"
    }
    target = ROOT / "independent-cancellation-control.json"
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": output["status"], "report_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}))
