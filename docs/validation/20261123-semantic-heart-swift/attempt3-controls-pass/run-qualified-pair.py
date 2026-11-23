#!/usr/bin/env python3
"""Adopt the already compiled Swift 6.4 runner/module; execute only the new 22."""
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import json
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from types import SimpleNamespace

WORK = Path("/mnt/development/projects/worktrees/anytype-wave15-semantic-swift-20261123")
RUN = Path("/mnt/development/projects/evidence/semantic-anchor-swift-20261123/attempt3")
BASE = RUN.parent
EVIDENCE = RUN / "evidence"
SOURCE = "fbbfe7100425482e3d9f8b6623bb2d1920f56528"
controller_path = WORK / "Tools/PinkhaSemanticAnchorSwiftControls/run_controls.py"
spec = importlib.util.spec_from_file_location("semantic_controls", controller_path)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
args = SimpleNamespace(run=RUN, package=BASE / "attempt1/package",
    build_root=Path("/mnt/development/build-cache/semantic-anchor-swift-20261123"),
    shared_cache=Path("/mnt/development/build-cache/anytype-inline-swift-20261123"),
    expected_app_sha=SOURCE)
receipt = {"status": "PROBE_UNKNOWN", "app_sha": SOURCE, "actual_methods_executed": 0,
    "actual_methods_passed": 0, "started_at": datetime.now(timezone.utc).isoformat(),
    "native_sdk_body": "INACTIVE_NOT_TYPECHECKED", "native_sdk_call": "NOT_RUN",
    "mounted_editor": "NOT_RUN", "app_capability": "OFF"}
exit_code = 1
try:
    manifest = controller.verify(args)
    original = controller.read(EVIDENCE / "build.json")
    controller.require(original["status"] == "FAIL_BUILD"
        and original["error"] == "Expected one Linux XCTest executable"
        and original["app_sha"] == SOURCE
        and original["command"]["exit_code"] == 0
        and controller.digest(EVIDENCE / "build.log") == original["command"]["log_sha256"],
        "Only the exact successful compile with known product-layout lookup failure can continue")
    receipt["original_compile_receipt_sha256"] = controller.digest(EVIDENCE / "build.json")
    receipt["original_compile_exit_code"] = 0
    receipt["original_lookup_status_preserved"] = original["status"]
    receipt["source_manifest_sha256"] = controller.digest(EVIDENCE / "source-manifest.json")
    receipt["continuation_controller_sha256"] = controller.digest(Path(__file__))
    receipt["toolchain"] = controller.toolchain()
    receipt["dependencies"] = controller.dependencies(args)
    controller.require(receipt["toolchain"] == original["toolchain"]
        and receipt["dependencies"] == original["dependencies"], "Compiled environment changed")
    binroot = args.build_root / "scratch/out/Products/Debug-linux-aarch64"
    products = {}
    start = datetime.fromisoformat(original["started_at"]).timestamp()
    finish = datetime.fromisoformat(original["finished_at"]).timestamp()
    for name in ("ProtobufMessagesTests-test-runner", "ProtobufMessagesTests.so"):
        p = binroot / name
        controller.require(p.is_file() and p.open("rb").read(4) == b"\x7fELF",
            "Missing actual ELF test runner/module")
        controller.require(start <= p.stat().st_mtime <= finish,
            "Test product was not linked by the recorded successful compile")
        products[name] = {"path": str(p), "sha256": controller.digest(p),
            "bytes": p.stat().st_size, "mtime_ns": p.stat().st_mtime_ns}
        dynamic = subprocess.check_output(["readelf", "-d", str(p)], text=True)
        (EVIDENCE / (name + ".dynamic.txt")).write_text(dynamic)
        if name.endswith("-test-runner"):
            controller.require("Shared library: [ProtobufMessagesTests.so]" in dynamic,
                "Runner does not load the qualified actual test module")
    receipt["compiled_products"] = products
    resources = {}
    bundle = binroot / "PinkhaHeartSemanticAnchorControls_ProtobufMessagesTests.bundle/NativePage"
    for target, row in manifest["files"].items():
        if "/Fixtures/NativePage/" not in target:
            continue
        p = bundle / Path(target).name
        controller.require(p.is_file() and controller.digest(p) == row["sha256"],
            "Compiled native fixture resource differs from exact source")
        resources[str(p)] = row["sha256"]
    receipt["resource_sha256"] = resources
    argv = [controller.SWIFT, "test", *controller.common(args), "--skip-build", "-j", "1",
        "--filter", "PinkhaHeartSemanticAnchor(Wire|Client)Tests"]
    result = controller.command(args, argv, EVIDENCE / "tests.log", 180)
    receipt["command"] = result
    rows = []
    for line in (EVIDENCE / "tests.log").read_text(errors="replace").splitlines():
        match = re.search(r"Test Case '([^']+)' (started|passed|failed)", line)
        if not match:
            continue
        name = re.search(r"(PinkhaHeartSemanticAnchor(?:Wire|Client)Tests)[. /]+(test[A-Za-z0-9_]+)", match.group(1))
        controller.require(name is not None, "Unselected XCTest method executed")
        rows.append({"method": name.group(1) + "." + name.group(2), "action": match.group(2)})
    starts = [row["method"] for row in rows if row["action"] == "started"]
    passes = [row["method"] for row in rows if row["action"] == "passed"]
    receipt.update(actual_methods_executed=len(starts), actual_methods_passed=len(passes), named_events=rows)
    controller.require(result["exit_code"] == 0, "A selected Swift control failed")
    controller.require(sorted(starts) == manifest["selected_methods"]
        and sorted(passes) == manifest["selected_methods"] and len(rows) == 44,
        "Incomplete, skipped, duplicate or unselected Swift controls")
    controller.verify(args)
    for row in products.values():
        controller.require(controller.digest(Path(row["path"])) == row["sha256"],
            "Compiled test product changed during execution")
    for path, expected in resources.items():
        controller.require(controller.digest(Path(path)) == expected,
            "Compiled fixture changed during execution")
    receipt["status"] = "PASS_TWENTY_TWO_NEW_SWIFT_CONTROLS"
    exit_code = 0
except BaseException as error:
    receipt.update(status="FAIL_QUALIFIED_CONTINUATION", error_type=type(error).__name__, error=str(error))
finally:
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    target = EVIDENCE / "qualified-test.json"
    controller.require(not target.exists(), "Original continuation receipt cannot be overwritten")
    controller.save(target, receipt)
print(json.dumps({key: receipt.get(key) for key in ("status","actual_methods_executed","actual_methods_passed","error")}))
raise SystemExit(exit_code)
