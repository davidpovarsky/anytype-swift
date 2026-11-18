"""Four actual native RPC processes on one disposable account, with real exports.

The preserved component-store controller is reused only for POSIX process-group
isolation and pinned source constants. Its fixture, protocol, and assertions are
not modified. This route does not prove Apple packaged-app or Swift fallback.
"""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from uuid import uuid4

_shared_path = Path(__file__).resolve().parents[1] / "compatibility_pairs/run_pairs.py"
_spec = importlib.util.spec_from_file_location("preserved_account_pair_process", _shared_path)
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)

PROTOCOL = "pinkha-t5-account-pair-v1"
METHOD = "TestT5AccountCompatibilityPairPhase"
FIXTURE = Path(__file__).with_name("account_pair_phase_test.go")
PHASES = shared.PHASES
DISABLED = "DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF"
STATUS = "NATIVE_ACCOUNT_PAIR_PASS"
SCOPE = "two exact Linux native RPC binaries; four processes reopen one synthetic account with real JSON/Protobuf exports; Apple and Swift pairing NOT_RUN"
EXPORT_NAMES = {name + "." + extension for name in ["document", "block", "quote"]
                for extension in ["pbc", "json"]}
require = shared.require
digest = shared.digest


def runtime_version(role):
    version = "v0.51.7-nightly.20261014.1-pinkha-native-derived-v1-" + shared.PATCHES[role]
    if role == "new":
        version += "-pinkha-native-t5-lookup-v1-" + shared.PATCHES[role]
    return version


def verify_artifact(role, entry):
    require(role in ["old", "new"], "Unknown native revision role")
    require(all(Path(entry[key]).is_absolute() for key in ["binary", "source", "inventory", "patch"]),
            "Absolute artifact/source paths required")
    binary = Path(entry["binary"]).resolve(strict=True)
    source = Path(entry["source"]).resolve(strict=True)
    inventory_path = Path(entry["inventory"]).resolve(strict=True)
    patch = Path(entry["patch"]).resolve(strict=True)
    require(digest(inventory_path, True) == shared.INVENTORIES[role], "Wrong immutable inventory")
    inventory = json.loads(inventory_path.read_text(encoding="utf8"))
    require(inventory["heart_sha"] == shared.PIN
            and inventory["patch_sha256"] == shared.PATCHES[role], "Wrong revision inventory")
    require(digest(patch, True) == shared.PATCHES[role], "Wrong patch bytes")
    require(shared.git(source, "rev-parse", "HEAD") == shared.PIN, "Wrong native source HEAD")
    require(digest(binary) == entry["binary_sha256"], "Wrong native binary bytes")
    with binary.open("rb") as stream:
        require(stream.read(6) == b"\x7fELF\x02\x01", "Actual 64-bit little-endian ELF binary required")
    fixture_sha = digest(FIXTURE, True)
    require(entry["fixture_sha256"] == fixture_sha, "Wrong account fixture source")
    marker = "pinkha-native-derived-v1-" + shared.PATCHES[role]
    feature = "pinkha-native-t5-lookup-v1-" + shared.PATCHES["new"]
    require(all(shared.contains(binary, value) for value in [marker, fixture_sha, PROTOCOL, METHOD]),
            "Missing hash-bound native/fixture markers")
    require(shared.contains(binary, feature) == (role == "new"), "Wrong separate runtime marker")
    capability = inventory.get("features", {}).get("t5_related_lookup", 0)
    require(capability == (1 if role == "new" else 0), "Wrong source capability")
    source_hashes = {}
    for item in inventory["files"]:
        relative = Path(item["path"])
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe inventory path")
        target = (source / relative).resolve(strict=True)
        require(target.is_relative_to(source), "Inventory escaped native checkout")
        actual = digest(target, True)
        require(actual == item["after_sha256"], "Native source differs: " + item["path"])
        source_hashes[item["path"]] = actual
    changed = set(shared.git(source, "diff", "--name-only", "HEAD").splitlines())
    untracked = set(shared.git(source, "ls-files", "--others", "--exclude-standard").splitlines())
    require((changed | untracked).issubset(source_hashes), "Unexpected native source outside inventory")
    return dict(binary=str(binary), binary_sha256=entry["binary_sha256"], source=str(source),
                heart_sha=shared.PIN, patch_sha256=shared.PATCHES[role], fixture_sha256=fixture_sha,
                inventory_sha256=digest(inventory_path, True), source_hashes=source_hashes,
                runtime_capability=capability, runtime_version=runtime_version(role))


def validate_state(state):
    for key in ["AccountID", "SpaceID", "ManifestID", "ManifestRaw", "CanonicalKey"]:
        require(isinstance(state.get(key), str) and state[key], "Missing original account state: " + key)
    require(Path(state["AccountID"]).name == state["AccountID"], "Unsafe account directory identity")
    documents = state.get("Documents", [])
    require(len(documents) == 3, "Three original document/block/sourceQuote records required")
    ids = [document.get("ID") for document in documents]
    require(all(isinstance(value, str) and value for value in ids)
            and len(set(ids + [state["ManifestID"]])) == 4, "Distinct actual object identities required")
    require(documents[0].get("BlockID") == ""
            and all(document.get("BlockID") for document in documents[1:])
            and documents[1]["BlockID"] != documents[2]["BlockID"], "Two original actual block identities required")
    for index, document in enumerate(documents):
        raw = json.loads(document["Canonical"])
        records = raw.get("records", [])
        require(raw.get("version") == 2 and raw.get("unknownRoot") == "preserve" and len(records) == 1,
                "Missing canonical/unknown-field sentinel")
        record = records[0]
        require(record.get("spaceId") == state["SpaceID"] and record.get("objectId") == document["ID"]
                and record.get("blockId", "") == document["BlockID"], "Canonical target identity differs")
        require(record.get("unknownRecord") == {"preserve": "unchanged"}
                and record.get("item", {}).get("unknownItem") == "preserve", "Missing unknown-field sentinels")
        require(record["item"].get("role") == ("sourceQuote" if index == 2 else "context")
                and record["item"].get("canonicalKey") == "Genesis 3:3", "Wrong canonical test case")
    return documents


def validate_phase(report, phase, role, identity, nonce, account_root, pid, state, state_sha, baseline):
    require(report.get("protocol") == PROTOCOL and report.get("phase") == phase, "Wrong phase/protocol")
    require(report.get("nonce") == nonce and report.get("pid") == pid, "Stale or foreign process report")
    for key in ["heart_sha", "patch_sha256", "fixture_sha256", "runtime_version"]:
        require(report.get(key) == identity[key], "Native identity mismatch: " + key)
    require(report.get("account_root") == str(account_root)
            and report.get("account_id") == state["AccountID"]
            and report.get("space_id") == state["SpaceID"]
            and report.get("state_sha256") == state_sha, "Different account, Space, or original state")
    require(report.get("closed") is True and report.get("test_passed") is True, "Native app/test not closed/passed")
    require(report.get("export_status") == "ACTUAL_JSON_AND_PROTOBUF", "Actual native exports not proven")
    require(report.get("swift_pairing_status") == "NOT_RUN" and report.get("client_enablement") == DISABLED,
            "Native receipt overstates Swift/client enablement")
    documents = validate_state(state)
    ids = {document["ID"] for document in documents}
    canonical = report.get("canonical_sha256", {})
    public = report.get("public_sha256", {})
    blocks = report.get("block_sha256", {})
    exports = report.get("exports", {})
    require(set(canonical) == ids | {state["ManifestID"]} and set(public) == ids,
            "Missing actual canonical/public sentinels")
    require(set(blocks) == {document["ID"] for document in documents[1:]}, "Missing actual block sentinels")
    require(set(exports) == EXPORT_NAMES, "Six actual native exports required per process")
    hashes = [value for mapping in [canonical, public, blocks, exports] for value in mapping.values()]
    require(all(isinstance(value, str) and len(value) == 64
                and set(value) <= set("0123456789abcdef") for value in hashes), "Invalid content digest")
    if baseline:
        require(all(report[key] == baseline[key] for key in
                    ["account_id", "space_id", "state_sha256", "canonical_sha256", "public_sha256", "block_sha256"]),
                "Original account, canonical data, public projection, or actual blocks changed")
    expected_names = {document["ID"]: document["Name"] for document in documents}
    if phase in ["old-edit", "new-recover"]:
        expected_names[documents[0]["ID"]] = "T5 ordinary title edited by r14"
    require(report.get("ordinary_names") == expected_names, "Ordinary old-runtime edit did not survive")
    require(report.get("public_members") == [documents[0]["ID"]], "Public document-only query widened")
    versions = report.get("private_versions", {})
    require(set(versions) == ids and all(type(value) is int for value in versions.values()),
            "Missing observed private versions")
    if role == "new":
        require(all(value == 1 for value in versions.values())
                and report.get("private_query_status") == "EXECUTED"
                and report.get("private_members") == sorted(ids), "New native lookup failed to recover all targets")
    else:
        require(report.get("private_query_status") == "NOT_ATTEMPTED_RUNTIME_UNAVAILABLE"
                and report.get("private_members") == [], "Old runtime attempted/claimed unavailable private lookup")
    calls = report.get("rpc_calls", {})
    require(all(isinstance(key, str) and type(value) is int and value > 0 for key, value in calls.items()),
            "Invalid actual RPC counters")
    for key, count in {"InitialSetParameters": 1, "AppGetVersion": 1, "AppShutdown": 1,
                       "WorkspaceOpen": 1, "ObjectExport": 6}.items():
        require(calls.get(key) == count, "Required native RPC count differs: " + key)
    require(calls.get("ObjectShow", 0) >= 4 and calls.get("ObjectSearch", 0) >= (2 if role == "new" else 1),
            "Actual live reads/searches not observed")
    if phase == "old-create":
        require(calls.get("WalletCreate") == 1 and calls.get("AccountCreate") == 1
                and calls.get("WorkspaceCreate") == 1 and calls.get("WorkspaceObjectListAdd") == 1
                and calls.get("BlockCreate") == 2
                and calls.get("ObjectCreate") == 4
                and calls.get("WalletRecover", 0) == 0 and calls.get("AccountSelect", 0) == 0,
                "Initial account creation contract differs")
    else:
        require(calls.get("WalletRecover") == 1 and calls.get("AccountSelect") in [1, 2]
                and calls.get("AccountMigrate", 0) == calls["AccountSelect"] - 1,
                "Exact existing account was not selected through native RPC")
        require(all(calls.get(key, 0) == 0 for key in
                    ["WalletCreate", "AccountCreate", "WorkspaceCreate", "ObjectCreate",
                     "BlockCreate", "ObjectCreateRelation", "ObjectCreateObjectType", "WorkspaceObjectListAdd"]),
                "Later phase recreated the account, Space, object, or block")
        require(calls.get("ObjectSetDetails", 0) == (1 if phase == "old-edit" else 0),
                "Later phase made an unexpected fixture write")


def preserve_evidence(workspace, destination):
    """Copy only explicit nonsensitive evidence, after checking every candidate."""
    require(not destination.exists(), "Fresh evidence destination required")
    needles_path = workspace / "sensitive-needles.private"
    candidates = [workspace / name for name in ["ownership.json", "result.json"]]
    if needles_path.is_file():
        needles = json.loads(needles_path.read_text(encoding="utf8"))
        require(len(needles) == 2 and all(isinstance(value, str) and value for value in needles),
                "Synthetic secret guard is incomplete")
        needles = [value.encode() for value in needles]
        candidates += [workspace / "state.json"]
        for phase, _ in PHASES:
            candidates += [workspace / (phase + extension) for extension in [".json", ".log"]]
            candidates += [workspace / "exports" / phase / name for name in sorted(EXPORT_NAMES)]
    else:
        # An early wallet failure has no safe secret inventory: retain the
        # controller result, but do not upload the unverified native output.
        needles = []
    existing = [path for path in candidates if path.is_file()]
    for path in existing:
        require(not path.is_symlink() and path.resolve().is_relative_to(workspace.resolve()),
                "Evidence escaped the disposable workspace")
        data = path.read_bytes()
        require(not any(needle in data for needle in needles),
                "Sensitive synthetic material found; native evidence withheld")
    destination.mkdir(parents=True, mode=0o755)
    destination.chmod(0o755)
    for path in existing:
        target = destination / path.relative_to(workspace)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        current = target.parent
        while current != destination:
            current.chmod(0o755)
            current = current.parent
        shutil.copyfile(path, target)
        target.chmod(0o644)
    return dict(secret_scan_status="PASS" if needles else "NATIVE_OUTPUT_WITHHELD_NO_SECRET_INVENTORY",
                copied_files=sorted(str(path.relative_to(workspace)) for path in existing))


def execute(manifest, workspace):
    require(os.name == "posix", "Actual account pairing requires the POSIX CI lane")
    config = json.loads(manifest.read_text(encoding="utf8"))
    require(config.get("schema") == 1 and config.get("protocol") == PROTOCOL, "Wrong native account-pair manifest")
    identities = {role: verify_artifact(role, config[role]) for role in ["old", "new"]}
    require(identities["old"]["binary"] != identities["new"]["binary"], "Two distinct exact native binaries required")
    root = (workspace / "account-root").resolve()
    root.mkdir(mode=0o700)
    reports, pids = [], set()
    state_sha, key_sha = None, None
    for phase, role in PHASES:
        require(shutil.disk_usage(workspace).free >= shared.RESERVE, "Disk reserve below 8 GiB")
        current = verify_artifact(role, config[role])
        require(current == identities[role], "Native artifact/source changed during pairing")
        nonce, report_path = str(uuid4()), workspace / (phase + ".json")
        env = dict(os.environ, PINKHA_ACCOUNT_PAIR_ROOT=str(root),
                   PINKHA_ACCOUNT_PAIR_REPORT=str(report_path), PINKHA_ACCOUNT_PAIR_PHASE=phase,
                   PINKHA_ACCOUNT_PAIR_ROLE=role, PINKHA_ACCOUNT_PAIR_NONCE=nonce,
                   PINKHA_ACCOUNT_PAIR_FIXTURE_SHA=current["fixture_sha256"],
                   PINKHA_ACCOUNT_PAIR_PATCH_SHA=current["patch_sha256"],
                   PINKHA_ACCOUNT_PAIR_OWNER_TOKEN=(workspace / "ownership.json").read_text(encoding="utf8"))
        command = [current["binary"], "-test.run", "^" + METHOD + "$",
                   "-test.count=1", "-test.v", "-test.timeout=300s"]
        log = workspace / (phase + ".log")
        pid = shared.run_process(command, env, log, workspace, deadline=330)
        require(pid not in pids, "Distinct native process required for every phase")
        pids.add(pid)
        output = log.read_text(encoding="utf8", errors="replace")
        require(("--- PASS: " + METHOD + " ") in output and output.count("--- PASS:") == 1
                and "--- SKIP:" not in output and "--- FAIL:" not in output,
                "Missing named passing native test or unexpected skip/failure")
        state_path, key_path = workspace / "state.json", workspace / "account-key.private"
        state = json.loads(state_path.read_text(encoding="utf8"))
        require(key_path.is_file() and key_path.stat().st_size > 0
                and key_path.stat().st_mode & 0o077 == 0, "Private synthetic key handling differs")
        if state_sha is None:
            state_sha, key_sha = digest(state_path), digest(key_path)
        require(digest(state_path) == state_sha and digest(key_path) == key_sha,
                "Original account state/key was replaced between processes")
        report = json.loads(report_path.read_text(encoding="utf8"))
        validate_phase(report, phase, role, current, nonce, root, pid, state, state_sha,
                       reports[0] if reports else None)
        for name, expected in report["exports"].items():
            path = workspace / "exports" / phase / name
            require(path.is_file() and not path.is_symlink() and digest(path) == expected,
                    "Actual original export bytes missing or changed")
        reports.append(report)
    require(all(verify_artifact(role, config[role]) == identities[role] for role in identities),
            "Native inputs changed after actual account pairing")
    return dict(status=STATUS, scope=SCOPE, identities=identities, phase_reports=reports,
                actual_counts=dict(binaries=2, native_processes=4, passing_test_invocations=4,
                                   actual_export_files=24),
                export_status="ACTUAL_JSON_AND_PROTOBUF", swift_pairing_status="NOT_RUN",
                full_F10="NOT_PROVEN", client_enablement=DISABLED)


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args(argv)
    os.umask(0o077)
    workspace = args.workspace.resolve()
    workspace.mkdir(parents=False, exist_ok=False, mode=0o700)
    owner = dict(protocol=PROTOCOL, run_id=str(uuid4()), synthetic_only=True)
    (workspace / "ownership.json").write_text(json.dumps(owner), encoding="utf8")
    receipt = dict(status="FAIL", reason="ATTEMPT_NOT_COMPLETED", scope=SCOPE,
                   started_at=datetime.now(timezone.utc).isoformat(), full_F10="NOT_PROVEN",
                   client_enablement=DISABLED, swift_pairing_status="NOT_RUN", **owner)
    result_path = workspace / "result.json"
    result_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf8")
    try:
        receipt.update(execute(args.manifest.resolve(strict=True), workspace))
        receipt["reason"] = "ACTUAL_ACCOUNT_SEQUENCE_COMPLETED"
    except Exception as error:
        receipt.update(status="FAIL", reason=type(error).__name__, error=str(error))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    result_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf8")
    print(json.dumps({key: value for key, value in receipt.items() if key not in ["identities", "phase_reports"]}))
    return 0 if receipt["status"] == STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
