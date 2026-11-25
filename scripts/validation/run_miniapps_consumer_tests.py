#!/usr/bin/env python3
"""Run only the new Anytype MiniApps planner tests against the real bridge package."""
import argparse
import json
import pathlib
import shutil
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--bridge-package", type=pathlib.Path)
args = parser.parse_args()
repo = pathlib.Path(__file__).resolve().parents[2]
bridge = (args.bridge_package or repo / "Dependencies/Hanlin/Packages/HanlinMiniAppsBridge").resolve()
if not (bridge / "Package.swift").is_file():
    raise SystemExit(f"Bridge package missing: {bridge}")
with tempfile.TemporaryDirectory(prefix="anytype-miniapps-tests-") as work:
    root = pathlib.Path(work)
    source = root / "Sources/MiniAppsConsumerPlanner"
    tests = root / "Tests/MiniAppsConsumerPlannerTests"
    source.mkdir(parents=True)
    tests.mkdir(parents=True)
    shutil.copy2(repo / "Anytype/Sources/Pinkha/MiniApps/PinkhaMiniAppsEditPlan.swift", source)
    shutil.copy2(repo / "AnytypeTests/PinkhaMiniAppsEditPlannerTests.swift", tests)
    manifest = """// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "MiniAppsConsumerPlannerChecks",
    platforms: [.iOS(.v17), .macOS(.v14)],
    dependencies: [.package(path: BRIDGE_PATH)],
    targets: [
        .target(name: "MiniAppsConsumerPlanner",
            dependencies: [.product(name: "HanlinMiniAppsBridge", package: "HanlinMiniAppsBridge")]),
        .testTarget(name: "MiniAppsConsumerPlannerTests",
            dependencies: ["MiniAppsConsumerPlanner",
                .product(name: "HanlinMiniAppsBridge", package: "HanlinMiniAppsBridge")])
    ])
"""
    (root / "Package.swift").write_text(manifest.replace("BRIDGE_PATH", json.dumps(str(bridge))))
    subprocess.run(["swift", "test", "--package-path", str(root), "--filter", "PinkhaMiniAppsEditPlannerTests"], check=True)
