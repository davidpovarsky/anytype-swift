#!/usr/bin/env python3
"""Stage and run only new full archive semantics, with exact original models.

This is a portable pure-code unit closure. It does not link Heart/Lib, run the
original editor, mint an Owner or qualify native application/COMMIT/ACK behavior.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

PINS = {
    "swift-protobuf": "c6fe6442e6a64250495669325044052e113e990c",
    "zipfoundation": "22787ffb59de99e5dc1fbfe80b19c97a904ad48d",
}
SOURCE_PATHS = [
    "OriginalEditorFramework/OriginalAnnotationNativeArchiveLayout.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeMapKeyGuard.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeSnapshotWire.swift",
    "OriginalEditorFramework/OriginalAnnotationNativeArchiveComparison.swift",
]
PACKET = "docs/pinkha/torah-integration/native-body-comparison-20261122"
parser = argparse.ArgumentParser()
parser.add_argument("--repo-root", required=True)
parser.add_argument("--output-root", required=True)
parser.add_argument("--expected-source-sha", required=True)
parser.add_argument("--expected-swift-version", default="6.4.2")
args = parser.parse_args()
repo = Path(args.repo_root).resolve()
work = Path(args.output_root).resolve()
work.mkdir(parents=True, exist_ok=False)
evidence = work / "evidence"
evidence.mkdir()
package = work / "package"
model_target = package / "Sources/ProtobufMessages"
control_target = package / "Sources/NativeBodySemanticControls"
model_target.mkdir(parents=True)
control_target.mkdir(parents=True)
result = {"started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "expected_source_sha": args.expected_source_sha, "status": "RUNNING",
          "native_executions": 0, "prior_controls_rerun": 0, "commands": [], "source_files": [],
          "scope": "New actual SwiftProtobuf/ZIPFoundation semantic comparator controls with synthetic original-format archives; no engine/Owner/atomic/mapping/ACK acceptance",
          "dependency_pins": PINS, "model_base": "b5162d777e3ebc5c4c0d044e02b52347c0c3dd6e"}


def save():
    (evidence / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")


def run(name, command, timeout):
    start = time.monotonic()
    with (evidence / (name + ".stdout.log")).open("wb") as stdout, (evidence / (name + ".stderr.log")).open("wb") as stderr:
        process = subprocess.Popen(command, cwd=repo, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
            code, timed_out = process.returncode, True
    out = (evidence / (name + ".stdout.log")).read_bytes()
    err = (evidence / (name + ".stderr.log")).read_bytes()
    result["commands"].append({"name": name, "args": command, "exit": code, "timed_out": timed_out,
        "seconds": round(time.monotonic() - start, 3), "stdout_sha256": hashlib.sha256(out).hexdigest(),
        "stderr_sha256": hashlib.sha256(err).hexdigest()})
    save()
    if code != 0 or timed_out:
        raise RuntimeError(name + " failed; preserve diagnostics and do not automatically replay")
    return out


def stage(path, destination, expected_blob=None):
    content = (repo / path).read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
    if expected_blob is not None and blob != expected_blob:
        raise RuntimeError("original source blob mismatch: " + path)
    destination.write_bytes(content)
    result["source_files"].append({"path": path, "git_blob": blob, "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)})


save()
try:
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_source_sha):
        raise RuntimeError("immutable full source SHA required")
    actual = run("source-head", ["git", "rev-parse", "HEAD"], 20).decode().strip()
    if actual != args.expected_source_sha:
        raise RuntimeError("workflow checked out a different source commit")
    result["source_commit"] = actual
    dirty = run("source-status", ["git", "status", "--porcelain", "--untracked-files=no"], 20)
    if dirty.strip():
        raise RuntimeError("tracked source is modified")
    swift = run("swift-version", ["swift", "--version"], 30).decode()
    if not re.search(r"\bSwift version " + re.escape(args.expected_swift_version) + r"\b", swift):
        raise RuntimeError("observed runner Swift version differs from the reviewed version")
    result["swift_version"] = swift
    run("zlib-version", ["pkg-config", "--modversion", "zlib"], 20)
    models = json.loads((repo / PACKET / "controls/generated-models.json").read_text())
    expected_models = {row["path"] for row in models}
    actual_models = {str(path.relative_to(repo)) for path in (repo / "Modules/ProtobufMessages/Sources/Protocol/Models").glob("*.swift")}
    if actual_models != expected_models or len(models) != 197:
        raise RuntimeError("original generated model inventory changed")
    for item in models:
        stage(item["path"], model_target / Path(item["path"]).name, item["git_blob"])
    for path in SOURCE_PATHS:
        stage(path, control_target / Path(path).name)
    stage(PACKET + "/controls/NativeBodySemanticControls.swift", control_target / "NativeBodySemanticControls.swift")
    manifest = '''// swift-tools-version:6.0
import PackageDescription
let package = Package(
    name: "NativeBodySemanticControls",
    products: [.executable(name: "NativeBodySemanticControls", targets: ["NativeBodySemanticControls"])],
    dependencies: [
        .package(url: "https://github.com/apple/swift-protobuf", revision: "c6fe6442e6a64250495669325044052e113e990c"),
        .package(url: "https://github.com/weichsel/ZIPFoundation", revision: "22787ffb59de99e5dc1fbfe80b19c97a904ad48d")
    ],
    targets: [
        .target(name: "ProtobufMessages", dependencies: [.product(name: "SwiftProtobuf", package: "swift-protobuf")], path: "Sources/ProtobufMessages", swiftSettings: [.swiftLanguageMode(.v6)]),
        .executableTarget(name: "NativeBodySemanticControls", dependencies: ["ProtobufMessages", .product(name: "SwiftProtobuf", package: "swift-protobuf"), .product(name: "ZIPFoundation", package: "ZIPFoundation")], path: "Sources/NativeBodySemanticControls", swiftSettings: [.swiftLanguageMode(.v6)])
    ]
)
'''
    (package / "Package.swift").write_text(manifest)
    (evidence / "Package.swift").write_text(manifest)
    save()
    run("build", ["swift", "build", "--package-path", str(package), "--product", "NativeBodySemanticControls",
                  "--configuration", "debug", "--jobs", "2", "--disable-index-store"], 1200)
    resolved = package / "Package.resolved"
    shutil.copyfile(resolved, evidence / "Package.resolved")
    resolution = json.loads(resolved.read_text())
    actual_pins = {pin["identity"]: pin["state"]["revision"] for pin in resolution["pins"]}
    if actual_pins != PINS:
        raise RuntimeError("dependency resolution differs from exact original pins")
    binary = package / ".build/debug/NativeBodySemanticControls"
    result["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    result["controls"] = json.loads(run("semantic-controls", [str(binary)], 90))
    if result["controls"]["tests_run"] != 30 or result["controls"]["native_executions"] != 0:
        raise RuntimeError("unexpected semantic control result")
    result["status"] = "PASS_PORTABLE_NATIVE_ARCHIVE_SEMANTICS"
except Exception as error:
    result["status"], result["error"] = "FAILED", str(error)
finally:
    result["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save()
    print(json.dumps({"status": result["status"], "source_commit": result.get("source_commit"),
                      "evidence": str(evidence), "error": result.get("error"),
                      "tests_run": result.get("controls", {}).get("tests_run", 0)}))
    if result["status"] == "FAILED":
        raise SystemExit(1)
