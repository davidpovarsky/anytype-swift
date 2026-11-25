#!/usr/bin/env python3
"""Continue the affected source UI after fixing the observed zero-frame Unlink button.
Old accepted products and results stay immutable; compiled modules are caches.
The original single-Any artifact and SDK6bd scope is explicit, not dual-runtime acceptance.
"""
import argparse
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

SOURCE = "4b9b381d3f9b8d5a9a358d626a69333c145e3282"
PRIOR = "40655e020f036d35df8b9292f3762251ec227458"
BASE_SHA = "341f28c617c1ada9d30b77cc682f652fe2207fff630e6f0ad1ec95685594e59d"
SHARED_RECEIPT_SHA = "0adcbb3387cd0ebaf4444909eac9c4ac10f6b58118c227044422a78de1c5f2a1"
STAGES = {
    "ui": {"scheme": "PinkhaAnyNativeApp", "target": "PinkhaAnyNativeUITests",
           "methods": ["NativeLaunchTests/testSemanticSourceLinkSurvivesEditAndColdReopen"]},
}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--base-controller", type=Path, required=True)
    parser.add_argument("--controller-commit", required=True)
    args = parser.parse_args()
    source, root = args.source.resolve(), args.run_root.resolve()
    import hashlib
    assert hashlib.sha256(args.base_controller.read_bytes()).hexdigest() == BASE_SHA
    module = importlib.util.spec_from_file_location("original_any_anchor_driver", args.base_controller)
    base = importlib.util.module_from_spec(module)
    module.loader.exec_module(base)
    require, write = base.require, base.write
    require(str(source) == "/Users/m1/builds/any-semantic-20261125/source-fbb7b19" and
            str(root).startswith("/Users/m1/builds/any-semantic-20261125/source-links") and
            not root.exists() and re.fullmatch("[0-9a-f]{40}", args.controller_commit),
            "fresh_exact_owned_source_and_root_required")
    require(shutil.disk_usage(root.parent).free >= 4 * 1024**3, "incremental_capacity")
    root.mkdir(mode=0o700); evidence = root / "evidence"; evidence.mkdir()
    commands = base.Commands(source, evidence)
    prior = Path("/Users/m1/builds/any-semantic-20261125/source-links-ui2")
    cache = Path("/Users/m1/builds/any-semantic-20261125/attempt3/derived")
    vendor = source / "Modules/PinkhaAnyRuntime/Vendor"
    original = Path("/Users/m1/builds/_retained-anytype/45539471031-1/build/"
                    "current-apple-native-ui-failed-45539471031-1/work/native-originals")
    shared = Path("/Users/m1/builds/semantic-sources-20261125/shared-components-2b2a-attempt1/"
                  "evidence/original-xctest-qualified.json")
    outcome = {"schema": "any-semantic-source-links-ui-continuation/v1", "sourceCommit": SOURCE,
               "controllerCommit": args.controller_commit, "controllerSHA256": base.sha(Path(__file__)),
               "nativeProducer": base.NATIVE_PRODUCER, "hanlinCommit": base.HANLIN_COMMIT,
               "scope": "single Any native artifact; SDK6bd; not final combined runtime or SDK97 acceptance",
               "status": "RUNNING", "stages": {}, "acceptedOldTestsRerun": 0,
               "nativeLibraryBuilds": 0, "acceptedNewNativeTestsRerun": 0, "physicalDevice": "NOT_RUN"}
    write(evidence / "execution.json", outcome)
    device = None; before = None; native_files = None; dependencies = None

    def interrupted(signum, frame):
        if commands.active is not None: commands.stop(commands.active)
        raise RuntimeError("owned_source_link_interrupted:" + str(signum))
    for sig in (signal.SIGTERM, signal.SIGINT): signal.signal(sig, interrupted)
    try:
        require(base.sha(shared) == SHARED_RECEIPT_SHA, "original_shared_receipt_changed")
        receipt = json.loads(shared.read_text())
        require(receipt["source_commit"] == "2b2a5611cee18ce7fcb76e7e91d455ca21e1bd3c" and receipt["status"] == "PASS_COMPONENTS_ONLY"
                and receipt["test_count"] == 5 and receipt["failure_count"] == receipt["skip_count"] == 0,
                "shared_component_scope_differs")
        shutil.copy2(shared, evidence / "qualified-shared-components.json")
        require(base.git(source, "hash-object", str(Path(__file__).resolve())) ==
                base.git(source, "rev-parse", args.controller_commit + ":Tools/AnySemanticAnchorValidation/source_links_unlink.py"),
                "controller_not_exact_frozen_git_blob")
        prior_source = base.source_state(source, PRIOR)
        require(prior_source == json.loads((prior / "evidence/source-after.json").read_text()),
                "accepted_prior_source_changed")
        prior_execution = json.loads((prior / "evidence/execution.json").read_text())
        require(prior_execution["status"] == "FAIL" and prior_execution["sourceCommit"] == PRIOR
                and prior_execution["acceptedNewNativeEvidenceSHA256"] ==
                    "a1558d0b732f905f6ad3d21723c84deebfca62fb5d7993c9133a2bf215188bbf"
                and prior_execution["acceptedNewNativeTestsRerun"] == 0
                and prior_execution["stages"]["ui"]["status"] == "FAIL",
                "original_native_pass_and_ui_failure_required")
        native_receipt = prior / "evidence/original-native-pass-ui-lookup-fail.json"
        require(base.sha(native_receipt) == "a1558d0b732f905f6ad3d21723c84deebfca62fb5d7993c9133a2bf215188bbf",
                "original_native_qualification_changed")
        shutil.copy2(native_receipt, evidence / "original-native-pass-ui-lookup-fail.json")
        failure_receipt = prior / "evidence/original-unlink-reachability-failure.json"
        require(base.sha(failure_receipt) == "01d8f5a1c7100da5fe231bbe85b58da04adec7415cf701e6a85fd895d02531e0",
                "original_unlink_reachability_failure_changed")
        shutil.copy2(failure_receipt, evidence / "original-unlink-reachability-failure.json")
        outcome["acceptedNewNativeEvidenceSHA256"] = base.sha(native_receipt)
        protected_products = {}
        for label, folder in {
            "accepted-initial-ui": Path("/Users/m1/builds/any-semantic-20261125/ui-typing2/evidence"),
            "accepted-source-link-native": Path("/Users/m1/builds/any-semantic-20261125/source-links1/evidence/native"),
        }.items():
            inventory = json.loads((folder / "original-products.json").read_text())
            saved = folder / "retained-original/Build/Products"
            require(base.inventory(saved) == inventory, "protected_original_products_changed:" + label)
            protected_products[label] = (saved, inventory)
        prior_cleanup = json.loads((prior / "evidence/cleanup.json").read_text())
        require(prior_cleanup["status"] == "PASS" and not prior_cleanup["remainingOwnedGroups"],
                "prior_ui_not_terminal")
        old_products = json.loads((prior / "evidence/ui/original-products.json").read_text())
        old_saved = prior / "evidence/ui/retained-original/Build/Products"
        require(base.inventory(old_saved) == old_products and
                base.inventory(cache / "Build/Products") == old_products,
                "accepted_original_products_changed")
        old_native = json.loads((prior / "evidence/native-binding.json").read_text())["files"]
        require(base.inventory(vendor) == old_native, "original_native_binding_changed")
        dependencies = base.dependency_state(cache / "SourcePackages")
        require(dependencies == json.loads((prior / "evidence/dependencies-after.json").read_text()),
                "original_package_dependencies_changed")
        write(evidence / "dependencies-before.json", dependencies)
        write(evidence / "prior-source.json", prior_source)
        write(evidence / "original-accepted-ui.json", prior_execution)
        commands.run(["git", "checkout", "--detach", SOURCE], "checkout-frozen-semantic-source")
        before = base.source_state(source, SOURCE)
        write(evidence / "source-before.json", before)
        review = json.loads((source / "docs/validation/20261125-semantic-source-link-candidate/source-review.json").read_text())
        require(review["base_commit"] == "68c3c94f6f4bb2299886799589b23753efe1c41b"
                and len(review["source_files"]) == 30
                and all(x["unchanged"] for x in review["original_controls"]),
                "phase2_review_scope_changed")
        for item in review["source_files"]:
            if item["path"] == "NativeApp/UITests/NativeLaunchTests.swift":
                require(base.sha(source / item["path"]) ==
                        "d3c5ff8190d97f51857da92e95307a5ce08732d3bb31c26904e19778d8dbaa9a",
                        "reviewed_menu_lookup_correction_changed")
            elif item["path"] == "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift":
                require(base.sha(source / item["path"]) ==
                        "14bd6d6183c9cd03b849403c9e3ab7b565b0a4abc8a0084f4b76b1ea060eea63",
                        "reviewed_unlink_label_and_hit_area_changed")
            else:
                require(base.sha(source / item["path"]) == item["sha256"],
                        "reviewed_source_changed:" + item["path"])
        product_changes = base.git(source, "diff", "--name-only", PRIOR, SOURCE,
                                   "--", "Modules", "NativeApp", "Anytype").splitlines()
        require(product_changes == ["Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift",
                                    "NativeApp/UITests/NativeLaunchTests.swift"],
                "ui_continuation_contains_unqualified_product_change")
        require(before["hanlinSourceFiles"] == prior_source["hanlinSourceFiles"],
                "unreviewed_hanlin_change")
        write(evidence / "phase2-source-review.json", review)
        changes = {name: {"before": prior_source["files"].get(name), "after": before["files"].get(name)}
                   for name in set(prior_source["files"]) | set(before["files"])
                   if prior_source["files"].get(name) != before["files"].get(name)}
        write(evidence / "affected-source.json", {"base": PRIOR, "current": SOURCE, "files": changes,
              "old_control_bodies_unchanged": review["original_controls"]})
        require(base.sha(original / "any.xcframework.zip") == base.NATIVE_ARCHIVE and
                base.sha(original / "native-artifact.json") == base.NATIVE_RECEIPT,
                "original_native_archive_changed")
        saved_vendor = evidence / "prior-native-original/Vendor"
        saved_vendor.parent.mkdir()
        vendor.rename(saved_vendor)
        require(base.inventory(saved_vendor) == old_native, "retired_original_native_changed")
        commands.run([sys.executable, "-B", str(source / "Tools/AnyEnginePort/prepare_native_runtime.py"),
                      "install", "--artifact", str(original), "--producer-commit", base.NATIVE_PRODUCER],
                     "bind-source-identical-any", 300)
        binding = json.loads((vendor / "consumer-binding.json").read_text())
        require(binding["consumerCommit"] == SOURCE and binding["archiveSHA256"] == base.NATIVE_ARCHIVE
                and binding["status"] == "SOURCE_IDENTICAL_NATIVE_ARTIFACT", "new_native_binding_differs")
        native_files = base.inventory(vendor)
        require({k: v for k, v in old_native.items() if k != "consumer-binding.json"} ==
                {k: v for k, v in native_files.items() if k != "consumer-binding.json"},
                "native_library_bytes_changed")
        write(evidence / "native-binding.json", {"binding": binding, "files": native_files})
        os.environ["PINKHA_ANY_NATIVE_ARTIFACT"] = "verified-v1"
        os.environ["ANY_BUILD_VERSION"] = "v0.5.0-pinkha.1"
        os.environ["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"
        runtime = json.loads((prior / "evidence/simulator.json").read_text())
        name = "EAnchorSources-" + SOURCE[:8] + "-" + uuid.uuid4().hex[:8]
        device = commands.run(["xcrun", "simctl", "create", name, runtime["deviceType"]["identifier"],
                               runtime["runtime"]["identifier"]], "create-owned-simulator").read_text().strip()
        require(re.fullmatch("[A-Fa-f0-9-]{36}", device), "owned_simulator_identity_invalid")
        write(evidence / "simulator.json", {"ownedUDID": device, "name": name,
              "runtime": runtime["runtime"], "deviceType": runtime["deviceType"]})
        commands.run(["xcrun", "simctl", "boot", device], "boot-owned-simulator")
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "wait-owned-boot", 240)
        destination = "platform=iOS Simulator,id=" + device
        products = cache / "Build/Products"
        for old_descriptor in products.glob("*.xctestrun"):
            require(base.inventory(old_saved) == old_products, "old_descriptors_not_preserved")
            old_descriptor.unlink()
        for stage, spec in STAGES.items():
            require(shutil.disk_usage(root).free >= 3 * 1024**3, "stage_build_capacity")
            output = evidence / stage; output.mkdir()
            selectors = ["-only-testing:" + spec["target"] + "/" + x for x in spec["methods"]]
            commands.run(["xcodebuild", "build-for-testing", "-jobs", "2",
                "-project", str(source / "NativeApp/AnyNative.xcodeproj"), "-scheme", spec["scheme"],
                "-configuration", "Debug", "-destination", destination, "-derivedDataPath", str(cache),
                "-parallel-testing-enabled", "NO", "-disableAutomaticPackageResolution",
                "-onlyUsePackageVersionsFromResolvedFile", "-resultBundlePath", str(output / "build.xcresult"),
                *selectors, "ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=YES",
                "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-", "PROVISIONING_PROFILE_SPECIFIER="],
                stage + "-build", 3900)
            descriptors = []
            for path in products.glob("*.xctestrun"):
                v = plistlib.loads(path.read_bytes())
                targets = [t for c in v.get("TestConfigurations", []) for t in c.get("TestTargets", [])]
                if spec["target"] in v or any(t.get("BlueprintName") == spec["target"] for t in targets):
                    descriptors.append(path)
            require(len(descriptors) == 1, "one_current_descriptor:" + stage)
            descriptor = descriptors[0]; shutil.copy2(descriptor, output / "original.xctestrun")
            compiled = base.inventory(products); write(output / "original-products.json", compiled)
            require(shutil.disk_usage(root).free >= 2 * 1024**3, "stage_test_capacity")
            result = output / "original.xcresult"
            commands.run(["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
                "-destination", destination, "-parallel-testing-enabled", "NO",
                "-maximum-concurrent-test-simulator-destinations", "1",
                "-collect-test-diagnostics", "never", "-resultBundlePath", str(result), *selectors],
                stage + "-test", 2400, check=False)
            exit_code = commands.last_record["exitCode"]
            try:
                qualified = base.qualify_test(commands, result, output, spec)
                require(exit_code == 0, "original_test_process_failed")
                outcome["stages"][stage] = qualified
            except BaseException as error:
                outcome["stages"][stage] = {"status": "FAIL", "testExitCode": exit_code,
                    "xcresult": str(result), "reason": str(error)[:1024]}
            require(base.inventory(products) == compiled, "test_modified_compiled_products")
            saved_products = output / "retained-original/Build/Products"
            saved_products.parent.mkdir(parents=True)
            commands.run(["/bin/cp", "-cR", str(products), str(saved_products)],
                         "retain-" + stage + "-original-products", 300)
            require(base.inventory(saved_products) == compiled, "original_products_retention_differs")
            write(output / "product-retention.json", {"sourceCommit": SOURCE,
                "selectedMethods": spec["methods"], "products": str(saved_products),
                "originalInventorySHA256": base.sha(output / "original-products.json"),
                "entries": len(compiled), "status": "PASS"})
            write(evidence / "execution.json", outcome)
        after = base.source_state(source, SOURCE)
        write(evidence / "source-after.json", after)
        require(before == after, "source_changed_during_acceptance")
        require(base.inventory(vendor) == native_files, "native_changed_during_acceptance")
        packages_after = base.dependency_state(cache / "SourcePackages")
        write(evidence / "dependencies-after.json", packages_after)
        require(dependencies == packages_after, "dependencies_changed_during_acceptance")
        require(base.inventory(old_saved) == old_products, "prior_original_products_modified")
        for label, (saved, inventory) in protected_products.items():
            require(base.inventory(saved) == inventory, "protected_original_products_modified:" + label)
        outcome["status"] = "PASS" if set(outcome["stages"]) == set(STAGES) and all(
            x["status"] == "PASS" for x in outcome["stages"].values()) else "FAIL"
    except BaseException as error:
        outcome["status"] = "FAIL"
        outcome["failure"] = {"type": type(error).__name__, "reason": str(error)[:1024]}
    finally:
        cleanup = {"ownedUDID": device, "status": "NO_DEVICE_CREATED"}
        if commands.active is not None: commands.stop(commands.active)
        if device:
            try:
                commands.run(["xcrun", "simctl", "shutdown", device], "shutdown-owned-simulator", 90, check=False)
                commands.run(["xcrun", "simctl", "delete", device], "delete-owned-simulator", 90)
                cleanup["status"] = "PASS"
            except BaseException as error:
                cleanup["status"] = "FAIL"; cleanup["error"] = str(error)[:1024]
                outcome["status"] = "FAIL"
        remaining = []
        for group in commands.groups:
            try: os.killpg(group, 0); remaining.append(group)
            except ProcessLookupError: pass
        cleanup["remainingOwnedGroups"] = remaining
        if remaining: cleanup["status"] = "FAIL"; outcome["status"] = "FAIL"
        write(evidence / "cleanup.json", cleanup)
        if before is not None:
            try:
                final = base.source_state(source, SOURCE)
                write(evidence / "source-after.json", final)
                require(final == before, "source_finalization_changed")
            except BaseException as error:
                outcome["sourceFinalizationError"] = str(error)[:1024]; outcome["status"] = "FAIL"
        write(evidence / "execution.json", outcome)
    print(json.dumps({"status": outcome["status"], "evidence": str(evidence),
                      "failure": outcome.get("failure"), "stages": outcome["stages"]}, sort_keys=True))
    return 0 if outcome["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
