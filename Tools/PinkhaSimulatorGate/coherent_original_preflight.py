"""Own only the current Release original-Products preflight simulator lifecycle."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from uuid import uuid4

import preflight
import wave15_batch as batch
import run_owned_single_lane as groups

PROTOCOL = "pinkha-coherent-original-preflight-v1"
ROOT = Path(__file__).resolve().parents[2]
PREPARE_SECONDS = 360.0
KINDS = ("iphone", "ipad")
require = batch.require


def read(path, maximum=2 * 1024**2):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= maximum,
            "Original lifecycle receipt is missing or unbounded")
    def unique(rows):
        result = {}
        for key, value in rows:
            require(key not in result, "Duplicate lifecycle JSON key")
            result[key] = value
        return result
    return json.loads(path.read_text(), object_pairs_hook=unique)


def save(path, value, *, original=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if original:
        with path.open("xb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    else:
        require(not path.is_symlink(), "Lifecycle receipt cannot be a symlink")
        temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
        with temporary.open("xb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)


def context():
    return dict(source_sha=os.environ.get("GITHUB_SHA"), run_id=os.environ.get("GITHUB_RUN_ID"),
                run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"))


def identity(value):
    require(isinstance(value, dict) and re.fullmatch("[0-9a-f]{40}", value.get("source_sha") or "")
            and all(isinstance(value.get(key), str) and re.fullmatch("[1-9][0-9]*", value[key])
                    for key in ("run_id", "run_attempt")), "Current controller/run/attempt identity required")


def actual_host():
    require(platform.system() == "Darwin" and platform.machine() == "arm64"
            and sys.version_info >= (3, 12), "Actual Apple ARM64 host and Python3.12 required")


class Commands:
    def __init__(self, control, directory, receipt, checkpoint, *, clock=time.monotonic,
                 execute=batch.run_worker_command, stopped=groups.verify_owned_group_stopped):
        self.control, self.directory, self.receipt, self.checkpoint = control, directory, receipt, checkpoint
        self.clock, self.execute, self.stopped = clock, execute, stopped

    def run(self, argv, name, timeout, *, observe=None):
        require(re.fullmatch("[a-z0-9-]+", name) and timeout > 0, "Invalid bounded preflight command")
        path = self.directory / (name + ".log")
        require(not path.exists(), "Original command log already exists")
        primary = None
        try:
            record = self.execute(argv, self.control, path, timeout)
        except BaseException as error:
            primary = error
            original = path.with_suffix(".command.json")
            try:
                record = read(original)
            except BaseException as metadata_error:
                record = dict(argv=argv, error_type=type(error).__name__,
                              original_receipt_failure=type(metadata_error).__name__)
        # Preserve a returned UUID before a later owned-group observation can fail.
        if observe is not None:
            try:
                observe(path, record)
            except BaseException as error:
                record["creation_observation_failure"] = dict(error_type=type(error).__name__, error=str(error))
                if primary is None: primary = error
        try:
            record["owned_group_quiescence"] = self.stopped(
                path.with_suffix(".command.json"), cleanup_profile=batch.COHERENT_HEART_PROFILE)
        except BaseException as error:
            record["quiescence_failure"] = dict(error_type=type(error).__name__, error=str(error),
                timeout_observations=getattr(error, "timeout_observations", []),
                quiescence_observation=getattr(error, "quiescence_observation", None))
            if primary is None: primary = error
        record.update(name=name, log_sha256=batch.digest(path) if path.is_file() else None)
        self.receipt.setdefault("commands", []).append(record)
        save(self.directory / (name + ".observation.json"), record, original=True)
        self.checkpoint()
        if primary is not None: raise primary
        require(record.get("return_code") == 0, "Original preflight command failed: " + name)
        return path


def planned_devices(inventory, binding):
    runtime, choices = preflight.select_pairs(inventory)
    require(set(choices) == set(KINDS) and isinstance(inventory.get("devices"), dict), "Complete original simulator inventory required")
    baseline = []
    names = []
    for items in inventory["devices"].values():
        require(isinstance(items, list), "Malformed baseline simulator list")
        for item in items:
            require(isinstance(item, dict) and batch.valid_udid(item.get("udid")), "Invalid baseline simulator identity")
            baseline.append(item["udid"].lower()); names.append(item.get("name"))
    require(len(baseline) == len(set(baseline)), "Duplicate baseline simulator UUID")
    planned = [dict(lane="preflight-" + kind, name="Pinkha-UI27-" + binding["run_id"] + "-" + kind,
                    device=choices[kind], runtime=runtime) for kind in KINDS]
    require(not set(names).intersection(item["name"] for item in planned), "Planned preflight name already exists")
    return planned, sorted(baseline)


def capture_created(directory, planned, intent, path, record, selected, checkpoint):
    require(path.is_file() and not path.is_symlink(), "Original create output missing")
    if path.stat().st_size > 128:
        return
    raw = path.read_bytes()
    try: udid = raw.decode("utf8").strip()
    except UnicodeError: return
    if not batch.valid_udid(udid):
        return
    argv = ["xcrun", "simctl", "create", planned["name"], planned["device"]["identifier"], planned["runtime"]["identifier"]]
    try:
        require(record.get("argv") == argv and udid.lower() not in intent["baseline_udids"],
                "Created UUID is baseline or differs from its original command")
        require(udid.lower() not in {row["udid"].lower() for row in selected.values()},
                "Two preflight creates returned the same UUID")
        owned = dict(planned, udid=udid)
        save(directory / "owned-simulator.json", owned, original=True)
        save(directory / "created-proof.json", dict(udid=udid, argv=argv,
            create_log=path.name, create_log_sha256=batch.digest(path),
            create_command_sha256=batch.digest(path.with_suffix(".command.json"))), original=True)
        kind = planned["lane"].removeprefix("preflight-")
        selected[kind] = {key: value for key, value in owned.items() if key != "lane"}
        checkpoint()
    except BaseException as error:
        save(directory / "creation-rejected.json", dict(error_type=type(error).__name__, error=str(error)), original=True)
        raise


def prepare(control, evidence, binding, *, factory=Commands, host=actual_host, clock=time.monotonic):
    directory = evidence / "preflight"
    directory.mkdir(parents=True, exist_ok=False)
    receipt = dict(protocol=PROTOCOL, status="RUNNING", phase="ADMISSION", selected={},
                   ui_tests_executed=0, started_at=batch.now(), **binding)
    checkpoint = lambda: save(directory / "preflight.json", receipt)
    checkpoint()
    started = clock()
    deadline = started + PREPARE_SECONDS
    runner = None
    def run(argv, name, maximum=60, *, observe=None):
        remaining = deadline - clock()
        require(remaining > 0, "Preflight preparation deadline exhausted")
        return runner.run(argv, name, min(maximum, remaining), observe=observe)
    try:
        identity(binding); host()
        runner = factory(control, directory, receipt, checkpoint, clock=clock)
        head = run(["git", "-C", str(control), "rev-parse", "HEAD"], "controller-head", 30).read_text().strip()
        require(head == binding["source_sha"], "Preflight must use the current controller checkout")
        dirty = run(["git", "-C", str(control), "status", "--porcelain", "--untracked-files=no"],
                    "controller-clean", 30).read_text()
        require(not dirty, "Current controller tracked source is not clean")
        xcode = run(["xcodebuild", "-version"], "xcode-version").read_text().strip()
        require(re.match(r"Xcode 27(?:\.|\s)", xcode), "Actual Xcode27 required")
        inventory_path = run(["xcrun", "simctl", "list", "--json"], "simulator-inventory")
        inventory = read(inventory_path, 16 * 1024**2)
        with (directory / "simulator-inventory.json").open("xb") as output:
            output.write(inventory_path.read_bytes())
        planned, baseline = planned_devices(inventory, binding)
        lifecycle = directory / "lifecycle"
        intent = dict(protocol=PROTOCOL, profile=batch.COHERENT_HEART_PROFILE, **binding,
            baseline_udids=baseline, baseline_inventory_sha256=batch.digest(inventory_path),
            preflight_devices=[], lane_devices=planned, created_at=batch.now())
        save(lifecycle / "intent.json", intent, original=True)
        receipt.update(phase="CREATE", intent_sha256=batch.digest(lifecycle / "intent.json"))
        checkpoint()
        for planned in intent["lane_devices"]:
            require(deadline - clock() > 0, "Preflight preparation deadline exhausted before create intent")
            kind = planned["lane"].removeprefix("preflight-")
            owned_dir = lifecycle / "lanes" / planned["lane"]
            owned_dir.mkdir(parents=True, exist_ok=False)
            argv = ["xcrun", "simctl", "create", planned["name"], planned["device"]["identifier"], planned["runtime"]["identifier"]]
            save(owned_dir / "create-started.json", dict(**binding, argv=argv,
                intent_sha256=receipt["intent_sha256"]), original=True)
            run(argv, "create-" + kind, 30, observe=lambda path, record, item=planned, target=owned_dir:
                capture_created(target, item, intent, path, record, receipt["selected"], checkpoint))
            require(kind in receipt["selected"], "Successful create did not return an exact owned UUID")
        swift = run(["swift", "--version"], "swift-version").read_text().strip()
        sdks = run(["xcodebuild", "-showsdks"], "xcode-sdks").read_text().strip()
        require(clock() <= deadline, "Preflight completed after its original preparation deadline")
        receipt.update(status="PREFLIGHT_PASS_UI_NOT_RUN", phase="COMPLETE", xcode=xcode,
            host_architecture=platform.machine(), python=sys.version, developer_dir=os.environ.get("DEVELOPER_DIR"),
            swift=swift, sdks=sdks)
        with open(os.environ["GITHUB_ENV"], "a") as output:
            for kind in KINDS: output.write("PINKHA_UI27_" + kind.upper() + "_UDID=" + receipt["selected"][kind]["udid"] + "\n")
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    receipt.update(finished_at=batch.now(), elapsed_seconds=max(0, clock()-started),
                   preparation_budget_seconds=PREPARE_SECONDS)
    checkpoint()
    return receipt


def admitted_journal(directory, binding):
    lifecycle = directory / "lifecycle"
    intent = read(lifecycle / "intent.json")
    identity(binding)
    require(intent.get("protocol") == PROTOCOL and intent.get("profile") == batch.COHERENT_HEART_PROFILE
            and all(intent.get(key) == value for key, value in binding.items()), "Preflight journal source/run/attempt differs")
    inventory_path = directory / "simulator-inventory.log"
    require(batch.digest(inventory_path) == intent.get("baseline_inventory_sha256"), "Original pre-create baseline changed")
    planned, baseline = planned_devices(read(inventory_path, 16 * 1024**2), binding)
    require(intent.get("lane_devices") == planned and intent.get("baseline_udids") == baseline
            and intent.get("preflight_devices") == [], "Preflight journal differs from original pair selection/baseline")
    known = []
    attempted = 0
    admitted = []
    for item in planned:
        target = lifecycle / "lanes" / item["lane"]
        if not target.exists(): continue
        require(target.is_dir() and not target.is_symlink() and not (target / "creation-rejected.json").exists(),
                "Unsafe or rejected preflight creation cannot authorize cleanup")
        started = read(target / "create-started.json")
        argv = ["xcrun", "simctl", "create", item["name"], item["device"]["identifier"], item["runtime"]["identifier"]]
        require(started == dict(**binding, argv=argv, intent_sha256=batch.digest(lifecycle / "intent.json")),
                "Original preflight create intent differs")
        owned_path = target / "owned-simulator.json"
        log = directory / ("create-" + item["lane"].removeprefix("preflight-") + ".log")
        if not log.exists():
            require(not owned_path.exists() and not (target / "created-proof.json").exists(),
                    "Owned creation receipt exists without its original command log")
            continue
        require(log.is_file() and not log.is_symlink(), "Original create log changed kind")
        attempted += 1
        admitted.append(item)
        if not owned_path.exists(): continue
        owned = read(owned_path)
        require(batch.valid_udid(owned.get("udid")) and owned == dict(item, udid=owned["udid"])
                and owned["udid"].lower() not in baseline, "Created receipt is baseline or changed ownership")
        proof = read(target / "created-proof.json")
        log = directory / ("create-" + item["lane"].removeprefix("preflight-") + ".log")
        original = read(log.with_suffix(".command.json"))
        require(proof == dict(udid=owned["udid"], argv=argv, create_log=log.name,
                    create_log_sha256=batch.digest(log), create_command_sha256=batch.digest(log.with_suffix(".command.json")))
                and log.read_text().strip() == owned["udid"] and original.get("argv") == argv,
                "Original create output/command proof changed")
        known.append({key: value for key, value in owned.items() if key != "lane"})
    require(len({row["udid"].lower() for row in known}) == len(known), "Duplicate owned preflight UUID")
    return dict(intent, lane_devices=admitted), known, attempted


def _admit_prior_batch_cleanup(evidence, binding, known, attempted):
    """Admit only this current continuation's exact already-cleaned owned IDs."""
    paths = [evidence / name for name in ("batch-intent.json", "execution.json", "batch-cleanup.json")]
    if not all(path.is_file() and not path.is_symlink() for path in paths) or len(known) != attempted:
        return None
    import coherent_original_products as original
    intent, execution, report = [read(path) for path in paths]
    if not all(value.get("protocol") == original.PROTOCOL and value.get("profile") == batch.COHERENT_HEART_PROFILE
        and value.get("source_sha") == original.SOURCE and value.get("control_source_sha") == binding["source_sha"]
        and value.get("run_id") == binding["run_id"] and value.get("run_attempt") == binding["run_attempt"]
        for value in (intent, execution)):
        return None
    if (intent.get("continuation") != original.NAME or intent.get("build_origin") != original.origin_fields()
        or execution.get("cleanup") != report or report.get("status") != "PASS"
        or sorted(intent.get("preflight_devices", []), key=lambda row: row.get("udid", "")) !=
           sorted(known, key=lambda row: row["udid"])):
        return None
    for device in known:
        rows = [row for row in report.get("devices", []) if row.get("name") == device["name"]]
        if len(rows) != 1: return None
        row = rows[0]
        if row.get("status") == "NOT_PRESENT":
            if not any(q.get("selector") == device["udid"] and q.get("selector_kind") == "OWNED_UDID"
                       and q.get("status") == "RETURNED_VALID_SCOPED_INVENTORY" for q in report.get("inventory_queries", [])):
                return None
        elif row.get("status") == "DELETED_OWNED_SIMULATOR" and row.get("udid") == device["udid"]:
            reconciled = row.get("delete_timeout_reconciliation", {})
            if not (row.get("delete_exit_code") == 0 or reconciled.get("status") in
                {"DELETION_PROVED_BY_ACTUAL_SCOPED_ABSENCE", "DELETION_PROVED_BY_SUCCESSFUL_SAME_OWNED_UUID_RETRY"}):
                return None
        else: return None
    return dict(status="REUSED_EXACT_CURRENT_BATCH_CLEANUP", originals={p.name: batch.digest(p) for p in paths},
                owned_udids=[row["udid"] for row in known], new_cleanup_commands=0)


def prior_batch_cleanup(evidence, binding, known, attempted, *, observation=None):
    """Unusable optional prior proof cannot block independently owned cleanup."""
    observation = {} if observation is None else observation
    try:
        result = _admit_prior_batch_cleanup(evidence, binding, known, attempted)
        observation["status"] = "ADMITTED" if result is not None else "NOT_ADMITTED"
        return result
    except (OSError, ValueError, RuntimeError, TypeError, AttributeError, KeyError) as error:
        observation.update(status="UNUSABLE_PRIOR_REPORT", error_type=type(error).__name__, error=str(error))
        return None


def cleanup(control, evidence, binding, *, policy=batch.cleanup_owned, host=actual_host):
    directory = evidence / "preflight"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "lifecycle-cleanup.json"
    require(not destination.exists(), "Preserve the original lifecycle cleanup receipt")
    receipt = dict(protocol=PROTOCOL, action="cleanup", status="RUNNING", started_at=batch.now(), **binding)
    save(destination, receipt, original=True)
    try:
        lifecycle = directory / "lifecycle"
        if not (lifecycle / "intent.json").exists():
            require(not (lifecycle / "lanes").exists(), "Creation state exists without its original ownership intent")
            receipt.update(status="NO_OWNED_CREATION", cleanup_commands=0)
        else:
            identity(binding)
            intent, known, attempted = admitted_journal(directory, binding)
            receipt.update(intent_sha256=batch.digest(lifecycle / "intent.json"), attempted_creations=attempted,
                           known_owned_udids=[row["udid"] for row in known])
            if attempted == 0:
                receipt.update(status="NO_OWNED_CREATION", cleanup_commands=0)
            else:
                host()
                head = subprocess.check_output(["git", "-C", str(control), "rev-parse", "HEAD"],
                    text=True, timeout=30).strip()
                require(head == binding["source_sha"], "Cleanup controller checkout differs")
                admission = {}
                receipt["prior_batch_cleanup_admission"] = admission
                prior = prior_batch_cleanup(evidence, binding, known, attempted, observation=admission)
                if prior is not None:
                    receipt.update(status="PASS", prior_batch_cleanup=prior, cleanup_commands=0)
                    receipt["finished_at"] = batch.now()
                    save(destination, receipt)
                    return receipt
                # The unchanged policy owns its original scoped queries, exact
                # identity checks and 180-second coherent cleanup deadline.
                require(not (lifecycle / "batch-cleanup.json").exists(), "Original fallback cleanup report already exists")
                save(lifecycle / "cleanup-admitted-intent.json", intent, original=True)
                receipt["cleanup_admitted_intent_sha256"] = batch.digest(lifecycle / "cleanup-admitted-intent.json")
                report = policy(intent, lifecycle)
                require(report.get("status") == "PASS", "Owned preflight fallback cleanup did not pass")
                receipt.update(status="PASS", fallback_cleanup=report,
                               fallback_cleanup_sha256=batch.digest(lifecycle / "batch-cleanup.json"))
    except BaseException as error:
        receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    receipt["finished_at"] = batch.now()
    save(destination, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=("prepare", "cleanup"))
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    args.control, args.evidence = args.control.resolve(), args.evidence.resolve()
    require(args.control == ROOT and args.evidence.is_relative_to(ROOT / "build"),
            "Current controller-owned build/evidence paths required")
    previous = {}
    def cancel(signum, frame):
        raise KeyboardInterrupt("Owned preflight lifecycle cancelled")
    try:
        for number in (signal.SIGTERM, signal.SIGINT):
            previous[number] = signal.getsignal(number); signal.signal(number, cancel)
        receipt = (prepare if args.action == "prepare" else cleanup)(args.control, args.evidence, context())
        print(json.dumps({key: receipt.get(key) for key in ("status", "source_sha", "run_id", "run_attempt")}))
        return 0 if receipt["status"] in {"PREFLIGHT_PASS_UI_NOT_RUN", "PASS", "NO_OWNED_CREATION"} else 1
    finally:
        for number, handler in previous.items(): signal.signal(number, handler)


if __name__ == "__main__":
    raise SystemExit(main())
