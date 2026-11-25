#!/usr/bin/env python3
"""Actual source review in the current unified Heart app after a sealed E handoff.

Update only the explicitly delegated existing account to the already qualified
App containing the opt-in closed observer. Retain complete pre/post account data
and the unchanged original fixture deadline. No account factory, source write,
engine switch, native test hook or build. The production UI owns both captures.
"""
from __future__ import annotations
import collections
import importlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import struct
import sys
import time
import traceback

sys.dont_write_bytecode = True
CONTROL = Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125/control-current5ffff")
CONTROL_SHA = "ad30f682471c585ac4dcaa7a521b4f00ad607fdecbe2197fdd61b3b9518150c2"
ADMISSION_SHA = "7bb0a565c6ad33cd9febdbd031d95da5162ad7e0451eea090d9cde052489d44e"
RETAINER_SHA = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
SELECTOR = "PinkhaStage1AcceptanceUITests/HeartSourceCaptureAcceptanceUITests/testActualHeartSourceReviewCloseAndRecapture"
UI_SOURCE_SHA = "c180073774f184c5ca732e20675ac6b4a3ddada728c3afc45a73e4fb0b910a29"
SOURCE = "5ffff121e696044b0d1955524b7a69baf453b4b1"
ORIGINAL_SOURCE = "5c05a612e4054a4adfa7f812343be6a15871cc89"
PRIOR = Path("/Users/m1/builds/e-combined-current-20261125/sources-current5c05-continuation1")
PRIOR_EXECUTION_SHA = "4a8819b03006a4b3e383f02906209667900583aaca5f4acd193c85168fcbfe6b"
PRIOR_BACKUP_SHA = "cb669d69c23b1b3789e642dfb721c2b4c5fcbd7f81c37088ebc55e251cc405c0"
PRIOR_DEVICE_PLIST_SHA = "29b2b65776b2f845f215dac20ddb3e35c02831ded9a647a33bfe64dda8033830"
CONTAINER_LOG_SHA = "d822bcff03d82c6d8ca6466995511f48ccec98b8e044fc7bb74714d670d33cf5"
CONTAINER_COMMAND_SHA = "a3a00005c271b94a814319a2d01ff5f12ca5dbbe90a94e7b8c77571f101c98db"
FIXTURE_SHA = "88464564e7d61c19c4d56961619b99116b29b6005bbd09d12053300943e0252f"
DEVICE = "9D025DE0-C487-49D9-9CFD-18B2574866FE"
BINDING = {"nonce":"57199972b6ea418d8b092cf653d7ad09","runAttempt":"1",
           "runID":"1795625392587749","sourceSHA":ORIGINAL_SOURCE}
DEADLINE = 1795632714.594939
PREPARATION = Path("/Users/m1/builds/e-combined-current-20261125/fresh-current5c05-attempt1")
PREPARATION_EXECUTION_SHA = "e6269f02d2c03dfbe7f1c519c812b762f1aa14a564d91583d472edd9ac732422"
PREPARATION_CONTROL = CONTROL / "original_current_heart_sources.py"
PREPARATION_CONTROL_SHA = "a4435fa57c1036237a3875925d28475c7b3d544cf227afae2b7e064b78ba1b7d"
ORIGINAL_ADMISSION = Path("/Users/m1/builds/e-combined-current-20261125/control-current5c05-114855/admission5c05a6.json")
ORIGINAL_ADMISSION_SHA = "47d25adc16a85db66df3920ab2cd8e77d3759b4802d34a40110d9b0726448214"
COMPLETION_SHA = "318b46d2918f968731d96a7309d4e80cb30e3160994d13da019e2f5c9e7c78b9"
UI_BUILD = Path("/Users/m1/builds/pinkha-c-heart-source-ui-20261125/ui-observer-49c-build1")
UI_RECEIPT_SHA = "ca3b3dac29fde6781a53ec5f7ef6c09cfeaffec46a987d261b6e58006d2c9662"
UI_SOURCE_PROOF_SHA = "032ce61ef58a08a460762e797e4da288023750c9e40e44f149079535012e358e"
UI_GENERATOR_PROOF_SHA = "fae2d2e9ea4a698003ebd1186f51a469f970a1eec51df98bb24dd6d4a5985b44"
UI_PROJECT_PROOF_SHA = "8b079b121b4a2fdf9a0c8fd2cf4236166e11e4a1106fb568d530b86cedcce0bb"
UI_PRODUCTS_SHA = "3c8b2aec6e7f13e5d3a0b2ce358e35387b70138a48a71e77e3198aec806d6904"
CORRECTED_UI_COMMIT = "49c656b23f5089076df7cb2e5da15efbb395fdcb"

def load_handoff(c, path, expected):
    c.require(path.is_absolute() and path.resolve() == path
              and re.fullmatch(r"[0-9a-f]{64}", expected), "Canonical pinned handoff required")
    raw = c.raw(path, 32768)
    c.require(c.sha(raw) == expected, "Original explicit C handoff changed")
    value = c.decode(raw)
    c.require(value == {"protocol":"pinkha-current-source-observer-account-update-handoff-v1",
        "originalSourceCommit":ORIGINAL_SOURCE,"newAppSourceCommit":SOURCE,"newUISourceCommit":CORRECTED_UI_COMMIT,
        "preparationRoot":str(PREPARATION),"preparationExecutionSHA256":PREPARATION_EXECUTION_SHA,
        "executionRoot":str(PRIOR),"executionSHA256":PRIOR_EXECUTION_SHA,"backupSHA256":PRIOR_BACKUP_SHA,
        "devicePlistSHA256":PRIOR_DEVICE_PLIST_SHA,"fixtureSHA256":FIXTURE_SHA,
        "device":DEVICE,"binding":BINDING,"deadlineEpoch":DEADLINE,
        "fixtureDeadlineExtended":False,"sourceOwner":"page154_e","continuationOwner":"migration_c"},
        "Only the explicitly delegated current account/update may run")
    return expected



def load_core():
    import hashlib
    path = CONTROL / "combined_heart_semantics_current.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != CONTROL_SHA:
        raise ValueError("Exact reviewed original product admission required")
    sys.path.insert(0, str(CONTROL))
    c = importlib.import_module("combined_heart_semantics_current")
    c.require(Path(c.__file__).resolve() == path and c.digest(path) == CONTROL_SHA, "Foreign admission module")
    return c



def owned_device(c, commands, label, expected="Shutdown"):
    output, _ = commands.run(["xcrun", "simctl", "list", "devices", "--json"], label, 30, capacity=False)
    rows = [dict(row, runtime=runtime) for runtime, items in c.decode(c.raw(output))["devices"].items()
            for row in items if row.get("udid") == DEVICE]
    c.require(len(rows) == 1 and rows[0].get("state") == expected
              and rows[0].get("runtime") == c.RUNTIME and rows[0].get("deviceTypeIdentifier") == c.DEVICE
              and rows[0].get("name") == "E-Combined-Heart-" + BINDING["nonce"],
              "Exact delegated simulator identity/state changed")
    return rows[0]

def app_container(c, commands, label):
    output, _ = commands.run(["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "data"], label, 30, capacity=False)
    path = Path(c.raw(output, 4096).decode().strip())
    root = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    c.require(path.resolve() == path and path.is_dir()
              and path.parent == root / "data/Containers/Data/Application"
              and re.fullmatch(r"[0-9A-F-]{36}", path.name), "Original delegated app container required")
    return path

def sealed_app_container(c):
    # CoreSimulator refuses get_app_container while Shutdown. Admit the exact
    # successful E resolution and independently compare the full private
    # shutdown inventory before boot; resolve through simctl again after boot.
    directory = PRIOR / "commands/final-private-sandbox-container"
    c.require(c.digest(directory / "result.json") == CONTAINER_COMMAND_SHA, "Original successful container command changed")
    command = c.decode(c.raw(directory / "result.json"))
    log = directory / "original.log"
    c.require(c.digest(log) == CONTAINER_LOG_SHA
              == command["logSHA256"]
              and command["argv"] == ["xcrun", "simctl", "get_app_container", DEVICE, c.BUNDLE, "data"]
              and command["exitCode"] == 0 and command["status"] == "PASS_COMMAND",
              "Original successful delegated app-container resolution required")
    path = Path(c.raw(log, 4096).decode().strip())
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    c.require(path.resolve() == path and path.is_dir()
              and path.parent == owner / "data/Containers/Data/Application"
              and re.fullmatch(r"[0-9A-F-]{36}", path.name), "Sealed delegated container changed")
    return path

def original_preparation(c):
    c.require(c.digest(PREPARATION_CONTROL) == PREPARATION_CONTROL_SHA
              and c.digest(ORIGINAL_ADMISSION) == ORIGINAL_ADMISSION_SHA,
              "Original unchanged E setup verifier/admission required")
    spec = importlib.util.spec_from_file_location("original_current_heart_sources", PREPARATION_CONTROL)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    c.require(Path(verifier.__file__).resolve() == PREPARATION_CONTROL and verifier.c is c,
              "Original setup verifier module differs")
    # This original function independently qualifies both accepted methods from
    # original enumeration, stdout, xcresult exports, and exact failed launch.
    return verifier.admit_prior(c.decode(c.raw(ORIGINAL_ADMISSION)))


def original_handoff(c, commands, evidence):
    execution_path = PRIOR / "evidence/execution.json"
    backup_path = PRIOR / "private/owned-account-originals/retention.json"
    fixture_path = PRIOR / "private/final-sandbox-originals" / c.FIXTURE
    c.require(c.digest(execution_path) == PRIOR_EXECUTION_SHA and c.digest(backup_path) == PRIOR_BACKUP_SHA
              and c.digest(fixture_path) == FIXTURE_SHA, "Original sealed handoff bytes changed")
    execution = c.decode(c.raw(execution_path)); backup = c.decode(c.raw(backup_path))
    fixture_bytes = c.raw(fixture_path, 65536); fixture = c.decode(fixture_bytes)
    accepted = original_preparation(c)
    c.require(accepted["binding"] == execution["binding"] == BINDING
              and accepted["ownedSimulator"] == execution["ownedSimulator"] == DEVICE
              and execution["status"] == "FAIL" and execution["controllerSHA256"] == PREPARATION_CONTROL_SHA
              and execution["sourceCommit"] == ORIGINAL_SOURCE
              and execution["nativeManifestSHA256"] == c.MANIFEST and execution["heartOverlaySHA256"] == c.OVERLAY
              and execution["priorExecutionSHA256"] == PREPARATION_EXECUTION_SHA
              and execution["setupMethodsReexecuted"] == 0 and execution["fixtureRestorations"] == 0
              and execution["fixtureDeadlineChanges"] == 0
              and set(execution["stages"]) == {"linked-ui"} and execution["stages"]["linked-ui"]["status"] == "FAIL",
              "Original setup and later actual source failure remain separate")
    for original in (accepted, execution):
        c.require(original["cleanup"]["status"] == "PASS" and original["cleanup"]["errors"] == []
                  and original["cleanup"]["ownedSimulatorDeleted"] is False
                  and original["cleanup"]["ownedSimulatorRetainedForRecovery"] == DEVICE
                  and all(x.get("absentAtOriginalExit") is True for x in original["cleanup"]["groups"]),
                  "Original terminal process/retention authority required")
    c.require(backup["protocol"] == "pinkha-owned-heart-account-retention-v1"
              and backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
              and backup["executionSHA256"] == PRIOR_EXECUTION_SHA and backup["device"] == DEVICE
              and backup["fixtureDeadlineChanged"] is False and backup["restoredFixtures"] == 0,
              "Current full four-scope backup required")
    completion_path = PRIOR / "evidence/retention-completion.json"
    c.require(c.digest(completion_path) == COMPLETION_SHA, "Original final retention changed")
    completion = c.decode(c.raw(completion_path))
    c.require(completion == {"status":"PASS_PRIVATE_RETENTION_WITH_ORIGINAL_OUTCOME_PRESERVED",
        "originalExecutionSHA256":PRIOR_EXECUTION_SHA,"retentionSHA256":PRIOR_BACKUP_SHA,
        "devicePlistSHA256":PRIOR_DEVICE_PLIST_SHA,"privateAccount":backup},
        "Actual final full backup completion differs")
    for name in ("preparation", "mounted"):
        c.require(accepted["stages"][name]["command"]["exitCode"] == 0,
                  "Original accepted command must actually exit zero")
    # Retain the real subsequent source UI failure; this account has an actual
    # source association. C does not assert or restore an initial no-link state.
    failed = execution["stages"]["linked-ui"]
    failed_log = PRIOR / "commands/linked-ui-test/original.log"
    summary = c.decode(c.raw(PRIOR / "evidence/linked-ui/summary.json"))
    c.require(c.digest(failed_log) == failed["command"]["logSHA256"]
              and failed["testInvoked"] is True
              and {k:summary[k] for k in ("totalTestCount","passedTests","failedTests","skippedTests")}
              == {"totalTestCount":1,"passedTests":0,"failedTests":1,"skippedTests":0},
              "Actual original failed method may not become acceptance")
    c.require(c.raw(PREPARATION / "private" / c.FIXTURE) == fixture_bytes,
              "Original prepared fixture changed")
    capture_raw = c.raw(PREPARATION / "private" / c.CAPTURE, 65536)
    reopen_raw = c.raw(PREPARATION / "private" / c.REOPEN, 65536)
    capture, reopen = c.decode(capture_raw), c.decode(reopen_raw)
    helper = CONTROL / "combined_heart_observations_gateway.py"
    c.require(c.digest(helper) == c.OBSERVATION_HELPER, "Original native observation helper required")
    specialized = importlib.import_module("combined_heart_observations_gateway")
    c.require(Path(specialized.__file__).resolve() == helper and specialized.COMBINED_VERSION == c.VERSION
              and specialized.ORIGINAL_OVERLAY == c.OVERLAY, "Exact original native runtime required")
    mounted_proof = specialized.observations(fixture, capture, reopen, capture_raw, BINDING)
    witness = capture.get("nativeBoundaryEvidence")
    c.require(isinstance(witness,dict) and witness["protocolVersion"] == 1
              and witness["extraNativeCalls"] == 0 and witness["source"] == "actual-client-call-results"
              and set(witness["files"]) == set(c.boundary.FILES), "Original native boundaries required")
    boundaries = {}
    for role, filename in c.boundary.FILES.items():
        row = witness["files"][role]; payload = c.raw(PREPARATION / "private" / filename, c.boundary.MAXIMUM)
        c.require(row["filename"] == filename and len(payload) == row["bytes"]
                  and c.sha(payload) == row["sha256"], "Original native boundary changed")
        boundaries[role] = payload
    native_proof = c.boundary.verify(boundaries, fixture, capture, c.native, c.mounted)
    c.require(native_proof["projectionFieldCount"] == 9
              and accepted["mountedProof"] == execution["mountedProof"] == mounted_proof
              and accepted["nativeBoundaryComparison"] == execution["nativeBoundaryComparison"] == native_proof
              and accepted["finalPrivateSandbox"]["files"] == execution["finalPrivateSandbox"]["files"],
              "Original setup/native evidence changed in the later custody")
    c.mounted.fixture(fixture, BINDING)
    c.require(fixture["createdAt"] + 978307200 + 7200 == DEADLINE and time.time() < DEADLINE,
              "The exact original fixture deadline must remain unchanged")
    owned_device(c, commands, "handoff-device")
    app = sealed_app_container(c)
    old_container = PRIOR / "commands/final-private-sandbox-container/original.log"
    c.require(Path(c.raw(old_container, 4096).decode().strip()) == app, "Original app container changed")
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    sealed_plist = PRIOR / "private/owned-account-originals/device.plist"
    live_plist = device_root / "device.plist"
    c.require(c.digest(sealed_plist) == PRIOR_DEVICE_PLIST_SHA == c.digest(live_plist),
              "Actual device metadata differs from the original sealed handoff")
    def identity(path):
        row = path.lstat()
        c.require(path.resolve() == path and not stat.S_ISLNK(row.st_mode), "Original root was replaced by an alias")
        return (row.st_dev, row.st_ino, row.st_mode)
    original_identity = (identity(device_root), identity(live_plist), identity(app))
    roots = {"application-data": app, "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
             "keychains": device_root / "data/Library/Keychains", "device-preferences": device_root / "data/Library/Preferences"}
    retainer_path = CONTROL / "retain_owned_heart_account.py"
    c.require(c.digest(retainer_path) == RETAINER_SHA, "Exact original safe account retention helper required")
    retainer = importlib.import_module("retain_owned_heart_account")
    c.require(Path(retainer.__file__).resolve() == retainer_path, "Foreign account retention helper")
    scope_identities = {}
    for label, root in roots.items():
        c.require(not root.is_symlink() and (not root.exists() or root.is_dir()),
                  "Original private scope must remain a canonical directory or absent")
        scope_identities[label] = identity(root) if root.exists() else None
    current_backup = backup
    for label, root in roots.items():
        scope = current_backup["scopes"][label]
        if scope["status"] == "NOT_PRESENT":
            c.require(not root.exists() and not root.is_symlink(), "An originally absent private scope appeared")
            continue
        inventory_path = PRIOR / "private/owned-account-originals" / (label + "-before.json")
        c.require(scope["status"] == "PRESERVED_ORIGINAL_BYTES_AND_MODES"
                  and c.digest(inventory_path) == scope["manifestSHA256"]
                  and retainer.inventory(root) == c.decode(c.raw(inventory_path)),
                  "Delegated native account differs from its exact sealed original E backup")
    owned_device(c, commands, "handoff-after-inventory")
    for label, root in roots.items():
        expected_identity = scope_identities[label]
        if expected_identity is None:
            c.require(not root.exists() and not root.is_symlink(),
                      "An originally absent private scope appeared during inventory")
        else:
            c.require(root.is_dir() and identity(root) == expected_identity,
                      "An original private scope was replaced during inventory")
    c.require(c.digest(live_plist) == PRIOR_DEVICE_PLIST_SHA
              and original_identity == (identity(device_root), identity(live_plist), identity(app)),
              "Delegated device or account identity changed during inventory")
    c.require(c.digest(app / "Library/Application Support" / c.FIXTURE) == FIXTURE_SHA,
              "Live fixture differs from original handoff")
    value = {"protocol":"pinkha-current-source-observer-update-sequential-handoff-v1",
        "originalSourceCommit":ORIGINAL_SOURCE,"newAppSourceCommit":SOURCE,"newUISourceCommit":CORRECTED_UI_COMMIT,
        "originalPreparationExecutionSHA256":PREPARATION_EXECUTION_SHA,
        "originalPreparationAndMountedIndependentlyRequalified":True,
        "priorExecutionSHA256":PRIOR_EXECUTION_SHA,"priorBackupSHA256":PRIOR_BACKUP_SHA,
        "originalDevicePlistSHA256":PRIOR_DEVICE_PLIST_SHA,"fixtureSHA256":FIXTURE_SHA,
        "binding":BINDING,"device":DEVICE,"originalDeadlineEpoch":DEADLINE,
        "priorSourceUIStatus":"FAIL","privateAccountUnchangedBeforeBoot":True,
        "sourceOwner":"page154_e","continuationOwner":"migration_c","fixtureFactoryInvocations":0}
    c.write(evidence / "handoff.json", value)
    return app, fixture, fixture_bytes, c.digest(evidence / "handoff.json"), retainer


def captures_inventory(c, app):
    parent = app / "Library/Application Support/Pinkha/NativeSourceCaptures"
    if not parent.exists():
        c.require(not parent.is_symlink(), "Capture parent cannot be a dangling alias")
        return parent, {}
    c.require(parent.resolve() == parent and parent.is_dir(), "Private capture parent is aliased")
    result = {}
    for child in sorted(parent.iterdir()):
        if re.fullmatch(r"source-observation-[0-9A-F-]{36}\.json", child.name):
            c.require(child.is_file() and not child.is_symlink()
                      and stat.S_IMODE(child.stat().st_mode) == 0o600
                      and child.stat().st_size <= 131072, "Unexpected diagnostic file authority")
            continue
        c.require(child.is_dir() and not child.is_symlink() and child.name.startswith("native-source-"),
                  "Unexpected private capture child")
        result[child.name] = c.inventory(child)
    c.require(len(result) <= 128, "Unbounded private capture inventory")
    return parent, result



def witness_heads(c, payload, manifest, fixture):
    offset = 0
    def field(maximum):
        nonlocal offset
        c.require(len(payload) - offset >= 8, "Truncated native witness length")
        size = struct.unpack(">Q", payload[offset:offset+8])[0]; offset += 8
        c.require(size <= maximum and size <= len(payload) - offset, "Native witness length bound")
        result = payload[offset:offset+size]; offset += size
        return result
    def number():
        value = field(8); c.require(len(value) == 8, "Native witness integer width")
        return struct.unpack(">Q", value)[0]
    for expected in (b"pinkha-localstore-witness-v1", b"anyenc-v1.0.3-decoded-value-roundtrip-v1", b"heart-owned-local-store-v1"):
        c.require(field(128) == expected, "Original native witness framing contract")
    native = manifest["Receipt"]["Source"]["source"]["native"]
    nonce = field(32)
    c.require(len(nonce) == 32 and c.sha(nonce) == native["OwnerSHA256"]
              and field(4096) == fixture["spaceID"].encode(), "Witness owner/space mismatch")
    c.require(number() == native["Generation"] == manifest["Receipt"]["Inventory"]["Generation"], "Witness generation mismatch")
    count = number()
    c.require(count <= 100000 and count == native["Collections"] == len(native["CollectionCoverage"]), "Witness collection count")
    heads = []; total_rows = 0; total_bytes = 0; previous_name = None
    for i in range(count):
        name = field(4096)
        c.require(name and (previous_name is None or previous_name < name), "Duplicate or unordered native collection")
        previous_name = name
        rows = number(); c.require(rows <= 10000000, "Native row bound")
        previous_id = None; byte_count = 0
        for _ in range(rows):
            identity, value = field(16*1024**2), field(512*1024**2)
            c.require(identity and (previous_id is None or previous_id < identity), "Duplicate or unordered native row")
            previous_id = identity; byte_count += len(value)
            if name == b"heads":
                c.require(3 <= len(identity) <= 4098 and identity[0] == 3 and identity[-1] == 0
                          and b"\0" not in identity[1:-1], "Invalid native head identity")
                heads.append(identity[1:-1].decode("utf-8"))
        coverage = native["CollectionCoverage"][i]
        c.require(coverage["NameSHA256"] == c.sha(name) and coverage["Rows"] == rows
                  and coverage["EncodedValueBytes"] == byte_count, "Original native collection coverage differs")
        total_rows += rows; total_bytes += byte_count
        c.require(total_rows <= 10000000, "Cumulative native row bound")
    c.require(offset == len(payload) and total_rows == native["Rows"]
              and total_bytes == native["EncodedValueBytes"] and len(heads) == len(set(heads)), "Native witness totals differ")
    tree_ids = {x["ObjectID"] for x in manifest["Trees"]}
    c.require(tree_ids.issubset(heads) and len(heads) > len(tree_ids), "Complete native head census missing")
    return len(heads)

def verify_bundle(c, directory, fixture):
    manifest_path = directory / "manifest.json"
    raw = c.raw(manifest_path, 16*1024**2); manifest = c.decode(raw); receipt = manifest["Receipt"]
    st = manifest_path.lstat()
    c.require(manifest_path.resolve() == manifest_path and stat.S_ISREG(st.st_mode)
              and st.st_nlink == 1 and stat.S_IMODE(st.st_mode) & 0o077 == 0,
              "Actual native manifest privacy differs")
    native = receipt["Source"]["source"]["native"]
    c.require(manifest["SourceRows"]["SHA256"] == receipt["Inventory"]["SourceWitnessSHA256"]
              == native["WitnessSHA256"]
              and receipt["Source"]["source"]["accountSHA256"] == receipt["Source"]["accountSHA256"]
              and receipt["Source"]["source"]["spaceSHA256"] == receipt["Inventory"]["SpaceSHA256"]
              == native["SpaceSHA256"], "Native witness/owner digests differ")
    c.require(manifest["Files"] is None or isinstance(manifest["Files"], list),
              "Native files must be an original nullable array")
    c.require(manifest["Contract"] == "pinkha-native-whole-source-bundle-v1"
              and receipt["Version"] == "loaded-account-native-space-source-v1"
              and receipt["Source"]["accountSHA256"] == c.sha(fixture["accountID"].encode())
              and receipt["Inventory"]["SpaceSHA256"] == c.sha(fixture["spaceID"].encode())
              and receipt["Source"]["accountAuthority"] == "held-application-account-directory-lease-v1"
              and receipt["Source"]["sessionAuthority"] == "validated-native-full-unassociated-session-v1",
              "Actual native account/session source binding differs")
    for flag in ("AccountSessionAuthorizedAtFinalCapture", "AllNativeHeadRowsAccounted",
                 "CapturedSnapshotsBoundToUnchangedCheckpoint", "OriginalNativeHistoryRowsRetained", "IndexResolverSnapshotBound"):
        c.require(receipt.get(flag) is True, "Incomplete native source capture: " + flag)
    c.require(receipt["PermitsDestinationWrites"] is False, "Source capture cannot imply destination admission")
    members = {}
    def visit(value):
        if isinstance(value, dict):
            if set(value) == {"Path", "SHA256", "Bytes"}:
                name = value["Path"]
                c.require(isinstance(name, str) and not PurePosixPath(name).is_absolute()
                          and "\\" not in name and all(p not in ("", ".", "..") for p in name.split("/"))
                          and name not in members and re.fullmatch(r"[0-9a-f]{64}", value["SHA256"])
                          and type(value["Bytes"]) is int and 0 <= value["Bytes"] <= 512*1024**2,
                          "Unsafe or duplicate native member")
                path = directory / name
                st = path.lstat()
                c.require(path.resolve() == path and stat.S_ISREG(st.st_mode) and st.st_nlink == 1
                          and st.st_size == value["Bytes"] and c.digest(path) == value["SHA256"]
                          and stat.S_IMODE(st.st_mode) & 0o077 == 0, "Original native member bytes/privacy differ")
                members[name] = dict(value)
            else:
                for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(manifest)
    c.require(len(members) <= 100000 and sum(x["Bytes"] for x in members.values()) <= 3*1024**3,
              "Bounded native capture required")
    actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    c.require(actual == set(members) | {"manifest.json"}, "Undeclared or missing native source member")
    snapshots = []
    object_ids = [x["ObjectID"] for x in manifest["Objects"]]
    tree_ids = [x["ObjectID"] for x in manifest["Trees"]]
    c.require(len(object_ids) == len(set(object_ids)) and len(tree_ids) == len(set(tree_ids))
              and set(object_ids) == {x["ObjectID"] for x in manifest["Trees"]
                                    if x["Status"] == "captured-current-snapshot"},
              "Actual object/tree identity census differs")
    for obj in manifest["Objects"]:
        view = c.decode(c.raw(directory / obj["NativeJSONView"]["Path"], 32*1024**2))
        c.require(view["Contract"] == "pinkha-native-snapshot-json-v1"
                  and view["SpaceID"] == fixture["spaceID"] and view["ObjectID"] == obj["ObjectID"]
                  and view["NativeType"] == obj["NativeType"] and view["UniqueKey"] == obj["UniqueKey"]
                  and view["SnapshotSHA256"] == obj["Snapshot"]["SHA256"]
                  and view["SnapshotBytes"] == obj["Snapshot"]["Bytes"], "Native snapshot identity/protobuf binding differs")
        snapshots.append(view)
    heads = witness_heads(c, c.raw(directory / manifest["SourceRows"]["Path"], 512*1024**2), manifest, fixture)
    counts = {"trees": len(manifest["Trees"]), "nativeHeads": heads, "objects": len(snapshots),
        "blocks": sum(len(v["Snapshot"]["blocks"]) for v in snapshots),
        "types": sum(v["NativeType"] == 528 for v in snapshots),
        "properties": sum(v["NativeType"] == 521 for v in snapshots),
        "options": sum(v["NativeType"] == 529 for v in snapshots), "files": len(manifest["Files"] or [])}
    c.require(receipt["CapturedObjects"] == counts["objects"] and receipt["NativeTrees"] == counts["trees"]
              and receipt["CapturedFiles"] == counts["files"], "Original capture receipt count mismatch")
    return {"manifestSHA256": c.sha(raw), "verifiedMembers": len(members),
        "verifiedBytes": sum(x["Bytes"] for x in members.values()), "counts": counts,
        "sourceWitnessSHA256": receipt["Inventory"]["SourceWitnessSHA256"],
        "currentFilePayloadCompleteness": receipt["CurrentFilePayloadCompleteness"],
        "destinationAdmission": False, "accountSHA256": c.sha(fixture["accountID"].encode()),
        "spaceSHA256": c.sha(fixture["spaceID"].encode())}

def observation(c, directory, fixture, handoff_sha):
    manifest = c.decode(c.raw(directory / "manifest.json")); found = []
    c.require(isinstance(manifest, list), "Original exported attachment manifest required")
    for row in manifest:
        for item in row.get("attachments", []):
            if not str(item.get("suggestedHumanReadableName", "")).startswith("heart-source-capture-ui_"): continue
            test = row.get("testIdentifier", "").removeprefix(SELECTOR.split("/")[0] + "/").removesuffix("()")
            c.require(test == "/".join(SELECTOR.split("/")[1:]) and item.get("isAssociatedWithFailure") is False
                      and item.get("deviceId", "").upper() == DEVICE, "Foreign actual UI observation")
            name = item.get("exportedFileName", "")
            c.require(isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."), "Unsafe attachment name")
            found.append(directory / name)
    c.require(len(found) == 1, "Exactly one actual C UI observation required")
    value = c.decode(c.raw(found[0], 65536))
    c.require(value["protocol"] == "pinkha-heart-source-capture-ui-v1" and value["status"] == "UI_PASS"
              and all(value[k] == v for k, v in BINDING.items())
              and value["fixtureSHA256"] == FIXTURE_SHA and value["handoffSHA256"] == handoff_sha
              and value["deadlineEpoch"] == DEADLINE and value["closeCompletions"] == 2
              and value["scope"] == "actual-source-capture-review-close-recapture-only", "Incomplete actual source UI observation")
    captures = value["captures"]
    c.require(len(captures) == 2 and len({x["captureID"] for x in captures}) == 2, "Two distinct actual capture requests required")
    for index, capture in enumerate(captures, 1):
        c.require(capture["ordinal"] == index and capture["accountID"] == fixture["accountID"]
                  and capture["spaceID"] == fixture["spaceID"] and re.fullmatch(r"[0-9a-f]{64}", capture["manifestSHA256"])
                  and capture["destinationWrites"] == "not-requested-and-not-qualified-by-this-method", "Wrong actual captured identity")
        counts = capture["counts"]
        c.require(all(type(n) is int and n >= 0 for n in counts.values())
                  and counts["definition-issues"] > 0 and counts["unmapped"] > 0, "Semantic requirements were hidden")
    return value, {"path": str(found[0]), "sha256": c.digest(found[0])}

def source_stage(c, commands, root, built, app, binding, device, additions):
    # Exact original executor predicates; this separate task selects only C's
    # compiled method. No E selector, assertion or source is modified.
    import types
    isolated = dict(c.stage.__globals__)
    isolated["STAGES"] = {"source-review": SELECTOR}
    stage = types.FunctionType(c.stage.__code__, isolated, "source_stage")
    return stage(commands, root, "source-review", built, app, binding, device, additions)

def admit_navigation_ui(c, commands, root, evidence, built):
    receipt_path = UI_BUILD / "evidence/receipt.json"
    c.require(c.digest(receipt_path) == UI_RECEIPT_SHA, "Exact actual UI producer receipt required")
    receipt = c.decode(c.raw(receipt_path))
    c.require(receipt["protocol"] == "pinkha-c-source-observer-onboarding-ui-producer-v1"
              and receipt["status"] == "PASS_COMPLETE_UI_BUILD_ONLY_NOT_ACCEPTANCE"
              and receipt["appSourceCommit"] == SOURCE
              and receipt["originalUISourceCommit"] == SOURCE
              and receipt["uiSourceCommit"] == CORRECTED_UI_COMMIT
              and receipt["controllerSHA256"] == "0273513a02aaa8e91f0f4130bd83b0906718913564d81c9aefe6e5ffa0d4e606"
              and receipt["appBuilds"] == receipt["nativeBuilds"] == receipt["testsExecuted"] == 0
              and receipt["appProductsUnchanged"] is True and receipt["nativeRuntimeUnchanged"] is True
              and all(x["absentAtOriginalExit"] is True for x in receipt["ownedGroups"]),
              "Actual source-bound UI-only producer scope differs")
    proof_pins = {"ui-source-proof.json": UI_SOURCE_PROOF_SHA,
                  "generator.json": UI_GENERATOR_PROOF_SHA,
                  "generated-project.json": UI_PROJECT_PROOF_SHA,
                  "ui-products.json": UI_PRODUCTS_SHA}
    for name, pin in proof_pins.items():
        c.require(c.digest(UI_BUILD / "evidence" / name) == pin, "UI producer proof changed: " + name)
    source_proof = c.decode(c.raw(UI_BUILD / "evidence/ui-source-proof.json"))
    c.require(source_proof["exactNavigationInverse"] is True
              and source_proof["allOtherUISourcesByteIdentical"] is True
              and source_proof["originalAssertionsRemoved"] == 0
              and source_proof["uiSourceCommit"] == CORRECTED_UI_COMMIT
              and len(source_proof["files"]) == 12, "Complete original UI source delta proof required")
    source = UI_BUILD / "ui-source"
    for name, row in source_proof["files"].items():
        path = source / name
        c.require(path.stat().st_size == row["bytes"] and c.digest(path) == row["sha256"],
                  "Actual compiled UI source changed")
    project = source / "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj"
    c.require(c.inventory(project) == c.decode(c.raw(UI_BUILD / "evidence/generated-project.json")),
              "Actual generated complete UI project changed")
    command = receipt["uiCommand"]
    log = UI_BUILD / "commands/complete-ui-build/original.log"
    c.require(command["exitCode"] == 0 and command["status"] == "PASS_COMMAND"
              and command["ownedGroupPresentAfterExit"] is False
              and c.digest(log) == command["logSHA256"] == "5102460190855238c9b9a4790dc839322f97fcdd889e5ac4787ecf8d3d32315d"
              and b"** TEST BUILD SUCCEEDED **" in c.raw(log, 64 * 1024**2),
              "Actual successful complete UI compilation required")
    original = Path(receipt["productRoot"])
    c.require(original == UI_BUILD / "derived/Build/Products"
              and receipt["productManifestSHA256"] == UI_PRODUCTS_SHA,
              "UI original product location differs")
    manifest = c.decode(c.raw(UI_BUILD / "evidence/ui-products.json"))
    c.require(c.inventory(original) == manifest, "Actual UI producer products changed")
    destination = root / "navigation-ui-products"
    mask = os.umask(0)
    try: commands.run(["cp", "-cR", str(original), str(destination)], "clone-corrected-ui-products", 180)
    finally: os.umask(mask)
    c.require(c.inventory(destination) == manifest, "Corrected UI clone bytes/modes differ")
    descriptor = destination / receipt["descriptorRelativePath"]
    c.require(descriptor.parent == destination and descriptor.suffix == ".xctestrun"
              and c.digest(descriptor) == receipt["descriptorSHA256"],
              "Actual corrected UI descriptor differs")
    old = built["ui"]
    c.require(receipt["originalSelection"] == old["originalSelection"], "Original UI selection changed")
    built["original-ui"] = old
    built["ui"] = {"products": destination, "inventory": manifest, "copies": {},
                   "descriptor": descriptor, "originalSelection": receipt["originalSelection"]}
    result = {"status": "QUALIFIED_EXPLICIT_UI_DERIVATIVE_NOT_ACCEPTANCE",
              "appSourceCommit": SOURCE, "uiSourceCommit": CORRECTED_UI_COMMIT,
              "producerReceiptSHA256": UI_RECEIPT_SHA, "sourceProofSHA256": UI_SOURCE_PROOF_SHA,
              "fullProductManifestSHA256": UI_PRODUCTS_SHA, "originalAssertionsRemoved": 0,
              "appBuilds": 0, "nativeBuilds": 0, "testsAlreadyRunByThisAdmission": 0}
    c.write(evidence / "corrected-ui-admission.json", result)
    return result


def install_same_native_app(c, commands, evidence, app, original_data, retainer):
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    def roots(data):
        return {"application-data":data,"shared-app-groups":device_root / "data/Containers/Shared/AppGroup",
                "keychains":device_root / "data/Library/Keychains","device-preferences":device_root / "data/Library/Preferences"}
    def inventory(data):
        return {label:(retainer.inventory(path) if path.exists() else None) for label,path in roots(data).items()}
    info = plistlib.loads(c.raw(app / "Info.plist"))
    c.require(info["CFBundleIdentifier"] == c.BUNDLE, "Update must use the exact existing application identity")
    before = inventory(original_data)
    c.write(evidence / "before-app-update-account.json", before)
    output, command = commands.run(["xcrun","simctl","install",DEVICE,str(app)], "install-qualified-source-observer-app", 120)
    updated_data = app_container(c,commands,"updated-original-container")
    after = inventory(updated_data)
    c.write(evidence / "after-app-update-account.json", after)
    differences = {}
    for label in before:
        a,b = before[label],after[label]
        if a != b:
            if isinstance(a,dict) and isinstance(b,dict):
                differences[label]={"removed":sorted(set(a)-set(b)),"added":sorted(set(b)-set(a)),
                    "changed":sorted(k for k in set(a)&set(b) if a[k] != b[k])}
            else: differences[label]={"originalScopePresent":a is not None,"updatedScopePresent":b is not None}
    c.write(evidence / "app-update-data-comparison.json", {"beforeContainer":str(original_data),
        "afterContainer":str(updated_data),"allFourScopesByteModeEqual":not differences,"differences":differences,
        "originalFixtureDeadlineEpoch":DEADLINE,"restoredData":False,"installCommand":command})
    c.require(not differences, "Installed App update changed retained account data; inspect exact observed differences")
    c.require(c.digest(updated_data / "Library/Application Support" / c.FIXTURE) == FIXTURE_SHA,
              "Updated App retained a different fixture")
    original_inventory = c.inventory(app)
    located,_ = commands.run(["xcrun","simctl","get_app_container",DEVICE,c.BUNDLE,"app"],
                             "updated-installed-app",30,capacity=False)
    installed = Path(c.raw(located,4096).decode().strip())
    c.require(installed.resolve() == installed and installed.is_dir()
              and installed.parent.parent == device_root / "data/Containers/Bundle/Application",
              "Actual installed App must belong to the owned simulator")
    installed_inventory = c.inventory(installed)
    def content(rows):
        return {name:{k:v for k,v in row.items() if k != "mode"} for name,row in rows.items()}
    c.write(evidence / "installed-app-original-inventory.json", original_inventory)
    c.write(evidence / "installed-app-actual-inventory.json", installed_inventory)
    c.require(content(original_inventory) == content(installed_inventory),
              "Actual installed App bytes, paths, kinds or links differ from the qualified product")
    return updated_data

def collect_diagnostic(c, app_data, private):
    parent = app_data / "Library/Application Support/Pinkha/NativeSourceCaptures"
    rows=[]
    if not parent.exists(): return rows
    c.require(parent.resolve() == parent and parent.is_dir(), "Diagnostic parent must be private and canonical")
    for item in sorted(parent.glob("source-observation-*.json")):
        c.require(re.fullmatch(r"source-observation-[0-9A-F-]{36}\.json", item.name)
                  and item.resolve() == item and item.is_file()
                  and stat.S_IMODE(item.stat().st_mode) == 0o600, "Diagnostic private file changed")
        raw=c.raw(item,131072); value=c.decode(raw)
        c.require(set(value)=={"contract","acceptance","truncated","events"}
                  and value["contract"]=="pinkha-heart-source-diagnostic-v1"
                  and value["acceptance"] is False and isinstance(value["events"],list)
                  and len(value["events"]) <= 128, "Unexpected source observer contract")
        c.write_bytes(private / "source-observations" / item.name, raw)
        rows.append({"file":item.name,"sha256":c.sha(raw),"bytes":len(raw)})
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--qualify-only", action="store_true")
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--handoff-sha256", required=True)
    args = parser.parse_args()
    c = load_core()
    input_handoff_sha = load_handoff(c, args.handoff, args.handoff_sha256)
    c.require(sys.platform == "darwin", "Actual Mac required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
              "Fresh canonical owned continuation root")
    args.root.mkdir(mode=0o700); os.umask(0o077)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    commands = c.Commands(args.root / "commands", args.root)
    result = { "protocol": "pinkha-current-source-observer-account-update-v1", "status": "FAIL",
        "sourceCommit": SOURCE, "originalFixtureSourceCommit": BINDING["sourceSHA"], "uiSourceCommit": CORRECTED_UI_COMMIT, "inputHandoffSHA256": input_handoff_sha,
        "controllerSHA256": c.digest(Path(__file__)), "binding": BINDING,
        "ownedSimulator": DEVICE, "originalSimulatorStateReused": True, "wholeSpaceMigration": False, "qualificationOnly": args.qualify_only,
        "builds": 0, "fixtureFactoryInvocations": 0, "deadlineExtended": False, "stages": {}}
    built = {}; claimed_boot = False; app_data = None; retainer = None
    try:
        admission_path = CONTROL / "admission5ffff.json"
        c.require(c.digest(admission_path) == ADMISSION_SHA, "Exact qualified current same-source admission required")
        admission = c.decode(c.raw(admission_path))
        c.require(admission["controllerSHA256"] == CONTROL_SHA and admission["sourceCommit"] == SOURCE, "Original product authority differs")
        c.require(c.digest(Path(admission["sourceRoot"]) / "PinkhaStage1Acceptance/Tests/HeartSourceCaptureAcceptanceUITests.swift") == UI_SOURCE_SHA, "Original compiled C method changed")
        # cp -cR must preserve the already-admitted directory modes. The
        # enclosing continuation root is 0700; no account data is read until the
        # private umask is restored. Exact source/product mode checks remain.
        private_mask = os.umask(0)
        try:
            result["sourceAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
        finally:
            os.umask(private_mask)
        result["productCloneModePolicy"] = "exact-original-modes-within-private-0700-root"
        result["correctedUIAdmission"] = admit_navigation_ui(c, commands, args.root, evidence, built)
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        c.common = importlib.import_module("contracts")
        c.native = importlib.import_module("consumer_contract")
        c.mounted = importlib.import_module("mounted_contract")
        c.boundary = importlib.import_module("page154_boundary")
        app_data, fixture, fixture_bytes, handoff_sha, retainer = original_handoff(c, commands, evidence)
        result["handoffSHA256"] = handoff_sha
        c.write_bytes(private / c.FIXTURE, fixture_bytes)
        parent, before = captures_inventory(c, app_data)
        c.write(private / "captures-before.json", before)
        if args.qualify_only:
            result["status"] = "QUALIFIED_SOURCE_PRODUCT_ACCOUNT_ONLY_NO_XCTEST"
        else:
            owned_device(c, commands, "immediately-before-boot")
            c.require(time.time() + 300 < DEADLINE, "Original fixture has insufficient bounded UI time")
            claimed_boot = True
            commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-delegated-simulator", 60)
            commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-delegated-boot", 180)
            owned_device(c, commands, "ready-for-source-ui", expected="Booted")
            c.require(app_container(c, commands, "booted-original-container") == app_data,
                      "Booted app resolution differs from sealed original account")
            app_data = install_same_native_app(c, commands, evidence, app, app_data, retainer)
            parent, actual_before = captures_inventory(c, app_data)
            c.require(actual_before == before, "Existing capture data changed during App update")
            additions = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1", "PINKHA_SEMANTIC_MOUNTED_TESTING": "1",
                "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_bytes.decode(),
                "PINKHA_HEART_SOURCE_CAPTURE_TESTING": "1", "PINKHA_HEART_SOURCE_CAPTURE_FIXTURE_SHA256": FIXTURE_SHA,
                "PINKHA_HEART_SOURCE_CAPTURE_HANDOFF_SHA256": handoff_sha,
                "PINKHA_HEART_SOURCE_CAPTURE_DEADLINE_EPOCH": repr(DEADLINE)}
            for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
                additions["PINKHA_SEMANTIC_MOUNTED_" + suffix] = BINDING[key]
            stage = source_stage(c, commands, evidence, built["ui"], app, BINDING, DEVICE, additions)
            result["stages"]["source-review"] = stage
            c.require(stage["status"] == "PASS" and stage["command"]["finishedAt"] < DEADLINE,
                      "Original C actual UI method did not pass within the original fixture deadline")
            ui, pin = observation(c, evidence / "source-review/private-attachments", fixture, handoff_sha)
            c.write(private / "actual-ui-observation.json", ui)
            result["uiObservationSHA256"] = pin["sha256"]
            _, after = captures_inventory(c, app_data)
            c.require(all(name in after and after[name] == inventory for name, inventory in before.items()),
                      "An existing source capture was changed or removed")
            new = sorted(set(after) - set(before))
            c.require(len(new) == 2, "Exactly two new native private bundles required")
            proofs = [verify_bundle(c, parent / name, fixture) for name in new]
            c.require(collections.Counter(x["manifestSHA256"] for x in proofs) ==
                      collections.Counter(x["manifestSHA256"] for x in ui["captures"]), "UI fingerprints differ from actual new native bundles")
            for capture in ui["captures"]:
                matches = [p for p in proofs if p["manifestSHA256"] == capture["manifestSHA256"]]
                c.require(matches and all(all(capture["counts"][key] == value for key, value in proof["counts"].items()) for proof in matches),
                          "UI census differs from original native snapshots/witness")
            c.write(private / "captures-after.json", after)
            result["nativeBundles"] = proofs
            result["distinctCaptureRequests"] = 2; result["closedReviews"] = 2
            result["status"] = "PASS_ACTUAL_SOURCE_UI_TWO_CAPTURES_CLOSE_AND_NATIVE_BUNDLE_COMPARISON"
    except BaseException as exc:
        result["firstFailure"] = c.error(exc)
        c.write(private / "controller-failure.json", {"error": c.error(exc), "traceback": traceback.format_exc()})
    finally:
        cleanup = {"status": "PASS", "ownedSimulatorDeleted": False, "ownedSimulatorRetainedForRecovery": DEVICE,
                   "groups": [], "errors": []}
        if claimed_boot:
            try:
                if app_data is not None:
                    # Diagnostic output is not acceptance and must never suppress
                    # independent witness/account retention when it is unavailable.
                    actual_data = app_container(c, commands, "final-observer-container")
                    result["sourceDiagnosticFiles"] = collect_diagnostic(c, actual_data, private)
                    result["sourceDiagnosticCollection"] = {"status":"COPIED_PRIVATE_DIAGNOSTICS_NOT_ACCEPTANCE"}
            except BaseException as exc:
                result["sourceDiagnosticCollection"] = {"status":"FAIL_NOT_ACCEPTANCE","error":c.error(exc)}
            try:
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, DEVICE, private / "final-sandbox-originals",
                    application_invoked=any(x.get("testInvoked") is True for x in result["stages"].values())
                        or (args.root / "commands/source-review-test/started.json").is_file())
                c.require(result["finalPrivateSandbox"]["files"] ==
                          c.decode(c.raw(PRIOR / "evidence/execution.json"))["finalPrivateSandbox"]["files"],
                          "Original E native witnesses changed during C capture")
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
            try:
                output, stopped = commands.run(["xcrun", "simctl", "shutdown", DEVICE], "cleanup-shutdown", 60, checked=False, capacity=False)
                c.require(stopped["exitCode"] == 0, "Delegated account shutdown failed")
                owned_device(c, commands, "final-delegated-shutdown")
            except BaseException as exc:
                cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True, "historicalGroupReprobed": False})
            else:
                try:
                    present = c.Commands.present(group)
                    cleanup["groups"].append({"pgid": group, "present": present})
                    if present: cleanup["status"] = "FAIL"; cleanup["errors"].append({"ownedGroupStillPresent": group})
                except BaseException as exc:
                    cleanup["status"] = "FAIL"
                    cleanup["groups"].append({"pgid":group,"observationError":c.error(exc),"signalsSent":0})
                    cleanup["errors"].append({"ownedGroupUnresolved":group,"error":c.error(exc)})
        try:
            result["finalProducts"] = {name: c.product_integrity(value) for name, value in built.items()}
            c.require(c.digest(PRIOR / "evidence/execution.json") == PRIOR_EXECUTION_SHA
                      and c.digest(PRIOR / "private/owned-account-originals/retention.json") == PRIOR_BACKUP_SHA,
                      "Original E evidence changed")
        except BaseException as exc:
            cleanup["status"] = "FAIL"; cleanup["errors"].append(c.error(exc))
        if cleanup["status"] != "PASS": result["status"] = "FAIL"
        result["cleanup"] = cleanup
        c.write(evidence / "cleanup.json", cleanup)
        c.write(evidence / "execution.json", result)
        if claimed_boot and cleanup["status"] == "PASS" and retainer is not None and "finalPrivateSandbox" in result:
            try:
                backup = retainer.retain(args.root, c.digest(evidence / "execution.json"))
                c.write(evidence / "account-retention.json", backup)
                c.write(evidence / "account-retention-handoff.json", {
                    "backupSHA256": c.digest(private / "owned-account-originals/retention.json"),
                    "devicePlistSHA256": c.digest(private / "owned-account-originals/device.plist"),
                    "executionSHA256": c.digest(evidence / "execution.json"), "device": DEVICE,
                    "originalDeadlineEpoch": DEADLINE, "fixtureDeadlineExtended": False})
            except BaseException as exc:
                c.write(evidence / "account-retention-failure.json", c.error(exc))
                result["status"] = "FAIL_ACCOUNT_RETENTION"
        c.write(evidence / "final-outcome.json", {"status": result["status"],
            "executionSHA256": c.digest(evidence / "execution.json"),
            "priorEOriginalFailurePreserved": True, "fixtureDeadlineExtended": False})
    print(json.dumps({"status": result["status"], "receipt": str(evidence / "execution.json"),
                      "finalOutcome": str(evidence / "final-outcome.json"),
                      "finalOutcomeSHA256": c.digest(evidence / "final-outcome.json"),
                      "firstFailure": result.get("firstFailure")}, sort_keys=True))
    return 0 if result["status"].startswith("PASS_ACTUAL_SOURCE_UI") or (
        args.qualify_only and result["status"] == "QUALIFIED_SOURCE_PRODUCT_ACCOUNT_ONLY_NO_XCTEST") else 1



if __name__ == "__main__":
    raise SystemExit(main())