#!/usr/bin/env python3
"""Actual original-app Heart source review on E's explicit sealed handoff.

No account factory, source write, engine switch, native test hook, rebuild or
fixture deadline extension. The production UI performs both real captures.
"""
from __future__ import annotations
import collections
import importlib
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
CONTROL = Path("/Users/m1/builds/e-combined-current-20261125/control-c5bcf1c")
CONTROL_SHA = "21998d3f410871cb5833e0de1a1b80ef06f17c2a688d43eead239b60ee373ddf"
ADMISSION_SHA = "fd59d4b22102b06b4379429bfe893c0b7b3dabd38edc6ff0df9b34caf75b39ce"
RETAINER_SHA = "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b"
PRIOR = Path("/Users/m1/builds/e-combined-current-20261125/fresh-ca7-attempt1")
PRIOR_EXECUTION_SHA = "6cb4ca7311cca3355db3d729ecd01a4ff2f15e6a52a518879e4408f7c8e64f37"
PRIOR_BACKUP_SHA = "48cbb1f005afcb653a0505769ecf496ac0f2aa3ff51e4650ce4f6e7aaa73526e"
FIXTURE_SHA = "0a90efa3fb54b8313a633dbb1d1b4b95b4515c1d93c567b6078b84ac06e90887"
DEVICE = "5E77C761-78E5-4530-B44C-7561216652A6"
BINDING = {"sourceSHA": "ca7cb16f91c3d5fc4f7c8c178369abc9276e9a07",
           "runID": "1795610792364366", "runAttempt": "1", "nonce": "e8ef5f2272c14b848c43944a531a4606"}
DEADLINE = 1795618093.996194
SELECTOR = "PinkhaStage1AcceptanceUITests/HeartSourceCaptureAcceptanceUITests/testActualHeartSourceReviewCloseAndRecapture"
UI_SOURCE_SHA = "efb4508405851be56d2302c2cea84d337d5fa3ca5caa241d6f7a96bf2cc0b2f6"

def load_core():
    import hashlib
    path = CONTROL / "combined_heart_semantics_gateway_derivative.py"
    if hashlib.sha256(path.read_bytes()).hexdigest() != CONTROL_SHA:
        raise ValueError("Exact reviewed original product admission required")
    sys.path.insert(0, str(CONTROL))
    c = importlib.import_module("combined_heart_semantics_gateway_derivative")
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

def original_handoff(c, commands, evidence):
    execution_path = PRIOR / "evidence/execution.json"
    backup_path = PRIOR / "private/owned-account-originals/retention.json"
    fixture_path = PRIOR / "private" / c.FIXTURE
    c.require(c.digest(execution_path) == PRIOR_EXECUTION_SHA and c.digest(backup_path) == PRIOR_BACKUP_SHA
              and c.digest(fixture_path) == FIXTURE_SHA, "Original sealed handoff bytes changed")
    execution = c.decode(c.raw(execution_path)); backup = c.decode(c.raw(backup_path))
    fixture_bytes = c.raw(fixture_path, 65536); fixture = c.decode(fixture_bytes)
    c.require(execution["binding"] == BINDING and execution["ownedSimulator"] == DEVICE
              and execution["controllerSHA256"] == CONTROL_SHA
              and execution["sourceCommit"] == BINDING["sourceSHA"]
              and execution["stages"]["preparation"]["status"] == "PASS"
              and execution["stages"]["mounted"]["status"] == "PASS", "Original actual account preparation/mounted proof required")
    c.require(execution["cleanup"]["status"] == "PASS"
              and execution["cleanup"]["ownedSimulatorDeleted"] is False
              and execution["cleanup"]["ownedSimulatorRetainedForRecovery"] == DEVICE,
              "Original terminal cleanup must retain the delegated account")
    c.require(backup["protocol"] == "pinkha-owned-heart-account-retention-v1"
              and backup["status"] == "PASS_PRIVATE_ACCOUNT_BACKUP_NOT_NEW_ACCEPTANCE"
              and backup["executionSHA256"] == PRIOR_EXECUTION_SHA and backup["device"] == DEVICE
              and backup["fixtureDeadlineChanged"] is False and backup["restoredFixtures"] == 0,
              "Complete original private account backup required")
    for stage in ("preparation", "mounted"):
        directory = PRIOR / "evidence" / stage
        log = PRIOR / "commands" / (stage + "-test") / "original.log"
        original = execution["stages"][stage]
        c.require(c.digest(log) == original["command"]["logSHA256"], "Original test stdout changed")
        proof = c.qualify_execution(c.decode(c.raw(directory / "summary.json")),
            c.decode(c.raw(directory / "tests.json")), c.STAGES[stage], DEVICE, log)
        c.require(c.decode(json.dumps(proof).encode()) == original["actual"], "Original retained actual test proof differs")
    c.mounted.fixture(fixture, BINDING)
    c.require(fixture["createdAt"] + 978307200 + 7200 == DEADLINE and time.time() < DEADLINE,
              "The exact original fixture deadline must remain unchanged")
    owned_device(c, commands, "handoff-device")
    app = app_container(c, commands, "handoff-container")
    old_container = PRIOR / "commands/final-private-sandbox-container/original.log"
    c.require(Path(c.raw(old_container, 4096).decode().strip()) == app, "Original app container changed")
    device_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / DEVICE
    roots = {"application-data": app, "shared-app-groups": device_root / "data/Containers/Shared/AppGroup",
             "keychains": device_root / "data/Library/Keychains", "device-preferences": device_root / "data/Library/Preferences"}
    retainer_path = CONTROL / "retain_owned_heart_account.py"
    c.require(c.digest(retainer_path) == RETAINER_SHA, "Exact original safe account retention helper required")
    retainer = importlib.import_module("retain_owned_heart_account")
    c.require(Path(retainer.__file__).resolve() == retainer_path, "Foreign account retention helper")
    for label, root in roots.items():
        scope = backup["scopes"][label]
        if scope["status"] == "NOT_PRESENT":
            c.require(not root.exists() and not root.is_symlink(), "An originally absent private scope appeared")
            continue
        inventory_path = PRIOR / "private/owned-account-originals" / (label + "-before.json")
        c.require(scope["status"] == "PRESERVED_ORIGINAL_BYTES_AND_MODES"
                  and c.digest(inventory_path) == scope["manifestSHA256"]
                  and retainer.inventory(root) == c.decode(c.raw(inventory_path)),
                  "Delegated native account differs from the original shutdown backup")
    owned_device(c, commands, "handoff-after-inventory")
    c.require(c.digest(app / "Library/Application Support" / c.FIXTURE) == FIXTURE_SHA,
              "Live fixture differs from original handoff")
    value = {"protocol": "pinkha-source-capture-sequential-handoff-v1",
        "priorExecutionSHA256": PRIOR_EXECUTION_SHA, "priorBackupSHA256": PRIOR_BACKUP_SHA,
        "fixtureSHA256": FIXTURE_SHA, "binding": BINDING, "device": DEVICE,
        "originalDeadlineEpoch": DEADLINE, "sourceOwner": "page154_e", "continuationOwner": "migration_c",
        "priorFullEStatus": execution["status"], "actualPriorPreparationAndMountedMethods": "PASS",
        "privateAccountUnchangedBeforeBoot": True, "fixtureFactoryInvocations": 0}
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

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    c = load_core()
    c.require(sys.platform == "darwin", "Actual Mac required")
    c.require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(),
              "Fresh canonical owned continuation root")
    args.root.mkdir(mode=0o700); os.umask(0o077)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    commands = c.Commands(args.root / "commands", args.root)
    result = {"protocol": "pinkha-actual-heart-source-capture-continuation-v1", "status": "FAIL",
        "sourceCommit": BINDING["sourceSHA"], "uiSourceCommit": "8aa603ddb179a98a711a1cb2208d556a498c602f",
        "controllerSHA256": c.digest(Path(__file__)), "binding": BINDING,
        "ownedSimulator": DEVICE, "originalSimulatorStateReused": True, "wholeSpaceMigration": False,
        "builds": 0, "fixtureFactoryInvocations": 0, "deadlineExtended": False, "stages": {}}
    built = {}; claimed_boot = False; app_data = None; retainer = None
    try:
        admission_path = CONTROL / "admission-ca7-ui8aa.json"
        c.require(c.digest(admission_path) == ADMISSION_SHA, "Exact qualified ca7/8aa admission required")
        admission = c.decode(c.raw(admission_path))
        c.require(admission["controllerSHA256"] == CONTROL_SHA, "Original product authority differs")
        result["sourceAdmission"], built, app = c.admit_and_clone_products(admission, args.root, evidence, commands)
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
        owned_device(c, commands, "immediately-before-boot")
        c.require(time.time() + 300 < DEADLINE, "Original fixture has insufficient bounded UI time")
        claimed_boot = True
        commands.run(["xcrun", "simctl", "boot", DEVICE], "boot-delegated-simulator", 60)
        commands.run(["xcrun", "simctl", "bootstatus", DEVICE, "-b"], "await-delegated-boot", 180)
        owned_device(c, commands, "ready-for-source-ui", expected="Booted")
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
                result["finalPrivateSandbox"] = c.preserve_final_sandbox(commands, DEVICE, private / "final-sandbox-originals",
                    application_invoked=any(x.get("testInvoked") is True for x in result["stages"].values()))
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
                present = c.Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                if present: cleanup["status"] = "FAIL"; cleanup["errors"].append({"ownedGroupStillPresent": group})
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
            except BaseException as exc:
                c.write(evidence / "account-retention-failure.json", c.error(exc))
                result["status"] = "FAIL_ACCOUNT_RETENTION"
        c.write(evidence / "final-outcome.json", {"status": result["status"],
            "executionSHA256": c.digest(evidence / "execution.json"),
            "priorEOriginalFailurePreserved": True, "fixtureDeadlineExtended": False})
    print(json.dumps({"status": result["status"], "receipt": str(evidence / "execution.json"),
                      "firstFailure": result.get("firstFailure")}, sort_keys=True))
    return 0 if result["status"].startswith("PASS_ACTUAL_SOURCE_UI") else 1

if __name__ == "__main__":
    raise SystemExit(main())
