#!/usr/bin/env python3
"""Continue only the original Any UI scope after the qualified native 2/2.
Preserve the complete original native Products before the incremental UI build.
The original source/SDK/native binding and the existing derived paths stay exact.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import sys
import uuid

SOURCE = "fbb7b19c3b6c7cbdff8343b0397693a762bc1da2"
BASE_CONTROLLER = "ad9db960f9db5440be19774c95e89cbbc3deac67"
BASE_CONTROLLER_SHA = "341f28c617c1ada9d30b77cc682f652fe2207fff630e6f0ad1ec95685594e59d"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--base-controller", type=Path, required=True)
    parser.add_argument("--controller-commit", required=True)
    args = parser.parse_args()
    source, original, root = args.source.resolve(), args.original.resolve(), args.run_root.resolve()
    assert re.fullmatch("[0-9a-f]{40}", args.controller_commit)
    assert hashlib.sha256(args.base_controller.read_bytes()).hexdigest() == BASE_CONTROLLER_SHA
    spec = importlib.util.spec_from_file_location("qualified_semantic_driver", args.base_controller)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    require, write = base.require, base.write
    require(str(original) == "/Users/m1/builds/any-semantic-20261125/attempt3"
            and str(root).startswith("/Users/m1/builds/any-semantic-20261125/")
            and not root.exists(), "exact_original_and_fresh_owned_root_required")
    require(shutil.disk_usage(root.parent).free >= 4 * 1024**3, "incremental_ui_capacity")
    root.mkdir(mode=0o700)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    commands = base.Commands(source, evidence)
    device = None
    outcome = {"schema": "any-semantic-ui-continuation/v1", "sourceCommit": SOURCE,
               "controllerCommit": args.controller_commit, "controllerSHA256": base.sha(Path(__file__)),
               "baseControllerCommit": BASE_CONTROLLER, "baseControllerSHA256": BASE_CONTROLLER_SHA,
               "nativeTestReruns": 0, "nativeLibraryBuilds": 0,
               "physicalDevice": "NOT_RUN", "status": "RUNNING"}
    write(evidence / "execution.json", outcome)

    def interrupted(signum, frame):
        if commands.active is not None:
            commands.stop(commands.active)
        raise RuntimeError("owned_ui_interrupted:" + str(signum))
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)
    try:
        prior = json.loads((original / "evidence/execution.json").read_text())
        require(prior["sourceCommit"] == SOURCE and prior["controllerCommit"] == BASE_CONTROLLER
                and prior["controllerSHA256"] == BASE_CONTROLLER_SHA
                and prior["failure"]["reason"] == "stage_build_capacity"
                and prior["stages"]["native"]["status"] == "PASS"
                and set(prior["stages"]) == {"native"}, "native_prior_not_exact")
        cleanup = json.loads((original / "evidence/cleanup.json").read_text())
        require(cleanup["status"] == "PASS" and not cleanup["remainingOwnedGroups"], "native_original_not_terminal")
        for name in ("summary", "tests"):
            require(base.sha(original / ("evidence/native/" + name + ".json")) ==
                    prior["stages"]["native"][name + "SHA256"], "native_original_receipt_changed")
        before = base.source_state(source, SOURCE)
        require(before == json.loads((original / "evidence/source-before.json").read_text()), "source_not_qualified_native")
        write(evidence / "source-before.json", before)
        write(original / "evidence/source-after-native-qualification.json", before)
        vendor = source / "Modules/PinkhaAnyRuntime/Vendor"
        native_files = base.inventory(vendor)
        require(native_files == json.loads((original / "evidence/native-binding.json").read_text())["files"],
                "qualified_native_library_changed")
        derived = original / "derived"
        packages = base.dependency_state(derived / "SourcePackages")
        require(packages == json.loads((original / "evidence/dependencies-before.json").read_text()),
                "qualified_dependencies_changed")
        write(evidence / "dependencies-before.json", packages)
        products = derived / "Build/Products"
        native_products = json.loads((original / "evidence/native/original-products.json").read_text())
        require(base.inventory(products) == native_products, "original_native_products_changed")
        saved = original / "evidence/native/retained-original/Build/Products"
        require(not saved.exists(), "native_products_already_retained")
        saved.parent.mkdir(parents=True)
        commands.run(["/bin/cp", "-cR", str(products), str(saved)], "retain-original-native-products", 300)
        require(base.inventory(saved) == native_products and base.inventory(products) == native_products,
                "native_preservation_changed_bytes")
        write(original / "evidence/native/products-retention.json", {
            "originalDerived": str(derived), "retainedProducts": str(saved),
            "productEntries": len(native_products), "originalProductsReceiptSHA256":
                base.sha(original / "evidence/native/original-products.json"),
            "originalXcresult": str(original / "evidence/native/original.xcresult"),
            "originalNativeResult": "PASS_2_OF_2", "sourceCommit": SOURCE,
            "furtherDerivedWritesAreUIContinuationOnly": True})
        os.environ["PINKHA_ANY_NATIVE_ARTIFACT"] = "verified-v1"
        os.environ["ANY_BUILD_VERSION"] = "v0.5.0-pinkha.1"
        os.environ["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"
        runtime = json.loads((original / "evidence/simulator.json").read_text())
        name = "AnySemanticUI-" + uuid.uuid4().hex[:10]
        device = commands.run(["xcrun", "simctl", "create", name, runtime["deviceType"]["identifier"],
                               runtime["runtime"]["identifier"]], "create-owned-ui-simulator").read_text().strip()
        require(re.fullmatch("[A-Fa-f0-9-]{36}", device), "owned_device_id_invalid")
        write(evidence / "simulator.json", {"ownedUDID": device, "name": name,
              "runtime": runtime["runtime"], "deviceType": runtime["deviceType"]})
        commands.run(["xcrun", "simctl", "boot", device], "boot-owned-ui-simulator")
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "wait-owned-ui-boot", 240)
        require(shutil.disk_usage(root).free >= 3 * 1024**3, "ui_build_capacity")
        ui = base.STAGES["ui"]
        selectors = ["-only-testing:" + ui["target"] + "/" + method for method in ui["methods"]]
        destination = "platform=iOS Simulator,id=" + device
        commands.run(["xcodebuild", "build-for-testing", "-jobs", "2",
            "-project", str(source / "NativeApp/AnyNative.xcodeproj"), "-scheme", ui["scheme"],
            "-configuration", "Debug", "-destination", destination, "-derivedDataPath", str(derived),
            "-parallel-testing-enabled", "NO", "-disableAutomaticPackageResolution",
            "-onlyUsePackageVersionsFromResolvedFile", "-resultBundlePath", str(evidence / "build.xcresult"),
            *selectors, "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=YES",
            "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-", "PROVISIONING_PROFILE_SPECIFIER="],
            "ui-incremental-build", 3_900)
        candidates = []
        for path in products.glob("*.xctestrun"):
            value = plistlib.loads(path.read_bytes())
            targets = [t for config in value.get("TestConfigurations", []) for t in config.get("TestTargets", [])]
            if ui["target"] in value or any(t.get("BlueprintName") == ui["target"] for t in targets):
                candidates.append(path)
        require(len(candidates) == 1, "one_current_original_ui_descriptor")
        descriptor = candidates[0]
        shutil.copy2(descriptor, evidence / "original.xctestrun")
        ui_products = base.inventory(products)
        write(evidence / "original-products.json", ui_products)
        result = evidence / "original.xcresult"
        require(shutil.disk_usage(root).free >= 2 * 1024**3, "ui_test_capacity")
        commands.run(["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
            "-destination", destination, "-parallel-testing-enabled", "NO",
            "-maximum-concurrent-test-simulator-destinations", "1",
            "-resultBundlePath", str(result), *selectors], "original-ui-test", 2_400, check=False)
        test_exit = commands.last_record["exitCode"]
        qualified = base.qualify_test(commands, result, evidence, ui)
        require(test_exit == 0, "original_ui_process_failed")
        require(base.inventory(products) == ui_products, "current_ui_products_changed")
        after = base.source_state(source, SOURCE)
        write(evidence / "source-after.json", after)
        require(before == after and native_files == base.inventory(vendor), "current_source_or_native_changed")
        packages_after = base.dependency_state(derived / "SourcePackages")
        write(evidence / "dependencies-after.json", packages_after)
        require(packages == packages_after and base.inventory(saved) == native_products,
                "original_native_or_dependencies_changed")
        outcome["ui"] = qualified
        outcome["originalNative"] = prior["stages"]["native"]
        outcome["status"] = "PASS"
    except BaseException as error:
        outcome["status"] = "FAIL"
        outcome["failure"] = {"type": type(error).__name__, "reason": str(error)[:1_024]}
    finally:
        cleanup = {"ownedUDID": device, "status": "NO_DEVICE_CREATED"}
        if commands.active is not None:
            commands.stop(commands.active)
        if device is not None:
            try:
                commands.run(["xcrun", "simctl", "shutdown", device], "shutdown-owned-ui-simulator", 90, check=False)
                commands.run(["xcrun", "simctl", "delete", device], "delete-owned-ui-simulator", 90)
                cleanup["status"] = "PASS"
            except BaseException as error:
                cleanup["status"] = "FAIL"; cleanup["error"] = str(error)[:1_024]
                outcome["status"] = "FAIL"
        remaining = []
        for group in commands.groups:
            try:
                os.killpg(group, 0); remaining.append(group)
            except ProcessLookupError:
                pass
        cleanup["remainingOwnedGroups"] = remaining
        if remaining:
            cleanup["status"] = "FAIL"; outcome["status"] = "FAIL"
        write(evidence / "cleanup.json", cleanup)
        write(evidence / "execution.json", outcome)
    print(json.dumps({"status": outcome["status"], "failure": outcome.get("failure"),
                      "evidence": str(evidence)}, sort_keys=True))
    return 0 if outcome["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
