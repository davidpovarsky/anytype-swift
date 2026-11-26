#!/usr/bin/env python3
"""Finalize original RuntimeCore hydration without repeating passed native/Host preparation."""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--recovery-root", type=Path, required=True)
args = parser.parse_args()
recovery = args.recovery_root
assert recovery.parent == Path("/Users/m1/development/anytype-root-active-20261125")
assert recovery.resolve() == recovery and recovery.is_dir()
root = recovery / "source"
controls = Path(__file__).resolve().parent
evidence = recovery / "runtime-preparation1"
final = evidence / "FINALIZATION.json"
assert not final.exists()
original_host = Path("/Users/m1/development/hanlin-miniapps-active-20261125/miniapps/build/runtime-host/RuntimeHostResources.zip")
host_sha = "540507770659f00b8424b394c0c3857f52001cd13a0dc2bc3b38f313b385303a"
source_sha = "86a6dde354947be9329fe1e8f4d45a433fe488c4"
config_sha = "03d96d520f785e34d85b643e31bcb4a424e46e76a81c6b4c245f91eaac3e110f"
def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
preparation_raw = (evidence / "RESULT.json").read_bytes()
preparation = json.loads(preparation_raw)
assert preparation["status"] == "FAILED" and preparation["error"] == "AssertionError()"
assert preparation["helperSHA256"] == digest(controls / "hydrate_original_runtime.py") == "f992eca65098ae206ee7efa078308be463f8646c1344e5e9bc4de85a4ce7c3fc"
assert preparation["source"] == source_sha
assert preparation["appBuilds"] == preparation["testsExecuted"] == 0
assert len(preparation["commands"]) == 2
for label, item in zip(("prepare-runtime-core", "canonical-workflow-host-copy"), preparation["commands"]):
    receipt_path = evidence / (label + ".command.json")
    command = json.loads(receipt_path.read_bytes())
    assert command["returncode"] == item["returncode"] == 0
    assert command["owned_group_drained"] is True
    assert digest(receipt_path) == item["receiptSHA256"]
    assert digest(evidence / (label + ".log")) == command["log_sha256"]
identity = json.loads((controls / "source-identity.json").read_bytes())
assert digest(controls / "source-identity.json") == "dca879b7fbbedf2f0243b7f3d90363ec5b6c468d82a49935de9219b1e38602a2"
expected_diff = (controls / "source-preparation.diff").read_bytes()
assert hashlib.sha256(expected_diff).hexdigest() == "863bf97e4b83fe9824be5345a7fcb2453f403a50d16ce3fdbc0c1c978b5482ab"
def verify_source():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=20).strip() == source_sha
    assert subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=root, timeout=20) == expected_diff
    assert len(identity["tracked_file_sha256"]) == 7693
    changed = [name for name, expected in identity["tracked_file_sha256"].items() if digest(root / name) != expected]
    assert not changed, changed
    assert digest(root / "Config.xcconfig") == config_sha
verify_source()
generated = root / "build/runtime-host/RuntimeHostResources.zip"
assert digest(original_host) == host_sha
assert digest(generated) == "0ca372ad4cd751a664ff8819af1f9ca5fd385da7daa009c90c318db47d2a4f5b"
assert digest(root / "AI_HLY/RuntimeHostResources.zip") == digest(generated)
old_paths = (
    b"/Users/m1/builds/hanlin-ai-cache-native-20261125/Scripts/Expo",
    b"/Users/m1/builds/hanlin-miniapps-final-native-20261125/Scripts/NativeScript",
)
new_paths = (
    str(root / "Scripts/Expo").encode(),
    str(root / "Scripts/NativeScript").encode(),
)
with zipfile.ZipFile(original_host) as original, zipfile.ZipFile(generated) as current:
    old_names, new_names = original.namelist(), current.namelist()
    assert len(old_names) == len(set(old_names)) == 28791
    assert len(new_names) == len(set(new_names)) == 28791
    assert set(old_names) == set(new_names)
    for name in sorted(old_names):
        old, new = original.read(name), current.read(name)
        if name == "MiniAppSDK/miniapp-sdk.json":
            expected = old
            for old_path, new_path in zip(old_paths, new_paths):
                assert expected.count(old_path) == new.count(new_path) == 1
                expected = expected.replace(old_path, new_path)
            assert expected == new, "Unexpected runtime SDK descriptor content change"
        else:
            assert old == new, name
backup = evidence / "regenerated-runtime-host.zip"
assert not backup.exists()
shutil.copy2(generated, backup)
assert digest(backup) == digest(generated)
# The qualified canonical archive includes the exact original descriptor provenance.
# Restore it only after proving the regeneration changed those two directory strings.
shutil.copy2(original_host, generated)
assert digest(generated) == digest(original_host) == host_sha
assert digest(controls / "owned_commands.py") == "e26589b62e3c69db67e534b3ecf42eb6342983e9c581474d9228f1bcc0e62f34"
sys.path.insert(0, str(controls))
from owned_commands import run_logged
os.environ.update(
    PATH="/Users/m1/builds/_preflight/native-owned-node245-20261125/node-v24.5.0-darwin-arm64/bin:/opt/homebrew/opt/python@3.12/libexec/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",
    PYTHONDONTWRITEBYTECODE="1",
)
host_log = (evidence / "prepare-runtime-core.log").read_text(errors="strict")
host_counts = dict((key, int(value)) for key, value in re.findall(r"^ℹ (tests|pass|fail|skipped) (\d+)$", host_log, re.MULTILINE))
assert host_counts == {"tests": 178, "pass": 177, "fail": 0, "skipped": 1}, host_counts
state = {
    "schema": "miniapps.original-runtime-finalization/1",
    "status": "RUNNING",
    "source": source_sha,
    "originalPreparationSHA256": hashlib.sha256(preparation_raw).hexdigest(),
    "originalFailurePreserved": True,
    "helperSHA256": digest(__file__),
    "generatedArchiveSHA256": digest(backup),
    "qualifiedCanonicalArchiveSHA256": host_sha,
    "zipEntriesVerified": 28791,
    "onlyGeneratedPayloadDifference": {
        "entry": "MiniAppSDK/miniapp-sdk.json",
        "oldPaths": [p.decode() for p in old_paths],
        "newPaths": [p.decode() for p in new_paths],
        "exactTwoStringSubstitutionVerified": True,
    },
    "commands": preparation["commands"],
    "appBuilds": 0, "nativeTestsExecuted": 0, "hostPreparationTests": host_counts,
    "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
}
try:
    argv = ["/bin/cp", "build/runtime-host/RuntimeHostResources.zip", "AI_HLY/RuntimeHostResources.zip"]
    result = run_logged(argv, root, evidence / "qualified-canonical-host-copy.log", 60)
    assert result.returncode == 0
    assert digest(root / "AI_HLY/RuntimeHostResources.zip") == host_sha
    argv = ["/bin/bash", "Scripts/Runtime/preflight-runtime-core.sh"]
    result = run_logged(argv, root, evidence / "preflight-runtime-core.log", 180)
    state["commands"].append({"label": "original-preflight-runtime-core", "argv": argv,
                              "returncode": result.returncode,
                              "receiptSHA256": digest(evidence / "preflight-runtime-core.command.json")})
    assert result.returncode == 0, ("Original RuntimeCore preflight failed", result.returncode)
    verify_source()
    assert (evidence / "RESULT.json").read_bytes() == preparation_raw
    state["nativeFiles"] = {}
    for name in [
        "Vendor/NodeMobile/NodeMobile.xcframework/Info.plist",
        "Vendor/NodeMobile/NodeMobile.xcframework/ios-arm64/NodeMobile.framework/NodeMobile",
        "Vendor/NodeMobile/NodeMobile.xcframework/ios-arm64-simulator/NodeMobile.framework/NodeMobile",
        "Vendor/Python/Python.xcframework/Info.plist",
        "Vendor/Python/Python.xcframework/ios-arm64/Python.framework/Python",
        "Vendor/Python/Python.xcframework/ios-arm64_x86_64-simulator/Python.framework/Python",
        "Vendor/Python/Python.xcframework/build/utils.sh",
        "Vendor/Python/Python.xcframework/build/iOS-dylib-Info-template.plist",
        "Vendor/Python/Python-VERSIONS",
    ]:
        path = root / name
        state["nativeFiles"][name] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    state.update(status="ORIGINAL_RUNTIME_CORE_PREPARED_AND_PREFLIGHT_PASS_BUILD_NOT_RUN",
                 sourceFilesVerified=7693, canonicalHostSHA256=host_sha,
                 configurationSHA256=config_sha, sourceAndOriginalDiffUnchanged=True)
except BaseException as error:
    state.update(status="FAILED", error=repr(error))
    raise
finally:
    state["finishedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state["freeBytesAfter"] = shutil.disk_usage(root).free
    final.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({k:state.get(k) for k in ["status","error","source","sourceFilesVerified","zipEntriesVerified","commands","appBuilds","nativeTestsExecuted","hostPreparationTests"]}), flush=True)
