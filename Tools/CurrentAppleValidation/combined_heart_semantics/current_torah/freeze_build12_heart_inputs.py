"""Freeze the original build12 inputs; no simulator, engine, test, or build."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import plistlib
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True
SOURCE = "0c5ffc51cdeb480194fdd4d5e396a602d04d5d78"
RECEIPT = "3375dd50d6855d3e75b95975ec78966ae0e5de5fb64a525fee4c0fae345fe0dc"
SOURCE_MANIFEST = "72de6e06e1da5daf0cec3f09121676debebce614a6b1cdae85c12df034b2a949"
PRODUCTS = "ed0bf4957ba2db59c676878429e006fea950560d24f14d372ac2c5df3d7215b5"
CORE = "ad30f682471c585ac4dcaa7a521b4f00ad607fdecbe2197fdd61b3b9518150c2"
BASE = Path("/Users/m1/builds/pinkha-dual-main-20261125")
DESTINATION = Path("/Users/m1/builds/e-combined-current-20261125/frozen-current0c5f")


def main():
    own = Path(__file__).resolve().parent
    core = own / "combined_heart_semantics_current.py"
    assert hashlib.sha256(core.read_bytes()).hexdigest() == CORE
    spec = importlib.util.spec_from_file_location("current_core", core)
    c = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = c
    spec.loader.exec_module(c)
    c.require(not DESTINATION.exists() and DESTINATION.parent.resolve() == DESTINATION.parent,
              "Fresh private immutable destination required")
    c.require(shutil.disk_usage(DESTINATION.parent).free >= 3 * 1024**3,
              "APFS source/products retention allowance plus 2 GiB emergency floor")
    os.umask(0o022)  # Preserve original directory modes in cp-cR; enclosing root is private.
    DESTINATION.mkdir(mode=0o700)
    result = {"status": "FAIL", "sourceCommit": SOURCE, "testsExecuted": 0,
              "builds": 0, "engineCalls": 0, "simulatorOperations": 0,
              "startedAt": time.time(), "freeBytesBefore": shutil.disk_usage(DESTINATION).free}
    try:
        original = BASE / "build12"
        for name, pin in (("receipt.json", RECEIPT), ("source-before.json", SOURCE_MANIFEST),
                          ("source-after.json", SOURCE_MANIFEST), ("products-all.json", PRODUCTS)):
            c.require(c.digest(original / name) == pin, "Original producer pin differs: " + name)
        receipt = c.decode(c.raw(original / "receipt.json"))
        producer = c.decode(c.raw(original / "source-before.json"))
        c.require(receipt["sourceCommit"] == SOURCE and receipt["sourceUnchanged"] is True
                  and receipt["status"] == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
                  and receipt["testsExecuted"] == 0, "Original complete App/UI producer required")
        inputs = receipt["inputs"]
        c.require(inputs["lockSHA256"] == c.LOCK and inputs["nativeSourceManifestSHA256"] == c.MANIFEST
                  and inputs["nativeSHA256"] == c.NATIVE_BINARY and inputs["sdkReceiptSHA256"] == c.SDK_RECEIPT,
                  "Exact current source/dependency closure required")
        for kind in ("app", "ui"):
            row = receipt[kind]
            c.require(row["status"] == "PASS_BUILD_EXIT_0" and row["exitCode"] == 0
                      and row["sourceCommit"] == SOURCE and row["ownedProcessGroup"] == "ABSENT_ESRCH",
                      "Original successful ended producer required")
            log = original / kind / "original.log"
            c.require(c.digest(log) == row["logSHA256"] and log.stat().st_size == row["logBytes"],
                      "Original producer log changed")
        c.source_admission(BASE / "source", SOURCE, producer, DESTINATION / "before-helpers")
        commands = c.Commands(DESTINATION / "commands", DESTINATION)
        commands.run(["cp", "-cR", str(BASE / "source"), str(DESTINATION / "source")], "clone-source", 180)
        commands.run(["cp", "-cR", str(original), str(DESTINATION / "original-producer")], "clone-producer-originals", 180)
        c.source_admission(DESTINATION / "source", SOURCE, producer, DESTINATION / "after-helpers")
        c.require(c.digest(DESTINATION / "source/Tools/PinkhaDualEngineRuntime/source-manifest.json") == c.MANIFEST
                  and c.digest(DESTINATION / "source/Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib") == c.NATIVE_BINARY,
                  "Cloned native source/library differ")
        full = c.decode(c.raw(original / "products-all.json"))
        manifests = {}
        descriptors = {"app": "Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun",
                       "ui": "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun"}
        for kind in ("app", "ui"):
            scope = kind + "-derived"
            source = BASE / scope / "Build/Products"
            inventory = c.inventory(source)
            files = {name: {k: v for k, v in row.items() if k != "mode"}
                     for name, row in inventory.items() if row["kind"] != "directory"}
            expected = {row["path"]: {k: v for k, v in row.items() if k != "path"}
                        for row in full[scope]["entries"]}
            c.require(files == expected, "Complete original producer inventory differs")
            destination = DESTINATION / (kind + "-products")
            commands.run(["cp", "-cR", str(source), str(destination)], "clone-" + kind + "-products", 180)
            c.require(c.inventory(destination) == inventory and c.inventory(source) == inventory,
                      "Original/APFS copy changed during immutable retention")
            manifest = DESTINATION / (kind + "-original-products.json")
            c.write(manifest, inventory)
            descriptor = destination / descriptors[kind]
            parsed = plistlib.loads(c.raw(descriptor))
            if kind == "app":
                targets = parsed["TestConfigurations"][0]["TestTargets"]
                matches = [x for x in targets if x["BlueprintName"] == "AnytypeTests"]
                c.require(len(matches) == 1, "Exact original native target required")
                target = matches[0]
            else:
                target = parsed["PinkhaStage1AcceptanceUITests"]
            c.require(target.get("OnlyTestIdentifiers", []) == [], "Complete original compiled target required")
            manifests[kind] = {"root": str(destination), "manifest": pin(c, manifest),
                               "descriptorRelativePath": descriptor.name, "descriptorSHA256": c.digest(descriptor),
                               "originalSelection": []}
        for name, expected in (("receipt.json", RECEIPT), ("source-before.json", SOURCE_MANIFEST),
                               ("source-after.json", SOURCE_MANIFEST), ("products-all.json", PRODUCTS)):
            c.require(c.digest(original / name) == expected
                      and c.digest(DESTINATION / "original-producer" / name) == expected,
                      "Producer originals changed during retention")
        c.require(not subprocess.check_output(["git", "-C", str(BASE / "source"), "status", "--porcelain"], timeout=60),
                  "Original source changed during retention")
        result.update(status="PASS_IMMUTABLE_ORIGINAL_INPUTS_NOT_ACCEPTANCE",
                      sourceFiles=len(producer["files"]), originalProductFiles=sum(len(x["entries"]) for x in full.values()),
                      producerReceiptSHA256=RECEIPT, sourceManifestSHA256=SOURCE_MANIFEST,
                      completeProductsSHA256=PRODUCTS, freeBytesAfter=shutil.disk_usage(DESTINATION).free,
                      finishedAt=time.time())
        c.write(DESTINATION / "freeze-receipt.json", result)
        retained = DESTINATION / "original-producer"
        admission = {"schema": "pinkha-combined-heart-semantics-admission-v1",
                     "executionEnvironment": "SentinelX-owned-Mac", "controllerSHA256": CORE,
                     "sourceCommit": SOURCE, "sourceRoot": str(DESTINATION / "source"),
                     "nativeManifestSHA256": c.MANIFEST, "heartOverlaySHA256": c.OVERLAY,
                     "producerReceipt": pin(c, retained / "receipt.json"),
                     "producerLogs": {k: pin(c, retained / k / "original.log") for k in ("app", "ui")},
                     "sourceBefore": pin(c, retained / "source-before.json"),
                     "sourceAfter": pin(c, retained / "source-after.json"),
                     "completeProducerProducts": pin(c, retained / "products-all.json"),
                     "immutableCloneReceipt": pin(c, DESTINATION / "freeze-receipt.json"), "products": manifests}
        path = own / "admission0c5ffc.json"
        c.write(path, admission)
        print(json.dumps({"status": result["status"], "receipt": pin(c, DESTINATION / "freeze-receipt.json"),
                          "admission": pin(c, path), "sourceFiles": result["sourceFiles"],
                          "originalProductFiles": result["originalProductFiles"]}, sort_keys=True), flush=True)
    except BaseException as exc:
        result.update(firstFailure=c.error(exc), finishedAt=time.time())
        if not (DESTINATION / "freeze-receipt.json").exists():
            c.write(DESTINATION / "freeze-receipt.json", result)
        raise


def pin(c, path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": c.digest(path)}


if __name__ == "__main__":
    main()
