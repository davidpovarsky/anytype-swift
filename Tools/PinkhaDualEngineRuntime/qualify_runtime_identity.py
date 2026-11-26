#!/usr/bin/env python3
"""Qualify full runtime identity against retained original11619 linker evidence."""
from __future__ import annotations
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
REPO = Path("/mnt/development/projects/worktrees/anytype-native-d-completion-20261125")
HERE = REPO / "Tools/PinkhaDualEngineRuntime"
ORIGINALS = Path("/mnt/development/projects/evidence/native-d-final-20261125/runtime-identity-originals11619")
OUT = Path("/mnt/development/projects/evidence/native-d-final-20261125/runtime-identity-controls-attempt1")
MODULE_SHA = "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0"
OLD_MANIFEST_SHA = "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
NEW_MANIFEST_SHA = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
OLD_BRIDGE_SHA = "29f365adab078c488f303f35d0269a7a97d02fbeb245c8b0807542f03616b6e5"
PINS = {
    "simulator": ("aa9320f43659d56fe7f366ad6a77943a296f0fe55e545ff2e6516dafbde91e49",
                  "8ae9c723dbae7f99246becd667fd7f055aff6b80d8df39ddb1e84acc12e60d62"),
    "device": ("f71d7d1108e427d79790c4e3bb99cd7667b7d62397cabe1ac53e0a7fd48c9f33",
               "7ed624973d66e8b61edbbde7177984bbf80ae29323c1fd633df1c12d69affa6e"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def main():
    module_path = HERE / "runtime_identity.py"
    assert sha(module_path.read_bytes()) == MODULE_SHA
    spec = importlib.util.spec_from_file_location("runtime_identity", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old_manifest = (HERE / "source-immutable-manifest.json").read_bytes()
    new_manifest = (HERE / "source-permission-manifest.json").read_bytes()
    assert sha(old_manifest) == OLD_MANIFEST_SHA and sha(new_manifest) == NEW_MANIFEST_SHA
    old_bridge = subprocess.check_output(["git", "-c", "safe.directory=" + str(REPO),
        "-C", str(REPO), "show", "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7:"
        "Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift"], timeout=20)
    assert sha(old_bridge) == OLD_BRIDGE_SHA
    retention = (ORIGINALS / "receipt.json").read_bytes()
    assert sha(retention) == "55841b0f7bf8cdf95541420bddfd027a6e1e89e15a111774d9d7323aa2a1744a"
    original_inputs = {}
    source_paths = [module_path, HERE / "source-immutable-manifest.json",
                    HERE / "source-permission-manifest.json", ORIGINALS / "receipt.json"]
    for kind, (receipt_pin, command_pin) in PINS.items():
        folder = ORIGINALS / kind
        receipt = folder / "receipt.json"
        command = folder / "combined-gomobile-bind.command.json"
        log = folder / "combined-gomobile-bind.log"
        source_paths += [receipt, command, log]
        assert sha(receipt.read_bytes()) == receipt_pin and sha(command.read_bytes()) == command_pin
        original_inputs[kind] = {"receipt": receipt.read_bytes(), "command": command.read_bytes(),
            "log": log.read_bytes(), "expectedReceiptSHA256": receipt_pin, "expectedCommandSHA256": command_pin}
    before = {str(p): sha(p.read_bytes()) for p in source_paths}
    historical_expected = module.identity(old_manifest, "2026-11-26")
    corrected_fixture = module.replacing_swift_profile(old_bridge, historical_expected)
    future_expected = module.identity(new_manifest, "2026-11-26")
    future_fixture = module.replacing_swift_profile(old_bridge, future_expected)
    cases = []

    def accepts(name, operation):
        try:
            value = operation()
            cases.append({"name": name, "status": "PASS"})
            return value
        except Exception as exc:
            cases.append({"name": name, "status": "FAIL", "error": type(exc).__name__ + ":" + str(exc)})

    def refuses(name, operation, reason):
        try:
            operation()
        except module.IdentityError as exc:
            cases.append({"name": name, "status": "PASS" if str(exc) == reason else "FAIL",
                          "observedRefusal": str(exc), "expectedRefusal": reason})
        except Exception as exc:
            cases.append({"name": name, "status": "FAIL", "error": type(exc).__name__ + ":" + str(exc)})
        else:
            cases.append({"name": name, "status": "FAIL", "error": "invalid_contract_was_accepted"})

    def verify(bridge=corrected_fixture, manifest=old_manifest, inputs=None):
        return module.qualify_application(manifest, "2026-11-26", bridge, inputs or original_inputs)

    def changed_command(kind, mutate):
        inputs = copy.deepcopy(original_inputs)
        command = json.loads(inputs[kind]["command"])
        mutate(command)
        inputs[kind]["command"] = encoded(command)
        inputs[kind]["expectedCommandSHA256"] = sha(inputs[kind]["command"])
        return inputs

    def changed_flags(old, new):
        def mutate(command):
            i = command["argv"].index("-ldflags") + 1
            assert old in command["argv"][i]
            command["argv"][i] = command["argv"][i].replace(old, new, 1)
        return changed_command("simulator", mutate)

    refuses("actual_compiled_App76_stale_profile_is_rejected",
            lambda: verify(old_bridge), "consumer_full_native_identity_differs")
    historical_proof = accepts("corrected_profile_matches_both_actual_original_linker_commands",
                               lambda: verify())
    refuses("consumer_commit_mismatch_is_rejected", lambda: verify(corrected_fixture.replace(
        b'let anyCommit = "41c07bd32e95a54824a3d3c5d592accf5074ab68"',
        b'let anyCommit = "cf87c43ff0100c2dc43c3c105c82b1b070b3a7a3"')),
        "consumer_full_native_identity_differs")
    refuses("consumer_build_date_mismatch_is_rejected", lambda: verify(corrected_fixture.replace(
        b'let anyBuildDate = "2026-11-26"', b'let anyBuildDate = "2026-11-25"')),
        "consumer_full_native_identity_differs")
    refuses("consumer_manifest_mismatch_is_rejected",
            lambda: verify(corrected_fixture.replace(OLD_MANIFEST_SHA.encode(), b"0" * 64, 1)),
            "consumer_full_native_identity_differs")
    refuses("duplicate_native_linker_assignment_is_rejected",
            lambda: verify(inputs=changed_flags(module.VERSION_PACKAGE + "BuildDate=2026-11-26",
                                               module.VERSION_PACKAGE + "Commit=2026-11-26")),
            "ambiguous_native_version_binding")
    refuses("actual_linker_date_disagreement_is_rejected",
            lambda: verify(inputs=changed_flags("BuildDate=2026-11-26", "BuildDate=2026-11-27")),
            "actual_linker_full_identity_differs")
    refuses("actual_linker_commit_disagreement_is_rejected",
            lambda: verify(inputs=changed_flags(
                "Commit=41c07bd32e95a54824a3d3c5d592accf5074ab68",
                "Commit=8fbd1e819fb132ac0e0a848d2ddf5c5714189b81")),
            "actual_linker_full_identity_differs")
    def wrong_target(command):
        i = command["argv"].index("-target=iossimulator/arm64")
        command["argv"][i] = "-target=ios/arm64"
    refuses("wrong_apple_target_is_rejected",
            lambda: verify(inputs=changed_command("simulator", wrong_target)),
            "native_slice_target_differs")
    refuses("failed_original_native_command_is_rejected",
            lambda: verify(inputs=changed_command("simulator", lambda x: x.update(exitCode=1))),
            "actual_successful_original_bind_required")
    changed_manifest = json.loads(old_manifest)
    changed_manifest["files"][module.FORMATTER]["sha256"] = "0" * 64
    refuses("changed_actual_version_formatter_is_rejected",
            lambda: module.identity(encoded(changed_manifest), "2026-11-26"),
            "native_version_route_changed:" + module.FORMATTER)
    refuses("future_8fbd_consumer_cannot_reuse_old11619_binaries",
            lambda: verify(future_fixture, new_manifest),
            "original_qualified_slice_identity_differs")
    missing = dict(original_inputs)
    missing.pop("device")
    refuses("missing_original_device_slice_is_rejected",
            lambda: verify(inputs=missing), "both_original_apple_slices_required")

    after = {str(p): sha(p.read_bytes()) for p in source_paths}
    assert before == after
    OUT.mkdir(mode=0o700)
    if historical_proof is not None:
        (OUT / "corrected-historical-fixture-proof.json").write_bytes(encoded(historical_proof))
    result = {"protocol": "pinkha-runtime-full-identity-regression-controls-v1",
        "status": "PASS" if all(row["status"] == "PASS" for row in cases) else "FAIL",
        "actualPythonControls": len(cases), "passed": sum(row["status"] == "PASS" for row in cases),
        "failed": sum(row["status"] != "PASS" for row in cases), "skipped": 0, "cases": cases,
        "originalCompiledBridgeSHA256": OLD_BRIDGE_SHA,
        "historicalCorrectedProfileFixtureSHA256": sha(corrected_fixture),
        "nextProfileFixtureSHA256": sha(future_fixture),
        "currentNativeSourceManifestSHA256": OLD_MANIFEST_SHA,
        "nextNativeSourceManifestSHA256": NEW_MANIFEST_SHA,
        "nextExpectedRuntimeVersion": future_expected["anyRuntimeVersion"],
        "moduleSHA256": MODULE_SHA, "controllerSHA256": sha(Path(__file__).read_bytes()),
        "sourceBefore": before, "sourceAfter": after,
        "sourceUnchanged": True, "appOrNativeCompilations": 0, "nativeCalls": 0,
        "historicalProductReclassified": False, "applicationAcceptanceClaimed": False}
    encoded_result = encoded(result)
    (OUT / "result.json").write_bytes(encoded_result)
    print(json.dumps({"status": result["status"], "passed": result["passed"], "failed": result["failed"],
                      "skipped": 0, "resultSHA256": sha(encoded_result), "path": str(OUT / "result.json")}))
    for row in cases:
        print(json.dumps(row, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
