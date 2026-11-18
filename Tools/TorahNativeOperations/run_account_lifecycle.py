#!/usr/bin/env python3
"""Build two pinned native clients and reopen one disposable T2 account four times.

This is a native account/Space lifecycle proof, not two App clients, a public
operations RPC, or permission to enable the App capability. Production Heart
changes remain separately inventoried; the account fixtures are test overlays.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import subprocess
import sys
from uuid import uuid4

import run_native_registration as closure

HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
APPROVED_SOURCE = "947fbde24d5657d0e1229f45bb3993648884a8a1"
APPROVAL = "docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval/revision-14"
LEGACY_PATCH = "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077"
LEGACY_INVENTORY = "952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14"
BUILDER = "Tools/PinkhaNativeDerived/build_custom_heart.py"
BUILDER_SHA = "8534f5a3ecc1df8321dc3820409f1c8812d876bfe7989877bf121681d04955fd"
PROTOCOL = "pinkha-t2-account-lifecycle-v1"
METHOD = "TestT2AccountLifecyclePhase"
PHASES = [("new-create", "new"), ("new-reopen", "new"), ("legacy-edit", "legacy"), ("new-recover", "new")]
FIXTURES = ("account_phase_test.go", "legacy_runtime_test.go", "new_runtime_test.go")
EXPORTS = {"document.json", "document.pbc"}
VISIBLE = "t2visiblejournalcontrolc729"
PRIVATE = "t2privatejournalcontentc729"
TAGS = "nogrpcserver nowatchdog nosigar nomutexdeadlockdetector timetzdata rasterizesvg"
PASS = "PASS_NATIVE_ACCOUNT_PRIVATE_HISTORY_LIFECYCLE"
SCOPE = "two exact native Linux binaries; four processes reopen one synthetic account; App capability OFF; two App clients and iOS NOT_RUN"
RESERVE = 8 * 1024**3


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def digest(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), "Regular nonsymlink file required: " + str(path))
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def relative(value: str) -> Path:
    path = PurePosixPath(value)
    require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and ":" not in value, "Unsafe source path")
    return Path(*path.parts)


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8").strip()


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def terminate_owned(process: subprocess.Popen) -> None:
    """Only the session/process group created by this controller may be signalled."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass
    # A child can ignore TERM after its parent exits. Reaping only the parent
    # must not leave that owned process group running in the next account phase.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=10)


def run_process(command: list[str], cwd: Path, env: dict, log: Path, timeout: int) -> int:
    require(os.name == "posix", "Native lifecycle execution is Linux-only")
    require(not log.exists(), "Refusing to reuse a prior command log")
    with log.open("xb") as stream:
        process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            terminate_owned(process)
            raise
        finally:
            stream.flush()
            os.fsync(stream.fileno())
    require(code == 0, "Native command failed: " + log.name)
    return process.pid


def fixture_identity(directory: Path) -> tuple[str, dict[str, str]]:
    value = hashlib.sha256()
    hashes = {}
    require({p.name for p in directory.glob("*.go")} == set(FIXTURES), "Unexpected account fixture Go source")
    for name in sorted(FIXTURES):
        file = directory / name
        hashes[name] = digest(file)
        value.update(name.encode() + b"\0" + file.read_bytes())
    return value.hexdigest(), hashes


def composition(legacy: dict, registration: dict) -> tuple[dict, dict]:
    require(legacy.get("heart_sha") == registration.get("heart_sha") == HEART, "Wrong native composition base")
    old = {}
    for entry in legacy["files"]:
        name = entry["path"]
        relative(name)
        require(name not in old, "Duplicate r14 inventory entry")
        old[name] = {"before_sha256": entry["before_sha256"], "after_sha256": entry["after_sha256"]}
    private = dict(registration["tracked"])
    for name, hash_value in registration["overlay"].items():
        require(name not in private, "Tracked/overlay T2 path collision")
        private[name] = {"before_sha256": None, "after_sha256": hash_value}
    for name in private:
        relative(name)
    require(not set(old).intersection(private), "r14/T2 composition collision includes tracked AND overlay paths")
    for inventory in (old, private):
        for entry in inventory.values():
            require(re.fullmatch(r"[0-9a-f]{64}", entry["after_sha256"]) is not None,
                    "Invalid native after hash")
            require(entry["before_sha256"] is None or re.fullmatch(r"[0-9a-f]{64}", entry["before_sha256"]),
                    "Invalid native before hash")
    return old, {**old, **private}


def verify_source(root: Path, expected: dict, modules: dict) -> dict:
    require(git(root, "rev-parse", "HEAD") == HEART, "Wrong native source HEAD")
    hashes = {}
    for name, entry in expected.items():
        target = root / relative(name)
        require(target.resolve().is_relative_to(root), "Native source escaped checkout")
        hashes[name] = digest(target)
        require(hashes[name] == entry["after_sha256"], "Native source changed: " + name)
    tracked = {name for name, entry in expected.items() if entry["before_sha256"] is not None}
    require(set(git(root, "diff", "--name-only", "HEAD").splitlines()) == tracked,
            "Unexpected tracked native changes")
    require(set(git(root, "ls-files", "--others", "--exclude-standard").splitlines()) <= set(expected) - tracked,
            "Unexpected native file outside composition inventory")
    require(all(digest(root / name) == value for name, value in modules.items()), "Native Go module files changed")
    return hashes


def apply_composition(root: Path, old_patch: Path, private_patch: Path, overlay: Path,
                      registration: dict, expected: dict, role: str) -> dict:
    require(role in {"legacy", "new"}, "Unknown runtime role")
    require(git(root, "rev-parse", "HEAD") == HEART and not git(root, "status", "--porcelain"),
            "Fresh exact Heart checkout required")
    modules = {name: digest(root / name) for name in ["go.mod", "go.sum"]}
    for name, entry in expected.items():
        target = root / relative(name)
        before = entry["before_sha256"]
        require((not target.exists()) if before is None else digest(target) == before,
                "Native composition base differs: " + name)
    patches = [old_patch] + ([private_patch] if role == "new" else [])
    for patch in patches:
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=root, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=root, check=True)
    if role == "new":
        require({p.relative_to(overlay).as_posix() for p in overlay.rglob("*.go")} == set(registration["overlay"]),
                "Unexpected T2 overlay source")
        for name, value in registration["overlay"].items():
            source, target = overlay / relative(name), root / relative(name)
            require(digest(source) == value and not target.exists(), "Refusing an overlay replacement")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    return {"module_hashes": modules, "source_hashes": verify_source(root, expected, modules)}


def runtime_version(role: str, registration_hash: str) -> str:
    require(role in {"legacy", "new"}, "Unknown runtime role")
    result = "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + LEGACY_PATCH
    if role == "new":
        result += "-pinkha-t2-registry-v1-" + registration_hash
    return result


def contains(file: Path, value: str) -> bool:
    needle, tail = value.encode(), b""
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            data = tail + chunk
            if needle in data:
                return True
            tail = data[-max(len(needle) - 1, 0):]
    return False


def verify_binary(role: str, identity: dict, registration_hash: str) -> None:
    binary = Path(identity["binary"])
    require(digest(binary) == identity["binary_sha256"], "Native binary bytes changed")
    with binary.open("rb") as stream:
        require(stream.read(6) == b"\x7fELF\x02\x01", "Actual 64-bit little-endian ELF required")
    require(identity["role"] == role and identity["heart_sha"] == HEART
            and identity["legacy_patch_sha256"] == LEGACY_PATCH
            and identity["registration_patch_sha256"] == (registration_hash if role == "new" else "none"),
            "Native role/source identity differs")
    require(identity["runtime_version"] == runtime_version(role, registration_hash), "Wrong native version identity")
    require(all(contains(binary, value) for value in
                [HEART, identity["runtime_version"], identity["fixture_sha256"], PROTOCOL, METHOD]),
            "Missing linked native/fixture source identity")
    require(contains(binary, "-pinkha-t2-registry-v1-" + registration_hash) == (role == "new"),
            "Legacy binary contains new T2 runtime marker")


def validate_state(state: dict) -> None:
    for key in ["AccountID", "SpaceID", "DocumentID", "BlockID", "RootID", "OperationID", "ClaimID", "ChangeID"]:
        require(isinstance(state.get(key), str) and bool(state[key]), "Missing original native state: " + key)
    require(Path(state["AccountID"]).name == state["AccountID"]
            and state["AccountID"] not in {".", ".."}, "Unsafe native account identity")
    require(len({state[key] for key in ["SpaceID", "DocumentID", "BlockID", "RootID", "ChangeID"]}) == 5,
            "Expected distinct actual native identities")
    require(re.fullmatch(r"[0-9a-f]{32}", state["OperationID"]), "Wrong operation identity")
    require(re.fullmatch(r"[0-9a-f]{64}/[0-9a-f]{64}", state["ClaimID"]), "Wrong immutable claim identity")
    require(re.fullmatch(r"[0-9a-f]{64}", state.get("OperationSHA256", "")), "Missing canonical operation hash")
    require(set(state.get("RawChanges", {})) == {state["RootID"], state["ChangeID"]}
            and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in state["RawChanges"].values()),
            "Exact signed root and operation hashes required")
    require(state.get("Heads") == [state["ChangeID"]], "Wrong signed private tree head")


def validate_phase(report: dict, phase: str, role: str, identity: dict, nonce: str,
                   account_root: Path, pid: int, state: dict, state_hash: str) -> None:
    validate_state(state)
    require((phase, role) in PHASES and report.get("protocol") == PROTOCOL and report.get("phase") == phase
            and report.get("role") == role, "Wrong native phase/role/protocol")
    require(report.get("pid") == pid and type(pid) is int and pid > 0 and report.get("nonce") == nonce,
            "Stale or foreign native process receipt")
    for key in ["heart_sha", "legacy_patch_sha256", "registration_patch_sha256", "fixture_sha256", "runtime_version"]:
        require(report.get(key) == identity[key], "Native source identity mismatch: " + key)
    require(report.get("account_root") == str(account_root) and report.get("state_sha256") == state_hash,
            "Different account path or original state")
    for key, state_key in {"account_id": "AccountID", "space_id": "SpaceID", "document_id": "DocumentID",
                           "block_id": "BlockID", "private_root_id": "RootID"}.items():
        require(report.get(key) == state[state_key], "Different original native identity: " + key)
    require(report.get("raw_changes_sha256") == state["RawChanges"] and report.get("heads") == state["Heads"],
            "Signed private history changed or disappeared")
    require(all(report.get(key) is True for key in ["account_stop_verified", "closed", "test_passed"]),
            "Native account was not stopped and test did not pass")
    require(report.get("app_capability") == "OFF" and report.get("two_app_clients") == "NOT_RUN"
            and report.get("ios_acceptance") == "NOT_RUN", "Receipt overstates App acceptance")
    observation = report.get("runtime_observation", {})
    if role == "new":
        require(observation == {"private_registry": "ACTUAL_NATIVE_FACTORY", "private_read": "EXACT_PERSISTED_CLAIM",
                                "idempotent_retry": "already_exists_same_payload", "operation_sha256": state["OperationSHA256"],
                                "claim_id": state["ClaimID"], "signed_change_id": state["ChangeID"], "private_type": 0x504B0001},
                "New native host did not recover exact private history")
    else:
        require(observation == {"private_registry": "UNKNOWN_CHANGE_TYPE_REJECTED", "private_read": "NOT_AVAILABLE_ON_LEGACY"},
                "Legacy runtime recognized or claimed the unavailable private host")
    visible = report.get("visibility", {})
    require(visible.get("ordinary_name") == VISIBLE + (" edited by legacy" if phase in {"legacy-edit", "new-recover"} else ""),
            "Ordinary native edit was not preserved")
    require(visible.get("block_sha256") == hashlib.sha256((state["BlockID"] + "\0" + VISIBLE).encode()).hexdigest(),
            "Original native block changed")
    require(visible.get("ordinary_fulltext_control") == "PASS" and visible.get("private_search") == "ABSENT"
            and visible.get("private_show") == "REJECTED" and visible.get("private_export") == "REJECTED_JSON_AND_PROTOBUF",
            "Actual native search/show/export boundary incomplete")
    require(set(visible.get("exports", {})) == EXPORTS
            and all(re.fullmatch(r"[0-9a-f]{64}", value) for value in visible["exports"].values()),
            "Both actual native exports required")
    require(report.get("cleanup") == ("TARGET_ORPHAN_PRESERVED_THEN_SPACE_AND_PROJECTION_REMOVED"
                                       if phase == "new-recover" else "NOT_REQUESTED_IN_THIS_PHASE"),
            "Native target/Space cleanup not proven")
    calls = report.get("rpc_calls", {})
    require(all(isinstance(key, str) and type(value) is int and value > 0 for key, value in calls.items()),
            "Invalid native RPC counters")
    require(set(calls) <= {"InitialSetParameters", "AppGetVersion", "WorkspaceOpen", "AccountStop", "AppShutdown",
                          "ObjectExport", "ObjectShow", "ObjectSearch", "WalletCreate", "AccountCreate",
                          "WorkspaceCreate", "ObjectCreate", "BlockCreate", "WalletRecover", "AccountSelect",
                          "AccountMigrate", "ObjectSetDetails", "BlockListDelete", "SpaceDelete"},
            "Unexpected native RPC outside the disposable lifecycle")
    for key, count in {"InitialSetParameters": 1, "AppGetVersion": 1, "WorkspaceOpen": 1,
                       "AccountStop": 1, "AppShutdown": 1, "ObjectExport": 4}.items():
        require(calls.get(key) == count, "Required native RPC count differs: " + key)
    require(calls.get("ObjectShow", 0) == 2 and calls.get("ObjectSearch", 0) >= 4, "Native live visibility controls missing")
    if phase == "new-create":
        require(all(calls.get(key) == 1 for key in ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate"])
                and all(calls.get(key, 0) == 0 for key in ["WalletRecover", "AccountSelect", "AccountMigrate"]),
                "Exactly one initial native account, Space and target required")
    else:
        require(calls.get("WalletRecover") == 1 and calls.get("AccountSelect") in {1, 2}
                and calls.get("AccountMigrate", 0) == calls["AccountSelect"] - 1, "Existing native account was not reopened")
        require(all(calls.get(key, 0) == 0 for key in ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate", "BlockCreate"]),
                "Later phase recreated account, Space, document or block")
    require(calls.get("ObjectSetDetails", 0) == (1 if phase == "legacy-edit" else 0), "Unexpected ordinary write")
    require(calls.get("BlockListDelete", 0) == calls.get("SpaceDelete", 0) == (1 if phase == "new-recover" else 0),
            "Unexpected or missing lifecycle deletion")


def validate_test_log(path: Path) -> None:
    output = path.read_text(encoding="utf-8", errors="replace")
    require(("--- PASS: " + METHOD + " ") in output and output.count("--- PASS:") == 1
            and "--- SKIP:" not in output and "--- FAIL:" not in output,
            "Missing exact named native PASS, or unexpected skip/failure")


def preserve_account_evidence(work: Path, destination: Path) -> dict:
    """Export only selected synthetic files; never the wallet or account store."""
    require(not destination.exists(), "Fresh evidence destination required")
    candidates = [work / "ownership.json", work / "result.json"]
    secrets_path = work / "sensitive-needles.private"
    if secrets_path.is_file() and not secrets_path.is_symlink():
        secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
        require(len(secrets) == 2 and all(isinstance(value, str) and value for value in secrets), "Incomplete secret inventory")
        needles = [value.encode() for value in secrets]
        candidates += [work / "state.json"]
        for phase, _ in PHASES:
            candidates += [work / (phase + suffix) for suffix in [".json", ".log"]]
            candidates += [work / "exports" / phase / name for name in sorted(EXPORTS)]
    else:
        needles = []  # No unverified native output may be uploaded after an early wallet failure.
    existing = [path for path in candidates if path.exists()]
    for path in existing:
        require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(work), "Unsafe evidence path")
        data = path.read_bytes()
        require(not any(needle in data for needle in needles), "Sensitive synthetic material detected; evidence withheld")
    destination.mkdir(parents=True, mode=0o755)
    destination.chmod(0o755)
    files = {}
    for path in existing:
        target = destination / path.relative_to(work)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        parent = target.parent
        while parent != destination:
            parent.chmod(0o755)
            parent = parent.parent
        shutil.copyfile(path, target)
        target.chmod(0o644)
        files[path.relative_to(work).as_posix()] = digest(target)
    return {"secret_scan": "PASS" if needles else "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY", "files_sha256": files}


def run_sequence(identities: dict, registration_hash: str, work: Path, evidence: Path) -> dict:
    work.mkdir(mode=0o700, exist_ok=False)
    owner = {"protocol": PROTOCOL, "nonce": str(uuid4()), "synthetic_only": True}
    write_json(work / "ownership.json", owner)
    root = work / "account-root"
    root.mkdir(mode=0o700)
    receipt = {"status": "FAIL", "scope": SCOPE, "started_at": datetime.now(timezone.utc).isoformat(),
               "app_capability": "OFF", "two_app_clients": "NOT_RUN", "ios_acceptance": "NOT_RUN", "phase_reports": []}
    write_json(work / "result.json", receipt)
    state_hash, key_hash, pids = None, None, set()
    try:
        for phase, role in PHASES:
            require(shutil.disk_usage(work).free >= RESERVE, "Disk reserve below 8 GiB")
            identity = identities[role]
            verify_binary(role, identity, registration_hash)
            nonce, path = str(uuid4()), work / (phase + ".json")
            env = dict(os.environ, PINKHA_T2_ACCOUNT_PHASE=phase, PINKHA_T2_ACCOUNT_ROLE=role,
                       PINKHA_T2_ACCOUNT_ROOT=str(root), PINKHA_T2_ACCOUNT_REPORT=str(path), PINKHA_T2_ACCOUNT_NONCE=nonce,
                       PINKHA_T2_ACCOUNT_FIXTURE_SHA=identity["fixture_sha256"],
                       PINKHA_T2_ACCOUNT_REGISTRATION_SHA=identity["registration_patch_sha256"],
                       PINKHA_T2_ACCOUNT_OWNER_TOKEN=(work / "ownership.json").read_text(), GOMAXPROCS="2")
            log = work / (phase + ".log")
            pid = run_process([identity["binary"], "-test.run", "^" + METHOD + "$", "-test.count=1", "-test.v", "-test.timeout=300s"],
                              work, env, log, 330)
            require(pid not in pids, "Distinct process required per account phase")
            pids.add(pid)
            validate_test_log(log)
            state_path, key_path = work / "state.json", work / "account-key.private"
            require(key_path.is_file() and key_path.stat().st_size > 0 and key_path.stat().st_mode & 0o077 == 0,
                    "Synthetic account key must remain private")
            state = json.loads(state_path.read_text())
            if state_hash is None:
                state_hash, key_hash = digest(state_path), digest(key_path)
            require(digest(state_path) == state_hash and digest(key_path) == key_hash, "Original account state/key was replaced")
            report = json.loads(path.read_text())
            validate_phase(report, phase, role, identity, nonce, root, pid, state, state_hash)
            for name, expected in report["visibility"]["exports"].items():
                file = work / "exports" / phase / name
                require(digest(file) == expected, "Actual native export missing or changed")
                require(all(value.encode() not in file.read_bytes() for value in [PRIVATE, state["RootID"], state["ClaimID"], state["OperationID"]]),
                        "Private journal leaked into ordinary export")
            receipt["phase_reports"].append(report)
            write_json(work / "result.json", receipt)
        receipt.update(status=PASS, actual_counts={"binaries": 2, "native_processes": 4, "passing_test_invocations": 4, "actual_export_files": 8})
        return receipt
    except BaseException as exc:
        receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error=type(exc).__name__)
        raise
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(work / "result.json", receipt)
        preserved = preserve_account_evidence(work, evidence / "account-sequence")
        write_json(evidence / "evidence-copy.json", preserved)


def execute(args: argparse.Namespace, receipt: dict) -> dict:
    require(os.name == "posix" and sys.platform == "linux", "Native account builds require Linux CI")
    control = Path(__file__).resolve().parents[2]
    tools_root = Path(__file__).resolve().parent
    source, work, evidence = args.approved_source.resolve(), args.work.resolve(), args.evidence.resolve()
    hearts = {"legacy": args.heart_legacy.resolve(), "new": args.heart_new.resolve()}
    require(len({control, source, work, evidence, *hearts.values()}) == 6, "Separate source/native/work/evidence paths required")
    require(re.fullmatch(r"[0-9a-f]{40}", args.expected_app_sha) is not None, "Exact app source SHA required")
    for root, pin in [(control, args.expected_app_sha), (source, APPROVED_SOURCE)]:
        require(git(root, "rev-parse", "HEAD") == pin and not git(root, "status", "--porcelain"), "Exact clean source required")
    work.mkdir(parents=True, exist_ok=False)
    require(shutil.disk_usage(work).free >= RESERVE, "Disk reserve below 8 GiB")
    version = subprocess.check_output(["go", "version"], text=True).strip()
    require(version == "go version go1.26.5 linux/amd64", "Exact Linux Go 1.26.5 required")
    approval = source / APPROVAL
    old_patch, old_inventory = approval / "native-heart-integration.patch", approval / "native-heart-integration.json"
    require(digest(old_patch) == LEGACY_PATCH and digest(old_inventory) == LEGACY_INVENTORY
            and digest(source / BUILDER) == BUILDER_SHA, "Immutable r14/builder source differs")
    old = json.loads(old_inventory.read_text())
    registration_path, patch = tools_root / "heart-registration.json", tools_root / "heart-registration.patch"
    registration = json.loads(registration_path.read_text())
    registration_hash = digest(patch)
    require(registration_hash == registration["patch_sha256"], "T2 registration patch differs from source inventory")
    old_expected, new_expected = composition(old, registration)
    expected = {"legacy": old_expected, "new": new_expected}
    fixture_sha, fixture_hashes = fixture_identity(tools_root / "account_lifecycle")
    receipt.update(app_sha=args.expected_app_sha, approved_source=APPROVED_SOURCE, heart_sha=HEART,
                   legacy_patch_sha256=LEGACY_PATCH, registration_patch_sha256=registration_hash,
                   registration_inventory_sha256=digest(registration_path), fixture_sha256=fixture_sha,
                   fixture_hashes=fixture_hashes, go_version=version, image_expected=closure.IMAGE,
                   composition_paths={role: sorted(value) for role, value in expected.items()})
    spec = importlib.util.spec_from_file_location("t2_account_pinned_builder", source / BUILDER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    builds, identities = {}, {}
    for role, heart in hearts.items():
        role_work = work / ("build-" + role)
        role_work.mkdir()
        builds[role] = apply_composition(heart, old_patch, patch, tools_root / "overlay", registration, expected[role], role)
        native = helper.fetch_tantivy(heart, "linux-amd64-musl")
        require(native["archive_sha256"] == closure.TANTIVY_SHA, "Wrong Tantivy archive")
        gowork = role_work / "go.work"
        gowork.write_text("go 1.26.5\n\nuse " + str(heart) + "\n\nreplace " + closure.GENPROTO_PATH + " => "
                         + closure.GENPROTO_PATH + " " + closure.GENPROTO_VERSION + "\n", encoding="utf-8")
        env = dict(os.environ, GOWORK=str(gowork), GOTOOLCHAIN="local", CGO_ENABLED="1", GOMAXPROCS="2",
                   GOMEMLIMIT="2048MiB", GOFLAGS="-mod=readonly", CGO_LDFLAGS="-L" + str(heart / "deps/libs/linux-amd64-musl"))
        def run(command: list[str], name: str, timeout: int = 900) -> None:
            receipt["commands"].append({"name": role + "-" + name, "argv": command, "cwd": str(heart)})
            write_json(evidence / "receipt.json", receipt)
            run_process(command, heart, env, evidence / (role + "-" + name + ".log"), timeout)
        run(["go", "mod", "download"], "pinned-module-download")
        env["GOPROXY"] = "off"
        run(["go", "list", "-m", "-json", closure.GENPROTO_PATH], "genproto-selection")
        selected = json.loads((evidence / (role + "-genproto-selection.log")).read_text())
        effective = selected.get("Replace", selected)
        require(selected.get("Path") == effective.get("Path") == closure.GENPROTO_PATH
                and effective.get("Version") == closure.GENPROTO_VERSION and effective.get("Sum") == closure.GENPROTO_SUM
                and effective.get("GoModSum") == closure.GENPROTO_MOD_SUM, "Unreviewed genproto module resolution")
        overlay = role_work / "overlay.json"
        replacements = {}
        for name in ["account_phase_test.go", role + "_runtime_test.go"]:
            target = heart / "clientlibrary/service" / ("pinkha_t2_" + name)
            require(not target.exists(), "Account fixture would replace native production/test source")
            replacements[str(target)] = str(tools_root / "account_lifecycle" / name)
        write_json(overlay, {"Replace": replacements})
        summary = runtime_version(role, registration_hash)
        linked_registration = registration_hash if role == "new" else "none"
        flags = ("-extldflags=-static -X github.com/anyproto/anytype-heart/util/vcs.GitCommit=" + HEART
                 + " -X github.com/anyproto/anytype-heart/util/vcs.GitSummary=" + summary
                 + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountFixtureSHA=" + fixture_sha
                 + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRuntimeRole=" + role
                 + " -X github.com/anyproto/anytype-heart/clientlibrary/service.t2AccountRegistrationSHA=" + linked_registration)
        binary = role_work / ("pinkha-t2-" + role + ".test")
        run(["go", "test", "-c", "-p", "1", "-tags", TAGS, "-overlay", str(overlay), "-ldflags", flags,
             "-o", str(binary), "./clientlibrary/service"], "compile")
        identity = {"role": role, "heart_sha": HEART, "legacy_patch_sha256": LEGACY_PATCH,
                    "registration_patch_sha256": linked_registration, "fixture_sha256": fixture_sha,
                    "runtime_version": summary, "binary": str(binary), "binary_sha256": digest(binary)}
        verify_binary(role, identity, registration_hash)
        require(verify_source(heart, expected[role], builds[role]["module_hashes"]) == builds[role]["source_hashes"],
                "Native composition changed during compile")
        identities[role] = identity
        write_json(evidence / (role + "-build.json"), {**identity, **builds[role], "tantivy": native,
                                                      "genproto": effective, "overlay": replacements})
    require(identities["legacy"]["binary_sha256"] != identities["new"]["binary_sha256"], "Two distinct native runtimes required")
    receipt["status"] = "RUNNING_NATIVE_ACCOUNT_SEQUENCE"
    write_json(evidence / "receipt.json", receipt)
    sequence = run_sequence(identities, registration_hash, work / "account-sequence", evidence)
    for role, heart in hearts.items():
        verify_binary(role, identities[role], registration_hash)
        require(verify_source(heart, expected[role], builds[role]["module_hashes"]) == builds[role]["source_hashes"],
                "Native source changed during account sequence")
    require(fixture_identity(tools_root / "account_lifecycle") == (fixture_sha, fixture_hashes), "Account fixture changed during execution")
    require(git(control, "rev-parse", "HEAD") == args.expected_app_sha and not git(control, "status", "--porcelain")
            and git(source, "rev-parse", "HEAD") == APPROVED_SOURCE and not git(source, "status", "--porcelain"),
            "Control or immutable source changed during execution")
    return {"status": PASS, "actual_counts": sequence["actual_counts"], "identities": identities,
            "account_receipt_sha256": digest(evidence / "account-sequence/result.json"),
            "private_account_lifecycle": "PASS_SAME_ACCOUNT_FOUR_PROCESSES", "unknown_client_preservation": "PASS_R14_PRIVATE_HISTORY_BYTES",
            "search_export_cleanup": "PASS_NATIVE_RPC_AND_EXISTING_CLEANUP", "full_t2_acceptance": "NOT_RUN"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(__doc__)
    for name in ["approved-source", "heart-legacy", "heart-new", "work", "evidence"]:
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args(argv)
    os.umask(0o077)
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    evidence.chmod(0o755)
    require(not (evidence / "receipt.json").exists(), "Fresh lifecycle evidence required")
    receipt = {"status": "NOT_RUN_PREFLIGHT", "scope": SCOPE, "run_id": os.environ.get("GITHUB_RUN_ID"),
               "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"), "workflow_ref": os.environ.get("GITHUB_WORKFLOW_REF"),
               "app_sha_expected": args.expected_app_sha, "app_capability": "OFF", "two_app_clients": "NOT_RUN",
               "ios_acceptance": "NOT_RUN", "full_t2_acceptance": "NOT_RUN", "commands": [],
               "started_at": datetime.now(timezone.utc).isoformat()}
    code = 1
    try:
        receipt.update(execute(args, receipt))
        code = 0
    except BaseException as exc:
        receipt.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "FAIL", error=type(exc).__name__)
        # Build/control errors contain only controller-defined labels. Native
        # phase stdout and wallet state remain in the separate private workspace.
        print(type(exc).__name__ + ": " + str(exc), file=sys.stderr)
    finally:
        receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
        write_json(evidence / "receipt.json", receipt)
        for file in evidence.rglob("*"):
            if file.is_dir():
                file.chmod(0o755)
            elif file.is_file() and not file.is_symlink():
                file.chmod(0o644)
    print(json.dumps({key: receipt.get(key) for key in ["status", "run_id", "app_sha_expected", "actual_counts", "app_capability", "two_app_clients"]}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
