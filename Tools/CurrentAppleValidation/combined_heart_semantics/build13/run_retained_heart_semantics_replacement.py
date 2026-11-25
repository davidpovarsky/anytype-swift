"""Run the exact current Heart methods, then seal the real shutdown account."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
CONTROLLER_SHA256 = "8629edd564dd10692801ffe3f89eb3d2b2e0afffe511023daf3c9360f70794fd"
RETENTION_SHA256 = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")
    path.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--supervisor-root", type=Path, required=True)
    args = parser.parse_args()
    own = Path(__file__).resolve().parent
    controller = own / "combined_heart_semantics_replacement.py"
    retention = own / "retain_owned_heart_account.py"
    require(digest(controller) == CONTROLLER_SHA256 and digest(retention) == RETENTION_SHA256,
            "Reviewed current controller and private retention helper required")
    require(args.admission.is_absolute() and args.admission.resolve() == args.admission
            and digest(args.admission) == args.admission_sha256, "Exact immutable admission required")
    admission = json.loads(args.admission.read_bytes())
    require(admission["controllerSHA256"] == CONTROLLER_SHA256, "Admission belongs to another controller")
    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
            "Fresh actual test root required")
    directory = args.supervisor_root
    require(directory.is_absolute() and directory.parent.resolve() == directory.parent and not directory.exists()
            and directory != args.root and not args.root.is_relative_to(directory), "Fresh separate supervisor root required")
    directory.mkdir(mode=0o700)
    argv = [sys.executable, "-B", str(controller), "--admission", str(args.admission),
            "--admission-sha256", args.admission_sha256, "--root", str(args.root), "--keep-owned-simulator"]
    result = {"protocol": "pinkha-current-heart-retained-execution-v1", "status": "FAIL",
              "sourceCommit": admission["sourceCommit"], "controllerSHA256": CONTROLLER_SHA256,
              "retentionSHA256": RETENTION_SHA256, "admissionSHA256": args.admission_sha256,
              "argv": argv, "startedAt": time.time(), "fixtureRestorations": 0,
              "fixtureDeadlineChanges": 0, "appBuilds": 0, "rawPrivateDataUploaded": False,
              "fullEAcceptance": False, "physicalDevice": "NOT_RUN"}
    try:
        log = directory / "controller-original.log"
        with log.open("xb") as stream:
            process = subprocess.Popen(argv, stdout=stream, stderr=subprocess.STDOUT,
                                       cwd=directory, start_new_session=True)
            write(directory / "active.json", {"pid": process.pid, "pgid": process.pid, "argv": argv,
                  "sourceCommit": admission["sourceCommit"], "startedAt": time.time()})
            code = process.wait()
        log.chmod(0o600)
        result["controllerExitCode"] = code
        result["controllerLog"] = {"bytes": log.stat().st_size, "sha256": digest(log)}
        execution_path = args.root / "evidence/execution.json"
        require(execution_path.is_file(), "Original controller execution receipt is missing")
        execution_sha256 = digest(execution_path)
        execution = json.loads(execution_path.read_bytes())
        result["originalExecution"] = {"path": str(execution_path), "bytes": execution_path.stat().st_size,
                                       "sha256": execution_sha256, "status": execution["status"]}
        result["actualStages"] = {name: row["status"] for name, row in execution["stages"].items()}
        # The helper sees the finished original receipt, never a mutable draft.
        # A failed original method is preserved as failed even if backup succeeds.
        import retain_owned_heart_account as account
        require(Path(account.__file__).resolve() == retention, "Foreign private retention module")
        result["accountRetention"] = account.retain(args.root, execution_sha256)
        require(digest(execution_path) == execution_sha256, "Original test result changed during backup")
        if code == 0 and execution["status"] == "PASS_SIX_ACTUAL_COMBINED_HEART_METHODS":
            result["status"] = "PASS_SIX_ACTUAL_METHODS_AND_PRIVATE_ACCOUNT_RETENTION"
        else:
            result["status"] = "ORIGINAL_TEST_FAILURE_PRESERVED_WITH_PRIVATE_ACCOUNT"
    except BaseException as exc:
        result["firstFailure"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        result["finishedAt"] = time.time()
        write(directory / "receipt.json", result)
    print(json.dumps({key: result[key] for key in ("status", "sourceCommit", "actualStages", "firstFailure")
                      if key in result}, sort_keys=True))
    return 0 if result["status"] == "PASS_SIX_ACTUAL_METHODS_AND_PRIVATE_ACCOUNT_RETENTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
