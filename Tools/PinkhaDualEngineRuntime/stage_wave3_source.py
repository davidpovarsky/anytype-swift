"""Forward-stage one accepted App source while preserving original App15 data.

No compiler, test, simulator, signing operation or cleanup is performed here.
The plan must be explicitly hash-bound and name the accepted Git commit.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

SOURCE = Path("/Users/m1/development/anytype-d-active-20261125/main14/source")
APP_DERIVED = SOURCE.parent / "app-derived"
PRESERVATION_SHA = "11ab2f45511d8b7917709c1706475538b9ea4ed228e1dc908dfa55a331cacc74"
OWNED_HELPER_SHA = "73bb6a4f6dde58faa723c38fddd322b6a6ff356fbbee44ecdeb949a77d358e1a"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require(value, reason):
    if not value:
        raise ValueError(reason)


def write(path, data):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


def git(*arguments):
    return subprocess.check_output(["git", "--no-replace-objects", "-C", str(SOURCE), *arguments], text=True).strip()


def inventory(root):
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), "Physical retained directory required: " + str(root))
    rows = {}
    for path in sorted(root.rglob("*")):
        key = str(path.relative_to(root))
        mode = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            rows[key] = {"kind": "symlink", "mode": mode, "target": os.readlink(path)}
        elif path.is_file():
            rows[key] = {"kind": "file", "mode": mode, "bytes": path.stat().st_size, "sha256": sha(path)}
        elif path.is_dir():
            rows[key] = {"kind": "directory", "mode": mode}
        else:
            raise ValueError("Unknown retained node: " + str(path))
    return rows


def verify_preservation(path):
    path = Path(path)
    require(sha(path) == PRESERVATION_SHA, "Original Wave2 preservation receipt differs")
    receipt = json.loads(path.read_text())
    require(receipt["status"] == "PASS_ORIGINAL_SOURCE_AND_PRODUCTS_BYTES_MODES_LINKS", "Original preservation status differs")
    sources = [(Path(receipt["retainedSource"]), path.parent / "original-source-inventory.json", receipt["sourceInventorySHA256"])]
    for name, row in receipt["products"].items():
        sources.append((Path(row["retained"]), path.parent / (name + "-original-inventory.json"), row["inventorySHA256"]))
    result = []
    for root, inventory_path, expected in sources:
        require(sha(inventory_path) == expected, "Original inventory bytes differ")
        rows = json.loads(inventory_path.read_text())
        require(inventory(root) == rows, "Retained original source/products changed: " + str(root))
        result.append({"root": str(root), "inventory": str(inventory_path), "inventorySHA256": expected, "entries": len(rows)})
    # The physical shared App Products are still the exact preserved App15
    # products. The next build may replace them only after this proof is saved.
    app_rows = json.loads((path.parent / "app-derived-original-inventory.json").read_text())
    require(inventory(APP_DERIVED / "Build/Products") == app_rows, "Current shared App Products diverged before forward staging")
    return {"status": "PASS_RETAINED_ORIGINAL_SOURCE_AND_PRODUCTS_REVERIFIED", "receiptSHA256": sha(path),
            "inventories": result, "currentAppProductsEqualOriginal": True}


def no_compiler_or_queue():
    output = subprocess.check_output(["ps", "-axo", "pid=,ppid=,args="], text=True)
    conflicts = []
    for line in output.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) != 3 or int(parts[0]) == os.getpid():
            continue
        command = parts[2]
        compiler = any(value in command for value in ("xcodebuild", "swift-frontend", "/swiftc", "/clang", "XCBBuildService"))
        shared_path = str(SOURCE) in command or str(APP_DERIVED) in command
        old_queue = "main16-wave2-20261127/control/launch_app16_when_compiler_admitted.py" in command
        if (compiler and shared_path) or old_queue:
            conflicts.append(line)
    require(not conflicts, "Shared compiler or superseded queue is still active")
    database = APP_DERIVED / "Build/Intermediates.noindex/XCBuildData/build.db"
    if database.exists():
        observed = subprocess.run(["/usr/sbin/lsof", str(database)], capture_output=True, text=True, timeout=15)
        require(observed.returncode == 1 and not observed.stdout, "Shared Xcode database still has an owner")
    return {"scopedCompilerOrQueueProcesses": [], "databasePresent": database.exists(), "observedAt": time.time()}


def native_files(root):
    rows = {}
    for path in sorted(Path(root).rglob("*")):
        require(not path.is_symlink(), "Native framework symlink is not admitted")
        if path.is_file():
            rows[str(path.relative_to(root))] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--accepted-source", required=True)
    args = parser.parse_args()
    require(re.fullmatch("[0-9a-f]{64}", args.plan_sha256) and sha(args.plan) == args.plan_sha256, "Exact staging plan bytes required")
    plan = json.loads(args.plan.read_text())
    require(plan["schema"] == "pinkha-root-forward-staging-plan-v1" and plan["readyForStaging"] is True, "Finalized staging plan required")
    require(re.fullmatch("[0-9a-f]{40}", args.accepted_source) and plan["appSourceSHA"] == args.accepted_source, "Root accepted source differs")
    require(plan["sourceRoot"] == str(SOURCE) and plan["appDerived"] == str(APP_DERIVED), "Unreviewed physical source/cache path")
    root = Path(plan["buildRoot"])
    require(root.parent == SOURCE.parent.parent and root.name.startswith("main16-wave3-"), "A separate Wave3 output root is required")
    require(not root.exists() and not root.is_symlink(), "Existing Wave3 evidence cannot be overwritten")
    require(SOURCE.is_dir() and not SOURCE.is_symlink(), "Original physical source is absent")
    require(git("rev-parse", "HEAD") == plan["previousSourceSHA"] and git("status", "--porcelain") == "", "Original source HEAD/status changed")
    require(sha(plan["gitBundle"]["path"]) == plan["gitBundle"]["sha256"], "Forward Git bundle bytes differ")
    require(sha(plan["buildAdmissionTemplate"]["path"]) == plan["buildAdmissionTemplate"]["sha256"], "Build admission template differs")
    require(sha(plan["ownedLifecycleHelper"]["path"]) == OWNED_HELPER_SHA, "Original owned-process helper differs")
    before_owners = no_compiler_or_queue()
    preserved = verify_preservation(plan["originalPreservationReceipt"])
    require(json.loads(Path(plan["queueStopReceipt"]["path"]).read_text())["status"] == "STOPPED_SUPERSEDED_QUEUE"
            and sha(plan["queueStopReceipt"]["path"]) == plan["queueStopReceipt"]["sha256"], "Superseded queue stop proof differs")
    # The preserved source, dependency materializations and products were all
    # re-read before the first mutation below. No historical source is restored.
    no_compiler_or_queue()
    root.mkdir(mode=0o700)
    stage = root / "source-staging1"
    stage.mkdir()
    started = time.time()
    free_before = shutil.disk_usage(root).free
    report = {"protocol": "pinkha-root-forward-staging-v1", "started": started,
              "planSHA256": args.plan_sha256, "sourceCommit": args.accepted_source,
              "priorSource": plan["previousSourceSHA"], "applicationBuilds": 0, "nativeBuilds": 0, "tests": 0,
              "sourceRoot": str(SOURCE), "appDerived": str(APP_DERIVED), "uiDerived": str(root / "ui-derived")}
    try:
        write(stage / "preservation-reverified.json", preserved)
        write(stage / "owners-before.json", before_owners)
        subprocess.run(["git", "-C", str(SOURCE), "bundle", "verify", plan["gitBundle"]["path"]], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(SOURCE), "fetch", "--no-tags", plan["gitBundle"]["path"], args.accepted_source], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(SOURCE), "merge-base", "--is-ancestor", plan["previousSourceSHA"], args.accepted_source], check=True)
        no_compiler_or_queue()
        require(git("rev-parse", "HEAD") == plan["previousSourceSHA"] and git("status", "--porcelain") == "", "Source changed before forward merge")
        subprocess.run(["git", "-C", str(SOURCE), "merge", "--ff-only", "--no-edit", args.accepted_source], check=True, capture_output=True)
        require(git("rev-parse", "HEAD") == args.accepted_source and git("status", "--porcelain") == "", "Fast-forward did not produce exact accepted source")
        pins = plan["pins"]
        require(sha(SOURCE / "Tools/Hanlin/prepare_sdk.py") == pins["sdkMaterializerSHA256"], "Canonical SDK materializer differs")
        source_pin = json.loads((SOURCE / "Tools/Hanlin/source.json").read_text())
        require(source_pin["revision"] == plan["sdkRevision"], "Accepted canonical SDK revision differs")
        sdk = SOURCE / "Dependencies/Hanlin"
        marker = sdk / ".pinkha-source.json"
        if marker.exists() and json.loads(marker.read_text())["revision"] != plan["sdkRevision"]:
            require(sha(marker) == plan["priorSDKReceiptSHA256"], "Unexpected prior SDK materialization")
            prior = root / "retained-prior-sdk"
            require(not prior.exists(), "Prior SDK retention path already exists")
            sdk.rename(prior)
            report["retainedPriorSDK"] = {"path": str(prior), "receiptSHA256": sha(prior / ".pinkha-source.json")}
        with (stage / "canonical-sdk-materialization.log").open("xb") as log:
            materialize = subprocess.run([sys.executable, "-B", str(SOURCE / "Tools/Hanlin/prepare_sdk.py"), "--source", plan["hanlinReadOnlySourceRoot"]],
                                         cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, timeout=300)
        require(materialize.returncode == 0, "Canonical SDK materialization failed; original source retained")
        with (stage / "canonical-sdk-check.log").open("xb") as log:
            checked = subprocess.run([sys.executable, "-B", str(SOURCE / "Tools/Hanlin/prepare_sdk.py"), "--check"],
                                     cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT, timeout=60)
        require(checked.returncode == 0, "Canonical SDK check failed")
        native_root = Path(plan["nativeMaterializationRoot"])
        native_receipt = native_root / "receipt.json"
        require(sha(native_receipt) == pins["nativeAssemblyReceiptSHA256"], "Native assembly differs")
        framework_inventory = native_root / "framework-files.json"
        require(sha(framework_inventory) == pins["nativeFrameworkInventorySHA256"], "Native inventory differs")
        require(native_files(SOURCE / "Dependencies/Middleware/Lib.xcframework") == json.loads(framework_inventory.read_text()), "Existing native framework differs; no replacement or rebuild attempted")
        require(sha(SOURCE / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json") == pins["nativeSourceManifestSHA256"], "Native source manifest differs")
        require(sha(SOURCE / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved") == pins["packageResolvedSHA256"], "Package lock differs")
        # The UI cache clone is private to this root; the original cache and
        # Products stay intact for their owners and retained acceptance.
        ui_source = Path(plan["uiDerivedCloneSource"])
        require(ui_source.is_dir() and not ui_source.is_symlink(), "Original UI cache clone source is missing")
        subprocess.run(["/bin/cp", "-cR", str(ui_source), str(root / "ui-derived")], check=True)
        inputs = root / "source-inputs"
        inputs.mkdir()
        shutil.copy2(plan["ownedLifecycleHelper"]["path"], inputs / "combined_heart_semantics_owned_outcomes.py")
        require(sha(inputs / "combined_heart_semantics_owned_outcomes.py") == OWNED_HELPER_SHA, "Original lifecycle helper copy differs")
        require(git("rev-parse", "HEAD") == args.accepted_source and git("status", "--porcelain") == "", "Accepted tracked source changed while staging")
        write(stage / "owners-after.json", no_compiler_or_queue())
        report.update(status="PASS_EXACT_APP16_SOURCE_AND_NATIVE_REUSED_ORIGINALS_RETAINED",
                      finished=time.time(), tree=git("rev-parse", "HEAD^{tree}"), freeBytesBefore=free_before,
                      freeBytesAfter=shutil.disk_usage(root).free, originalPreservationSHA256=PRESERVATION_SHA,
                      originalPreservationReverifiedSHA256=sha(stage / "preservation-reverified.json"),
                      sourceManifestSHA256=pins["nativeSourceManifestSHA256"],
                      canonicalSDKRevision=plan["sdkRevision"], sdkReceiptSHA256=sha(marker),
                      originalIntermediatesAndPackagePathsReused=False, controllerSHA256=sha(__file__))
        write(stage / "receipt.json", report)
        paths = {"intermediates": APP_DERIVED / "Build/Intermediates.noindex",
                 "sourcePackages": APP_DERIVED / "SourcePackages", "sdkModules": APP_DERIVED / "SDKExplicitPrecompiledModules",
                 "products": APP_DERIVED / "Build/Products"}
        observed = {name: {"path": str(path), "exists": path.exists(), "symlink": path.is_symlink()} for name, path in paths.items()}
        require(all(observed[name]["exists"] == present and not observed[name]["symlink"] for name, present in
                    [("intermediates", False), ("sourcePackages", False), ("sdkModules", True), ("products", True)]),
                "Measured cache state changed; a new review is required")
        cache = {"protocol": "app16-observed-cache-requalification-v1", "sourceCommit": args.accepted_source,
                 "stageReceiptSHA256": sha(stage / "receipt.json"), "stageSourceAndNativePreservationRetained": True,
                 "invalidatedStageMetadata": ["originalIntermediatesAndPackagePathsReused"],
                 "originalIntermediatesAndPackagePathsReused": False, "applicationBuilds": 0, "testsExecuted": 0,
                 "observedPaths": observed, "originalApp15IntermediatesBytes": 3713556480,
                 "estimateNewAppPhaseBytes": 6442450944, "emergencyFloorBytes": 2147483648,
                 "concurrentGrowthAllowanceBytes": 536870912, "observedAt": time.time(),
                 "freeBytes": shutil.disk_usage(root).free,
                 "estimateReason": "Existing reviewed 6 GiB App estimate: original 3.46 GiB compiler intermediates plus 2.54 GiB checkout/relink allowance. No claim of a measured future peak."}
        cache_dir = root / "cache-requalification1"
        cache_dir.mkdir()
        write(cache_dir / "receipt.json", cache)
        draft = json.loads(Path(plan["buildAdmissionTemplate"]["path"]).read_text())
        draft.update(readyForBuild=False, appSourceSHA=args.accepted_source, buildRoot=str(root),
                     nativeMaterializationRoot=str(native_root),
                     sourceStaging={"path": str(stage / "receipt.json"), "sha256": sha(stage / "receipt.json")},
                     cacheQualification={"path": str(cache_dir / "receipt.json"), "sha256": sha(cache_dir / "receipt.json")})
        draft["pins"].update(pins)
        draft["pins"]["sdkMaterializationReceiptSHA256"] = sha(marker)
        write(root / "build-admission.draft.json", draft)
        print(json.dumps({"status": report["status"], "stagingReceipt": str(stage / "receipt.json"),
                          "stagingReceiptSHA256": sha(stage / "receipt.json"), "draftAdmission": str(root / "build-admission.draft.json"),
                          "draftAdmissionSHA256": sha(root / "build-admission.draft.json"), "builds": 0, "tests": 0}))
        return 0
    except BaseException as error:
        write(stage / "failure.json", dict(report, status="FAIL_FORWARD_STAGING_PRESERVED", error=repr(error), finished=time.time(),
                                            currentSourceSHA=git("rev-parse", "HEAD"), freeBytes=shutil.disk_usage(root).free))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
