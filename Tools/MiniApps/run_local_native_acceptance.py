#!/usr/bin/env python3
"""Execute the original five native Anytype objectives with a genuine local identity.

This entry point reuses the original source/build/entitlement/product/selection
and five-method execution gates. It never supplies synthetic GitHub metadata.
"""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_native_acceptance as original
from local_execution import PRIVATE_ROOT, POLICY, prepare, identity, digest, write
from local_producer import admit as admit_producer


def cleanup_owned(args, receipt):
    descriptor = identity(args.app, args.local_execution, args.local_execution_sha256)
    path = args.evidence / "preflight/preflight.json"
    if not path.is_file():
        return
    preflight = json.loads(path.read_bytes())
    original.require(preflight["execution_origin"] == "local-mac"
        and preflight["run_id"] == descriptor["run_id"]
        and preflight["source_sha"] == descriptor["source_sha"]
        and preflight["local_execution_sha256"] == args.local_execution_sha256,
        "Foreign local simulator preflight")
    inventory = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"],
                                                  text=True, timeout=30))
    devices = {row["udid"]: row for rows in inventory["devices"].values() for row in rows}
    observations = []
    for kind, selected in preflight["selected"].items():
        udid = selected["udid"]
        name = "Pinkha-UI27-" + descriptor["run_id"] + "-" + kind
        original.require(kind in {"ipad", "iphone"} and re.fullmatch(r"[0-9A-Fa-f-]{36}", udid)
            and selected["name"] == name, "Unowned simulator identity")
        if udid not in devices:
            observations.append({"udid": udid, "already_absent": True})
            continue
        original.require(devices[udid]["name"] == name, "Simulator name/ownership changed")
        for operation in ("shutdown", "delete"):
            result = subprocess.run(["xcrun", "simctl", operation, udid],
                                    capture_output=True, text=True, timeout=60)
            observations.append({"udid": udid, "operation": operation,
                "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
            if operation == "delete":
                original.require(result.returncode == 0, "Owned simulator deletion failed")
    receipt["owned_simulator_cleanup"] = observations
    write(args.evidence / "owned-simulator-cleanup.json", observations)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--app", type=Path, default=PRIVATE_ROOT / "source")
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--derived", type=Path, required=True)
    parser.add_argument("--phase", choices=("all", "build", "test", "cleanup"), default="all")
    parser.add_argument("--execution-sha256")
    parser.add_argument("--retain-simulators", action="store_true")
    args = parser.parse_args()
    args.app, args.evidence, args.derived = map(Path.resolve, (args.app, args.evidence, args.derived))
    original.require(args.app == PRIVATE_ROOT / "source"
        and args.evidence.is_relative_to(PRIVATE_ROOT / "evidence")
        and args.derived.is_relative_to(PRIVATE_ROOT) and not args.derived.is_relative_to(args.app)
        and not args.derived.is_relative_to(args.evidence) and not args.evidence.is_relative_to(args.derived),
        "Unowned or overlapping original application execution roots")
    args.local_cache_snapshot = args.local_cache_snapshot_sha256 = None
    args.local_execution = args.evidence / "local-execution.json"
    args.lane, args.device, args.language = "miniapps-native", "ipad", "en"
    args.heart_source_run_id = None
    policy = json.loads(POLICY.read_bytes())
    args.runtime_profile = policy["runtime_profile"]
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    for key, value in policy["build_environment"].items():
        original.require(key not in os.environ or os.environ[key] == value,
                         "An existing native environment value differs: " + key)
        os.environ[key] = value
    os.environ.update(UI27_DEVICE_FAMILY="ipad", UI27_LANGUAGE="en")
    receipt = {"status": "RUNNING", "phase": args.phase, "execution_origin": "local-mac",
               "github_run_id": None, "actual_test_methods": 0,
               "started_at": datetime.now(timezone.utc).isoformat()}
    def stop(signum, frame):
        raise InterruptedError("Owned local original application execution interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        if args.phase in {"all", "build"}:
            original.require(not args.derived.exists(), "Fresh owned products required for the original build")
            descriptor = prepare(args.app, args.evidence, args.derived)
            args.local_execution_sha256 = digest(args.local_execution)
        else:
            original.require(args.execution_sha256 is not None,
                             "An existing execution requires its frozen descriptor digest")
            args.local_execution_sha256 = args.execution_sha256
            descriptor = identity(args.app, args.local_execution, args.local_execution_sha256)
        receipt.update(source_sha=descriptor["source_sha"], run_id=descriptor["run_id"],
                       local_execution_sha256=args.local_execution_sha256)
        if args.phase == "cleanup":
            cleanup_owned(args, receipt)
            receipt["status"] = "OWNED_SIMULATOR_CLEANUP_ONLY"
            return 0
        if args.phase in {"all", "build"}:
            build = {"status": "BUILDING", "started_at": datetime.now(timezone.utc).isoformat()}
            original.build_consumer(args, build)
            receipt["consumer_build_status"] = build["status"]
            original.require(build["status"] == "BUILD_PASS_TESTS_NOT_RUN",
                             "The original application build has not passed its complete gates")
            if args.phase == "build":
                receipt["status"] = "BUILD_PASS_ORIGINAL_FIVE_NOT_RUN"
                return 0
        pin = json.loads((args.app / "Tools/MiniApps/producer.json").read_bytes())
        admit_producer(args.app, args.evidence / "producer", args.evidence, pin)
        original.execute(args, receipt)
        original.require(receipt["status"] == "MINIAPPS_TWO_APP_NATIVE_PASS",
                         "The original five application objectives did not pass")
        receipt["actual_test_methods"] = 5
        return 0
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        return 1
    finally:
        if (args.phase != "cleanup" and args.phase != "build" and not args.retain_simulators
                and getattr(args, "local_execution_sha256", None)):
            try:
                cleanup_owned(args, receipt)
            except BaseException as error:
                receipt["cleanup_error"] = str(error)
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        write(args.evidence / "local-execution-result.json", receipt)
        print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
