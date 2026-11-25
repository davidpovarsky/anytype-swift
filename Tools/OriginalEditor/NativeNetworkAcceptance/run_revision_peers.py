#!/usr/bin/env python3
"""Run only the new native revision phase on the retained two-repository fixture.

This controller never compiles, creates accounts/objects, copies peer databases,
or supplies native bodies to a peer. It requires an already built real native
test binary and preserves its own final result even after a failing child.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import sys
import time

ROLES = ("producer", "consumer")
TEST = "^TestOtzariaOriginalNetworkRevisionPeer$"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_regular(path: Path) -> None:
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode) or stat.S_ISLNK(value.st_mode):
        raise ValueError("Expected an owned regular input file: " + str(path))


def require_private_directory(path: Path) -> None:
    value = path.lstat()
    if not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode) or value.st_mode & 0o077:
        raise ValueError("Expected an existing private original fixture directory: " + str(path))


def write_json(path: Path, value: object) -> None:
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    temporary = path.with_name(path.name + ".writing-" + str(os.getpid()))
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            raise FileExistsError("Existing evidence is immutable: " + str(path))
        os.rename(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def read_json(path: Path) -> dict:
    require_regular(path)
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("Expected a retained object receipt: " + str(path))
    return value


def run_pair(binary: Path, fixture: Path, phase: Path, suffix: str, timeout: int) -> list[dict]:
    children = []
    start = time.monotonic()
    abort_recorded = False
    try:
        for base_role in ROLES:
            role = base_role + suffix
            output = phase / (role + ".log")
            handle = output.open("xb")
            os.chmod(output, 0o600)
            environment = os.environ.copy()
            environment.update({
                "OTZARIA_ORIGINAL_NETWORK_ROOT": str(fixture),
                "OTZARIA_ORIGINAL_REVISION_RUN": str(phase),
                "OTZARIA_ORIGINAL_REVISION_ROLE": role,
            })
            command = [str(binary), "-test.run=" + TEST, "-test.v", "-test.timeout=10m"]
            process = subprocess.Popen(command, cwd=phase, env=environment,
                                       stdout=handle, stderr=subprocess.STDOUT)
            children.append({"role": role, "process": process, "handle": handle,
                             "log": output, "command": command})
        while any(item["process"].poll() is None for item in children):
            failures = [item for item in children if item["process"].poll() not in (None, 0)]
            timed_out = time.monotonic() - start > timeout
            if (failures or timed_out) and not abort_recorded:
                write_json(phase / "abort.json", {
                    "reason": "peer_process_failed" if failures else "controller_deadline",
                    "failed_roles": [item["role"] for item in failures],
                    "actual_exit_codes": {item["role"]: item["process"].returncode for item in failures},
                    "request": "cancel native test contexts and perform actual AccountStop",
                })
                abort_recorded = True
            if time.monotonic() - start > timeout + 45:
                for item in children:
                    if item["process"].poll() is None:
                        item["process"].terminate()
                        item["forced_termination"] = True
            if time.monotonic() - start > timeout + 60:
                for item in children:
                    if item["process"].poll() is None:
                        item["process"].kill()
                        item["forced_kill"] = True
            time.sleep(0.5)
    finally:
        for item in children:
            if item["process"].poll() is None:
                item["process"].terminate()
                try:
                    item["process"].wait(timeout=15)
                except subprocess.TimeoutExpired:
                    item["process"].kill()
                    item["process"].wait()
            item["handle"].close()
    elapsed = time.monotonic() - start
    results = []
    for item in children:
        role = item["role"]
        receipt_root = phase / role
        output = {
            "role": role, "pid": item["process"].pid,
            "exit_code": item["process"].returncode, "pair_seconds": elapsed,
            "command": item["command"], "log_sha256": sha256(item["log"]),
            "forced_termination": item.get("forced_termination", False),
            "forced_kill": item.get("forced_kill", False),
        }
        for kind in ("process", "stop", "accepted"):
            path = receipt_root / (kind + ".json")
            if path.exists():
                output[kind] = read_json(path)
                output[kind + "_sha256"] = sha256(path)
        results.append(output)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--binary-sha256", required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--phase", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    arguments = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("Native acceptance is restricted to the actual Mac.")
    for path in (arguments.binary, arguments.source_manifest, arguments.fixture, arguments.phase):
        if not path.is_absolute():
            raise ValueError("Every native input/output path must be absolute.")
    if not re.fullmatch(r"[0-9a-f]{64}", arguments.binary_sha256):
        raise ValueError("An exact native binary SHA-256 is required.")
    require_regular(arguments.binary)
    require_regular(arguments.source_manifest)
    require_private_directory(arguments.fixture)
    credential = arguments.fixture / "development-mnemonic.private"
    require_regular(credential)
    if credential.stat().st_mode & 0o077:
        raise ValueError("The retained development credential is not private.")
    if sha256(arguments.binary) != arguments.binary_sha256:
        raise ValueError("The actual native binary differs from its frozen receipt.")
    # Read only nonsecret identity data; never copy/reveal the credential.
    pointer = read_json(arguments.fixture / "source-pointer.json")
    for key in ("account_id", "space_id", "object_id", "annotation_uuid"):
        if not isinstance(pointer.get(key), str) or not pointer[key]:
            raise ValueError("The previously observed native identity is missing.")
    fixture = arguments.fixture.resolve(strict=True)
    phase = arguments.phase
    for role in ROLES:
        require_private_directory(fixture / (role + "-repository"))
    if phase == fixture or phase.is_relative_to(fixture):
        raise ValueError("New phase evidence must be separate from the existing peer fixture.")
    if not phase.parent.is_dir() or phase.parent.is_symlink():
        raise ValueError("An existing ordinary parent for phase evidence is required.")
    phase.mkdir(mode=0o700)
    result = {
        "schema": "otzaria.original.native-network-revision-run.v1",
        "status": "RUNNING", "binary": str(arguments.binary),
        "binary_sha256": arguments.binary_sha256,
        "source_manifest": str(arguments.source_manifest),
        "source_manifest_sha256": sha256(arguments.source_manifest),
        "fixture": str(fixture), "phase": str(phase),
        "same_account_id": pointer["account_id"], "same_space_id": pointer["space_id"],
        "same_object_id": pointer["object_id"], "annotation_uuid": pointer["annotation_uuid"],
        "new_account_created_by_controller": False,
        "native_local_receipt_used_as_network_ack": False,
        "compile_performed_by_controller": False,
        "children": [],
    }
    write_json(phase / "invocation.json", result)
    start = time.monotonic()
    try:
        live = run_pair(arguments.binary, fixture, phase, "", arguments.timeout)
        result["children"].extend(live)
        validate_children(live, pointer, reopened=False)
        cold = run_pair(arguments.binary, fixture, phase, "-reopen", arguments.timeout)
        result["children"].extend(cold)
        validate_children(cold, pointer, reopened=True)
        accepted_hash = read_json(phase / "consumer-applied-pointer.json")["root_sha256"]
        if any(item["accepted"].get("root_sha256") != accepted_hash for item in live + cold):
            raise ValueError("Live/cold processes did not observe the same accepted native root.")
        result["final_root_sha256"] = accepted_hash
        result["status"] = "PASS"
    except BaseException as error:
        result["status"] = "FAILED"
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
    finally:
        result["elapsed_seconds"] = time.monotonic() - start
        result["max_child_rss_platform_units"] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        result["binary_unchanged"] = sha256(arguments.binary) == arguments.binary_sha256
        result["source_manifest_unchanged"] = sha256(arguments.source_manifest) == result["source_manifest_sha256"]
        if not result["binary_unchanged"] or not result["source_manifest_unchanged"]:
            result["status"] = "FAILED_INPUT_DRIFT"
        # The known development credential is checked only in memory. A match
        # forbids publishing the affected log; no secret bytes enter the result.
        private_bytes = credential.read_bytes().strip()
        result["logs_with_credential_match"] = [
            p.name for p in phase.glob("*.log")
            if private_bytes and private_bytes in p.read_bytes()
        ]
        result["public_log_release_allowed"] = not result["logs_with_credential_match"]
        result["phase_bytes"] = sum(p.stat().st_size for p in phase.rglob("*") if p.is_file())
        write_json(phase / "result.json", result)
        print(json.dumps({key: result[key] for key in
                          ("status", "phase", "elapsed_seconds", "phase_bytes",
                           "binary_unchanged", "public_log_release_allowed")}))
    return 0 if result["status"] == "PASS" else 1


def validate_children(children: list[dict], pointer: dict, reopened: bool) -> None:
    if len(children) != 2 or len({item["pid"] for item in children}) != 2:
        raise ValueError("Two distinct actual native peer processes are required.")
    for item in children:
        if item["exit_code"] != 0 or item["forced_termination"] or item["forced_kill"]:
            raise ValueError("A native process failed or required forced termination: " + item["role"])
        observed = item.get("process", {})
        stopped = item.get("stop", {})
        accepted = item.get("accepted", {})
        if (observed.get("pid") != item["pid"]
                or observed.get("same_account") != pointer["account_id"]
                or observed.get("same_space") != pointer["space_id"]
                or observed.get("same_object") != pointer["object_id"]
                or observed.get("network_mode") != 0 or observed.get("lan_sync_disabled") is not True
                or observed.get("new_account_created") is not False
                or stopped.get("returned") is not True or stopped.get("application_absent") is not True
                or accepted.get("same_native_root") != pointer["object_id"]):
            raise ValueError("The actual peer identity/network/stop evidence differs: " + item["role"])
        if reopened:
            if accepted.get("actual_fresh_process_reopen") is not True or accepted.get("read_only") is not True:
                raise ValueError("Cold original account reopening was not observed.")
        elif item["role"] == "producer":
            if (accepted.get("status") != "ACTUAL_OTHER_PROCESS_NATIVE_REVISION_READBACK"
                    or accepted.get("complete_original_baseline_blocks_equal") is not True
                    or accepted.get("changed_peer_block_absent") is not True):
                raise ValueError("The other process did not read the full conditional native result.")
        elif (accepted.get("actual_remote_change_observed_before_stale_compare") is not True
                or accepted.get("stale_native_compare_refused_without_apply_or_head_change") is not True
                or accepted.get("actual_conditional_original_apply") is not True
                or accepted.get("independent_peer_readback_observed") is not True):
            raise ValueError("Remote change, stale conflict, native replacement or peer observation is absent.")


if __name__ == "__main__":
    raise SystemExit(main())
