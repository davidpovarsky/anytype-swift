"""Freeze the original build15 inputs; no simulator, engine, test, or build."""
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
SOURCE = "379ca3568f247d2fc218ed63df24796d461713c0"
CORE = 'faa65b9dbb0c3976f173fe8878a0bb0a166d414db6ba813163da25c624d8d074'  # Exact original App and separately completed UI proof.
BASE = Path("/Users/m1/development/anytype-d-active-20261125/main15")
DESTINATION = Path("/Users/m1/development/anytype-e-active-20261125/main15/frozen-original")


def main():
    own = Path(__file__).resolve().parent
    core = own / "combined_heart_semantics_current.py"
    assert hashlib.sha256(core.read_bytes()).hexdigest() == CORE
    spec = importlib.util.spec_from_file_location("current_core", core)
    c = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = c
    spec.loader.exec_module(c)
    c.require(isinstance(c.BUILD15_PROOF, dict), "Actual App15 producer not yet pinned")
    RECEIPT = c.BUILD15_PROOF["receipt"]
    SOURCE_MANIFEST = c.BUILD15_PROOF["source"]
    PRODUCTS = c.BUILD15_PROOF["products"]
    c.require(not DESTINATION.exists() and DESTINATION.parent.resolve() == DESTINATION.parent,
              "Fresh private immutable destination required")
    c.require(shutil.disk_usage(DESTINATION.parent).free >= 3 * 1024**3,
              "APFS source/products retention allowance plus 2 GiB emergency floor")
    os.umask(0o077)  # Only each exact clone temporarily uses zero mask inside the private root.
    DESTINATION.mkdir(mode=0o700)
    result = {"status": "FAIL", "sourceCommit": SOURCE, "testsExecuted": 0,
              "builds": 0, "engineCalls": 0, "simulatorOperations": 0,
              "startedAt": time.time(), "freeBytesBefore": shutil.disk_usage(DESTINATION).free}
    try:
        original = BASE / "build15-ui-continuation1"
        original_app = BASE / "build15"
        for name, expected_pin in (("receipt.json", RECEIPT), ("source-before.json", SOURCE_MANIFEST),
                          ("source-after.json", SOURCE_MANIFEST), ("products-all.json", PRODUCTS)):
            c.require(c.digest(original / name) == expected_pin, "Original producer pin differs: " + name)
        receipt = c.decode(c.raw(original / "receipt.json"))
        original_source = Path(receipt["inputs"]["sourceRoot"])
        c.require(original_source == Path("/Users/m1/development/anytype-d-active-20261125/main14/source")
                  and original_source.resolve() == original_source, "Actual warm source path differs")
        producer = c.decode(c.raw(original / "source-before.json"))
        c.require(receipt["sourceCommit"] == SOURCE and receipt["sourceUnchanged"] is True
                  and receipt["status"] == "PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
                  and receipt["protocol"] == "pinkha-app15-original-app-ui-continuation-v1"
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
            log = (original_app if kind == "app" else original) / kind / "original.log"
            c.require(c.digest(log) == row["logSHA256"] and log.stat().st_size == row["logBytes"],
                      "Original producer log changed")
        c.source_admission(original_source, SOURCE, producer, DESTINATION / "before-helpers")
        commands = c.Commands(DESTINATION / "commands", DESTINATION)
        def clone(source, destination, label, timeout):
            c.require(destination.is_relative_to(DESTINATION) and not destination.exists()
                      and DESTINATION.stat().st_mode & 0o777 == 0o700,
                      "Exact-mode clones must stay inside the private root")
            previous_mask = os.umask(0)
            try:
                commands.run(["cp", "-cR", str(source), str(destination)], label, timeout)
            finally:
                os.umask(previous_mask)
        clone(original_source, DESTINATION / "source", "clone-source", 180)
        clone(original, DESTINATION / "original-producer", "clone-ui-continuation-originals", 180)
        clone(original_app, DESTINATION / "original-app-producer", "clone-original-failed-producer", 180)
        c.source_admission(DESTINATION / "source", SOURCE, producer, DESTINATION / "after-helpers")
        bundle = own / "external-producer-08ed.bundle"
        c.require(c.digest(bundle) == "1832f0035eca04b3b62bd880f8bc8a3380c342d73fc3cba4097783d0928e7c16",
                  "Exact external producer Git bundle required")
        commands.run(["git", "-C", str(DESTINATION / "source"), "-c", "maintenance.auto=false", "-c", "gc.auto=0",
                      "fetch", str(bundle), "HEAD:refs/retained/app15-producer"],
                     "retain-external-producer-git", 60)
        producer_commit = "08ed46041a4d45164e000212eb26fd1c98fee966"
        external = {"commit": producer_commit}
        for field, name in (("controller", "Tools/PinkhaDualEngineRuntime/build_main_permission.py"),
                            ("delta", "Tools/PinkhaDualEngineRuntime/build_main_permission_delta.json")):
            value = subprocess.check_output(["git", "-C", str(DESTINATION / "source"), "show", producer_commit + ":" + name], timeout=60)
            target = DESTINATION / "external-producer" / Path(name).name
            c.write_bytes(target, value)
            external[field] = pin(c, target)
        external_proof = c.qualify_external_producer(
            {"externalProducer": external, "sourceCommit": SOURCE}, DESTINATION / "source", receipt)
        continuation_bundle = own / "app15-ui-continuation-fb23.bundle"
        c.require(c.digest(continuation_bundle) == c.APP15_CONTINUATION["bundleSHA256"],
                  "Exact committed UI-continuation Git bundle required")
        commands.run(["git", "-C", str(DESTINATION / "source"), "-c", "maintenance.auto=false", "-c", "gc.auto=0",
                      "fetch", str(continuation_bundle), "HEAD:refs/retained/app15-ui-continuation"],
                     "retain-ui-continuation-git", 60)
        continuation_commit = c.APP15_CONTINUATION["commit"]
        continuation_bytes = subprocess.check_output(["git", "-C", str(DESTINATION / "source"), "show",
            continuation_commit + ":Tools/PinkhaDualEngineRuntime/resume_main_permission_ui.py"], timeout=60)
        continuation_target = DESTINATION / "external-producer/resume_main_permission_ui.py"
        c.require(c.sha(continuation_bytes) == c.APP15_CONTINUATION["controllerSHA256"],
                  "Actual continuation source Git bytes differ")
        c.write_bytes(continuation_target, continuation_bytes)
        file_list = Path(c.APP15_CONTINUATION["fileList"])
        file_list_bytes = c.raw(file_list)
        c.require(c.sha(file_list_bytes) == c.APP15_CONTINUATION["fileListSHA256"],
                  "Original actual AnytypeTests compiler input list differs")
        retained_list = DESTINATION / "original-compiler-inputs/AnytypeTests.SwiftFileList"
        c.write_bytes(retained_list, file_list_bytes)
        retained = DESTINATION / "original-producer"
        retained_app = DESTINATION / "original-app-producer"
        continuation = {"commit": continuation_commit, "controller": pin(c, continuation_target),
            "admission": pin(c, retained / "admission.json"),
            "compilerInputs": pin(c, retained / "new-uikit-compiler-inputs.json"),
            "compilerFileList": pin(c, retained_list),
            "originalInputs": {name: pin(c, retained_app / name) for name in c.APP15_ORIGINAL_PINS},
            "appProductsBefore": pin(c, retained / "original-app-products-before.json"),
            "appProductsAfter": pin(c, retained / "original-app-products-after.json")}
        for name, expected in c.APP15_ORIGINAL_PINS.items():
            c.require(c.digest(original_app / name) == c.digest(retained_app / name) == expected,
                      "Original failed producer and successful App evidence changed: " + name)
        ui_copy = original / "original-ui-copy.json"
        c.require(c.digest(ui_copy) == c.BUILD15_PROOF["uiCopy"],
                  "Exact complete original UI source copy required")
        ui_copy_data = c.decode(c.raw(ui_copy))
        c.require(ui_copy_data["generatorSHA256"] == "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
                  and len(ui_copy_data["copiedFiles"]) == 12, "Original full UI source identity differs")
        generated = BASE / "ui-source-build15"
        for row in ui_copy_data["copiedFiles"]:
            name = row["path"]
            copied = generated / name
            source_path = DESTINATION / "source" / name
            c.require(c.digest(copied) == row["sha256"] == c.digest(source_path),
                      "Original copied UI source differs: " + name)
        before_ui = c.inventory(generated)
        clone(generated, DESTINATION / "original-ui-source", "clone-original-ui-source", 60)
        c.require(c.inventory(generated) == before_ui == c.inventory(DESTINATION / "original-ui-source"),
                  "Complete generated UI source changed while retaining")
        c.write(DESTINATION / "original-ui-source-inventory.json", before_ui)
        c.require(c.digest(DESTINATION / "source/Tools/PinkhaDualEngineRuntime/source-permission-manifest.json") == c.MANIFEST
                  and c.digest(DESTINATION / "source/Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib") == c.NATIVE_BINARY,
                  "Cloned native source/library differ")
        runtime_pins = {phase: pin(c, DESTINATION / "original-producer" / ("runtime-identity-" + phase + ".json"))
                        for phase in ("before", "after-app", "after-ui")}
        runtime_proof = c.qualify_app15_runtime({"runtimeIdentity": runtime_pins}, DESTINATION / "source")
        full = c.decode(c.raw(original / "products-all.json"))
        manifests = {}
        descriptors = {"app": "Anytype_AnytypeTests_iphonesimulator27.0-arm64.xctestrun",
                       "ui": "PinkhaPrebuiltUI_iphonesimulator27.0-arm64.xctestrun"}
        for kind in ("app", "ui"):
            scope = kind + "-derived"
            source = Path(full[scope]["base"])
            argv = receipt[kind]["argv"]
            c.require(argv.count("-derivedDataPath") == 1, "One actual producer derived-data path required")
            derived = Path(argv[argv.index("-derivedDataPath") + 1])
            c.require(source == derived / "Build/Products" and source.resolve() == source,
                      "Actual recorded source/Products location differs")
            inventory = c.inventory(source)
            files = {name: {k: v for k, v in row.items() if k != "mode"}
                     for name, row in inventory.items() if row["kind"] != "directory"}
            expected = {row["path"]: {k: v for k, v in row.items() if k != "path"}
                        for row in full[scope]["entries"]}
            c.require(files == expected, "Complete original producer inventory differs")
            destination = DESTINATION / (kind + "-products")
            clone(source, destination, "clone-" + kind + "-products", 180)
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
        c.require(not subprocess.check_output(["git", "-C", str(original_source), "status", "--porcelain"], timeout=60),
                  "Original source changed during retention")
        for name, expected in c.APP15_ORIGINAL_PINS.items():
            c.require(c.digest(original_app / name) == c.digest(retained_app / name) == expected,
                      "Original App evidence changed during full retention: " + name)
        continuation_proof = c.qualify_app15_continuation({
            "uiContinuation": continuation, "externalProducer": external,
            "sourceBefore": pin(c, retained / "source-before.json"),
            "sourceAfter": pin(c, retained / "source-after.json"),
            "producerLogs": {"app": pin(c, retained_app / "app/original.log"),
                             "ui": pin(c, retained / "ui/original.log")},
            "runtimeIdentity": runtime_pins, "products": manifests},
            DESTINATION / "source", receipt)
        result.update(status="PASS_IMMUTABLE_ORIGINAL_INPUTS_NOT_ACCEPTANCE",
                      sourceFiles=len(producer["files"]), originalProductFiles=sum(len(x["entries"]) for x in full.values()),
                      producerReceiptSHA256=RECEIPT, sourceManifestSHA256=SOURCE_MANIFEST,
                      completeProductsSHA256=PRODUCTS, freeBytesAfter=shutil.disk_usage(DESTINATION).free,
                      externalProducer=external_proof, uiContinuation=continuation_proof,
                      runtimeIdentity=runtime_proof, finishedAt=time.time())
        c.write(DESTINATION / "freeze-receipt.json", result)
        retained = DESTINATION / "original-producer"
        admission = {"schema": "pinkha-combined-heart-semantics-admission-v1",
                     "executionEnvironment": "SentinelX-owned-Mac", "controllerSHA256": CORE,
                     "sourceCommit": SOURCE, "sourceRoot": str(DESTINATION / "source"),
                     "nativeManifestSHA256": c.MANIFEST, "heartOverlaySHA256": c.OVERLAY,
                     "producerReceipt": pin(c, retained / "receipt.json"),
                     "producerLogs": {"app": pin(c, retained_app / "app/original.log"),
                                      "ui": pin(c, retained / "ui/original.log")},
                     "sourceBefore": pin(c, retained / "source-before.json"),
                     "sourceAfter": pin(c, retained / "source-after.json"),
                     "completeProducerProducts": pin(c, retained / "products-all.json"),
                     "immutableCloneReceipt": pin(c, DESTINATION / "freeze-receipt.json"), "products": manifests,
                     "externalProducer": external, "uiContinuation": continuation, "runtimeIdentity": runtime_pins,
                     "originalUICopy": pin(c, retained / "original-ui-copy.json")}
        path = own / "admission379ca.json"
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
