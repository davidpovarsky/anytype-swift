#!/usr/bin/env python3
"""Hydrate lock-pinned RuntimeCore using the original producer workflow."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--recovery-root", type=Path, required=True)
args = parser.parse_args()
recovery = args.recovery_root
assert recovery.parent == Path("/Users/m1/development/anytype-root-active-20261125")
assert recovery.resolve() == recovery and recovery.is_dir()
root = recovery / "source"
controls = Path(__file__).resolve().parent
evidence = recovery / "runtime-preparation1"
assert not evidence.exists()
evidence.mkdir()
source_sha = "86a6dde354947be9329fe1e8f4d45a433fe488c4"
host_sha = "540507770659f00b8424b394c0c3857f52001cd13a0dc2bc3b38f313b385303a"
config_sha = "03d96d520f785e34d85b643e31bcb4a424e46e76a81c6b4c245f91eaac3e110f"
bundle = recovery / "runtime-input/hanlin-runtime-2ac91db28c0bee53ae53afae8e30a934e7a23d5c706cc321f7c91cbc68523194.zip"

def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def save(name, value):
    (evidence / name).write_text(json.dumps(value, indent=2) + "\n")

identity = json.loads((controls / "source-identity.json").read_bytes())
assert digest(controls / "source-identity.json") == "dca879b7fbbedf2f0243b7f3d90363ec5b6c468d82a49935de9219b1e38602a2"
assert len(identity["tracked_file_sha256"]) == 7693
expected_diff = (controls / "source-preparation.diff").read_bytes()
assert hashlib.sha256(expected_diff).hexdigest() == "863bf97e4b83fe9824be5345a7fcb2453f403a50d16ce3fdbc0c1c978b5482ab"
def verify_source():
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, timeout=20).strip() == source_sha
    assert subprocess.check_output(["git", "diff", "--binary", "HEAD"], cwd=root, timeout=20) == expected_diff
    changed = [name for name, expected in identity["tracked_file_sha256"].items() if digest(root / name) != expected]
    assert not changed, changed
    assert digest(root / "Config.xcconfig") == config_sha
    assert digest(root / "build/runtime-host/RuntimeHostResources.zip") == host_sha

verify_source()
lock = json.loads((root / "RuntimeDependencies.lock.json").read_bytes())
assert digest(bundle) == lock["runtimeBundle"]["sha256"] == "196a35562a31229b1bcf05afbe49f76470ced90a7fbf0494ecebd5c06d07440f"
assert lock["runtimeBundle"]["artifactDependencyHash"] == "2ac91db28c0bee53ae53afae8e30a934e7a23d5c706cc321f7c91cbc68523194"
original_failed = json.loads((recovery / "producer1/build.command.json").read_bytes())
assert original_failed["returncode"] == 74 and original_failed["owned_group_drained"] is True
assert "Could not resolve package dependencies" in (recovery / "producer1/build.log").read_text(errors="replace")
assert digest(controls / "owned_commands.py") == "e26589b62e3c69db67e534b3ecf42eb6342983e9c581474d9228f1bcc0e62f34"
sys.path.insert(0, str(controls))
from owned_commands import run_logged
os.environ.update(
    PATH="/Users/m1/builds/_preflight/native-owned-node245-20261125/node-v24.5.0-darwin-arm64/bin:/opt/homebrew/opt/python@3.12/libexec/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer",
    PYTHONDONTWRITEBYTECODE="1",
    RUNTIME_CORE_BUNDLE_ARCHIVE=str(bundle),
)
state = {
    "schema": "miniapps.original-runtime-hydration/1",
    "status": "RUNNING",
    "source": source_sha,
    "sourceIdentitySHA256": digest(controls / "source-identity.json"),
    "runtimeBundleSHA256": digest(bundle),
    "runtimeBundleBytes": bundle.stat().st_size,
    "originalBuildFailureSHA256": digest(recovery / "producer1/build.command.json"),
    "originalBuildFailurePreserved": True,
    "helperSHA256": digest(__file__),
    "startedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "freeBytesBefore": shutil.disk_usage(root).free,
    "appBuilds": 0, "testsExecuted": 0, "commands": [],
}
save("RESULT.json", state)
try:
    argv = ["/bin/bash", "Scripts/Runtime/prepare-runtime-core.sh"]
    result = run_logged(argv, root, evidence / "prepare-runtime-core.log", 600)
    state["commands"].append({"label": "original-prepare-runtime-core", "argv": argv, "returncode": result.returncode,
                              "receiptSHA256": digest(evidence / "prepare-runtime-core.command.json")})
    assert result.returncode == 0, ("Original RuntimeCore preparation failed", result.returncode)
    state["originalPreparedHostSHA256"] = digest(root / "AI_HLY/RuntimeHostResources.zip")
    workflow = root / ".github/workflows/validate-app-split.yml"
    assert "cp build/runtime-host/RuntimeHostResources.zip AI_HLY/RuntimeHostResources.zip" in workflow.read_text()
    argv = ["/bin/cp", "build/runtime-host/RuntimeHostResources.zip", "AI_HLY/RuntimeHostResources.zip"]
    result = run_logged(argv, root, evidence / "canonical-workflow-host-copy.log", 60)
    state["commands"].append({"label": "original-canonical-host-copy", "argv": argv, "returncode": result.returncode,
                              "receiptSHA256": digest(evidence / "canonical-workflow-host-copy.command.json")})
    assert result.returncode == 0
    assert digest(root / "AI_HLY/RuntimeHostResources.zip") == host_sha
    argv = ["/bin/bash", "Scripts/Runtime/preflight-runtime-core.sh"]
    result = run_logged(argv, root, evidence / "preflight-runtime-core.log", 180)
    state["commands"].append({"label": "original-preflight-runtime-core", "argv": argv, "returncode": result.returncode,
                              "receiptSHA256": digest(evidence / "preflight-runtime-core.command.json")})
    assert result.returncode == 0, ("Original RuntimeCore preflight failed", result.returncode)
    verify_source()
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
                 sourceFilesVerified=7693, canonicalHostSHA256=host_sha, configurationSHA256=config_sha,
                 sourceAndOriginalDiffUnchanged=True)
except BaseException as error:
    state.update(status="FAILED", error=repr(error))
    raise
finally:
    state["finishedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    state["freeBytesAfter"] = shutil.disk_usage(root).free
    save("RESULT.json", state)
    print(json.dumps({k:state.get(k) for k in ["status","error","source","sourceFilesVerified","commands","appBuilds","testsExecuted"]}), flush=True)
