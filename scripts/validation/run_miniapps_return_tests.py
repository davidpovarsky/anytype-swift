#!/usr/bin/env python3
"""Execute the production callback queue's focused identity/lifecycle regressions."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
evidence = args.evidence.resolve()
evidence.mkdir(parents=True, exist_ok=False)
paths = [
    "Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaMiniAppsReturnQueue.swift",
    "Modules/PinkhaAnyHanlin/Tests/PinkhaAnyHanlinTests/PinkhaMiniAppsReturnQueueTests.swift",
]
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
inputs = {p: digest(repo / p) for p in paths}
receipt = {
    "scope": "Original Foundation callback queue only; no UIKit, native writes, ACK, or two-app acceptance",
    "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
    "tested_worktree_inputs": inputs,
    "started_at": datetime.now(timezone.utc).isoformat(),
    "toolchain": subprocess.check_output(["swift", "--version"], text=True).strip(),
}
(evidence / "started.json").write_text(json.dumps(receipt, indent=2) + "\n")
with tempfile.TemporaryDirectory(prefix="pinkha-miniapps-return-") as temporary:
    work = Path(temporary)
    source = work / "Sources/PinkhaHanlinCore"
    tests = work / "Tests/PinkhaAnyHanlinTests"
    source.mkdir(parents=True)
    tests.mkdir(parents=True)
    shutil.copy2(repo / paths[0], source)
    shutil.copy2(repo / paths[1], tests)
    manifest = """// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "PinkhaMiniAppsReturnChecks",
    targets: [
        .target(name: "PinkhaHanlinCore"),
        .testTarget(name: "PinkhaAnyHanlinTests", dependencies: ["PinkhaHanlinCore"])
    ],
    swiftLanguageModes: [.v6])
"""
    (work / "Package.swift").write_text(manifest)
    (evidence / "Package.swift").write_text(manifest)
    command = ["swift", "test", "--package-path", str(work),
               "--filter", "PinkhaMiniAppsReturnQueueTests",
               "--xunit-output", str(evidence / "tests.xml")]
    receipt["command"] = command
    with (evidence / "original.log").open("w") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, timeout=180)
    receipt["exit_code"] = result.returncode
    receipt["source_unchanged"] = all(digest(repo / p) == h for p, h in inputs.items())
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    receipt["original_log_sha256"] = digest(evidence / "original.log")
    receipt["xml_files"] = {p.name: digest(p) for p in evidence.glob("*.xml")}
    (evidence / "result.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))
    raise SystemExit(result.returncode if receipt["source_unchanged"] else 2)
