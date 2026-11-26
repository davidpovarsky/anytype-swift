"""Finish exact original App14 retention with the actual tracked immutable-manifest locator."""
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
SOURCE = "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
RECEIPT = "b6b3ba75809a9bebe6fbf2dbf77149def27cb1eabe1771f9d5d73108c56e00d6"
SOURCE_MANIFEST = "fe01408dac1397de8aef9e1eb8a16d9bf637cd30303404bbca1810bede58f959"
PRODUCTS = "1941073f958baf7285b83ed411aef2b1a0d5dee75c2ff830510fb47b50d60109"
CORE = "59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de"
BASE = Path("/Users/m1/development/anytype-d-active-20261125/main14")
DESTINATION = Path("/Users/m1/development/anytype-e-active-20261125/main14/frozen-original")


def main():
    own = Path(__file__).resolve().parent
    core = own / "combined_heart_semantics_current.py"
    assert hashlib.sha256(core.read_bytes()).hexdigest() == CORE
    spec = importlib.util.spec_from_file_location("current_core", core)
    c = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = c
    spec.loader.exec_module(c)
    c.require(DESTINATION.is_dir() and DESTINATION.resolve() == DESTINATION,
              "Exact existing original clone required")
    c.require(c.digest(DESTINATION / "freeze-receipt.json") ==
              "0091bfd64587372178b4fa7b5c456b2c14b64a249d8f8080650297f6b70643d1",
              "Original copy failure must remain exact")
    failed = c.decode(c.raw(DESTINATION / "freeze-receipt.json"))
    c.require(failed["status"] == "FAIL" and failed["sourceCommit"] == SOURCE
              and failed["firstFailure"] == {"type": "ValueError", "message": "Complete generated UI source changed while retaining"}
              and failed["testsExecuted"] == failed["engineCalls"] == failed["simulatorOperations"] == failed["builds"] == 0,
              "Only the actual generated-directory copy mismatch is admitted")
    c.require(not (DESTINATION / "app-products").exists() and not (DESTINATION / "ui-products").exists(),
              "No products were copied by the failed attempt")
    c.require(c.digest(DESTINATION / "freeze-continuation-receipt.json") ==
              "e50892b0e035547cd32f16c78ed01400e7e6a794ac170965e72174f56a233828",
              "Original legacy-locator refusal must remain unchanged")
    prior = c.decode(c.raw(DESTINATION / "freeze-continuation-receipt.json"))
    c.require(prior["status"] == "FAIL" and prior["firstFailure"] ==
              {"type": "ValueError", "message": "Cloned native source/library differ"}
              and prior["sourceCommit"] == SOURCE
              and prior["testsExecuted"] == prior["engineCalls"] == prior["simulatorOperations"] == prior["builds"] == 0,
              "Only the observed original410b-manifest locator failure is admitted")
    c.require(c.digest(DESTINATION / "source/Tools/PinkhaDualEngineRuntime/source-manifest.json") ==
              "410b441e5726b4a2ff7b259e296ad2ba819a5751cd46732945f62259ace42cc9",
              "Historical source manifest must remain unchanged")

    c.require(shutil.disk_usage(DESTINATION.parent).free >= 3 * 1024**3,
              "APFS source/products retention allowance plus 2 GiB emergency floor")
    os.umask(0o022)  # Preserve original directory modes in cp-cR; enclosing root is private.
    result = {"status": "FAIL", "sourceCommit": SOURCE, "testsExecuted": 0,
              "builds": 0, "engineCalls": 0, "simulatorOperations": 0,
              "startedAt": time.time(), "freeBytesBefore": shutil.disk_usage(DESTINATION).free}
    try:
        original = BASE / "build14"
        for name, expected_pin in (("receipt.json", RECEIPT), ("source-before.json", SOURCE_MANIFEST),
                          ("source-after.json", SOURCE_MANIFEST), ("products-all.json", PRODUCTS)):
            c.require(c.digest(original / name) == expected_pin, "Original producer pin differs: " + name)
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
        c.source_admission(BASE / "source", SOURCE, producer, DESTINATION / "locator-before-helpers")
        commands = c.Commands(DESTINATION / "locator-commands", DESTINATION)
        c.source_admission(DESTINATION / "source", SOURCE, producer, DESTINATION / "locator-after-helpers")
        bundle = own / "external-producer-b9e9.bundle"
        c.require(c.digest(bundle) == "1c41078815eaab6a3fb42f302e42bd8eb1e60195c7fbe1c53f4e4580f628b793",
                  "Exact external producer Git bundle required")
        c.require(subprocess.check_output(["git", "-C", str(DESTINATION / "source"), "rev-parse",
                  "refs/retained/app14-producer"], timeout=60).decode().strip() ==
                  "b9e9d2f3cce9adfe6ffd45a6cce6c19f8bbce421", "Original retained producer Git object differs")
        producer_commit = "b9e9d2f3cce9adfe6ffd45a6cce6c19f8bbce421"
        external = {"commit": producer_commit}
        for field, name in (("controller", "Tools/PinkhaDualEngineRuntime/build_main_immutable.py"),
                            ("delta", "docs/validation/20261126-native11619-apple-slices/app14-controller-delta.json")):
            value = subprocess.check_output(["git", "-C", str(DESTINATION / "source"), "show", producer_commit + ":" + name], timeout=60)
            target = DESTINATION / "external-producer" / Path(name).name
            c.require(c.raw(target) == value, "Original retained producer bytes differ")
            external[field] = pin(c, target)
        external_proof = c.qualify_external_producer(
            {"externalProducer": external, "sourceCommit": SOURCE}, DESTINATION / "source", receipt)
        ui_copy = original / "original-ui-copy.json"
        c.require(c.digest(ui_copy) == "be4b6678269a7789a483b7cc7078a2a9e1957d164efdb114c143de1ab1856229",
                  "Exact complete original UI source copy required")
        ui_copy_data = c.decode(c.raw(ui_copy))
        c.require(ui_copy_data["generatorSHA256"] == "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
                  and len(ui_copy_data["copiedFiles"]) == 12, "Original full UI source identity differs")
        generated = BASE / "ui-source-build14"
        for row in ui_copy_data["copiedFiles"]:
            name = row["path"]
            copied = generated / name
            source_path = DESTINATION / "source" / name
            c.require(c.digest(copied) == row["sha256"] == c.digest(source_path),
                      "Original copied UI source differs: " + name)
        before_ui = c.inventory(generated)
        failed_copy = c.inventory(DESTINATION / "original-ui-source")
        directory_names = {
            "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj/project.xcworkspace",
            "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj/project.xcworkspace/xcshareddata",
            "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj/project.xcworkspace/xcshareddata/swiftpm",
            "PinkhaStage1Acceptance/PinkhaPrebuiltUI.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/configuration"}
        differences = {name for name in set(before_ui) | set(failed_copy) if before_ui.get(name) != failed_copy.get(name)}
        c.require(differences == directory_names and len(before_ui) == len(failed_copy) == 27,
                  "Original failure is not the exact four generated-directory modes")
        for name in directory_names:
            c.require(before_ui[name] == {"kind": "directory", "mode": 0o777}
                      and failed_copy[name] == {"kind": "directory", "mode": 0o755},
                      "Original observed generated-directory mode transition differs")
        c.require(c.decode(c.raw(DESTINATION / "original-generated-copy-failure.json")) ==
                  {"original": before_ui, "failedCopy": failed_copy, "modeDifferences": sorted(differences)},
                  "Original observed directory-mode failure differs")
        c.require((DESTINATION / "original-ui-source-preserved").is_dir(),
                  "Prior exact mode-preserving copy is required")
        c.require(c.inventory(generated) == before_ui == c.inventory(DESTINATION / "original-ui-source-preserved"),
                  "Complete generated UI source changed while retaining")
        c.require(c.decode(c.raw(DESTINATION / "original-ui-source-inventory.json")) == before_ui, "Retained generated UI source inventory differs")
        c.require(c.digest(DESTINATION / "source/Tools/PinkhaDualEngineRuntime/source-immutable-manifest.json") == c.MANIFEST
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
                      externalProducer=external_proof, finishedAt=time.time())
        c.write(DESTINATION / "freeze-source-locator-receipt.json", result)
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
                     "immutableCloneReceipt": pin(c, DESTINATION / "freeze-source-locator-receipt.json"),
                     "originalLocatorFailure": pin(c, DESTINATION / "freeze-continuation-receipt.json"),
                     "originalFreezeFailure": pin(c, DESTINATION / "freeze-receipt.json"), "products": manifests,
                     "externalProducer": external,
                     "originalUICopy": pin(c, retained / "original-ui-copy.json")}
        path = own / "admission76f59.json"
        c.write(path, admission)
        print(json.dumps({"status": result["status"], "receipt": pin(c, DESTINATION / "freeze-source-locator-receipt.json"),
                          "admission": pin(c, path), "sourceFiles": result["sourceFiles"],
                          "originalProductFiles": result["originalProductFiles"]}, sort_keys=True), flush=True)
    except BaseException as exc:
        result.update(firstFailure=c.error(exc), finishedAt=time.time())
        if not (DESTINATION / "freeze-source-locator-receipt.json").exists():
            c.write(DESTINATION / "freeze-source-locator-receipt.json", result)
        raise


def pin(c, path):
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": c.digest(path)}


if __name__ == "__main__":
    main()
