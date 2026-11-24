"""Execute only newly registered SDK06 components against an immutable App.

This is a new test-bundle build. It never labels that bundle as the retained
native bundle, and never relaxes the old selector or the23/32 result validator.
"""
from __future__ import annotations
import base64
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import stat
import tarfile

import sdk06_component_projection as projection

PROTOCOL = "sdk06-projected-components-v1"
_SEAL = object()


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def save(path, value, *, fresh=False):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    with Path(path).open("xb" if fresh else "wb") as output:
        output.write(raw)


def inventory(root):
    require(root.is_dir() and not root.is_symlink(), "A regular owned product root is required")
    result = {}
    for path in sorted(root.rglob("*")):
        observed = path.lstat()
        name = path.relative_to(root).as_posix()
        require(stat.S_ISDIR(observed.st_mode) or stat.S_ISREG(observed.st_mode),
                "Links or special files are not admitted in projected products")
        row = {"kind": "directory" if path.is_dir() else "file",
               "mode": stat.S_IMODE(observed.st_mode)}
        if path.is_file():
            row.update(bytes=observed.st_size, sha256=sha(path))
        result[name] = row
    return result


def archive_product(root, evidence, inputs, generated, *, build_return_code=None,
                    bundle_identity_validated=False):
    roots = {"Source": generated}
    if root.is_dir():
        roots["Build/Products"] = root
    maps = {name: inventory(path) for name, path in roots.items()}
    target = evidence / "SDK06PendingProducts.tar.gz"
    require(not target.exists(), "Current component products may be archived only once")
    with tarfile.open(target, "w:gz", compresslevel=1) as archive:
        for prefix, path in roots.items():
            archive.add(path, arcname=prefix, recursive=False)
            for name in sorted(maps[prefix]):
                archive.add(path / name, arcname=prefix + "/" + name, recursive=False)
    require(all(inventory(path) == maps[name] for name, path in roots.items()),
            "Generated inputs or current products changed while archiving")
    receipt = {"protocol": PROTOCOL, "source_binding": inputs, "trees": maps,
               "archive_bytes": target.stat().st_size, "archive_sha256": sha(target),
               "archive_path": str(target), "build_return_code": build_return_code,
               "bundle_identity_validated": bundle_identity_validated,
               "native_app_builds": 0, "native_library_builds": 0, "component_bundle_builds": 1,
               "test_execution_claimed": False}
    save(evidence / "current-component-products.json", receipt, fresh=True)
    return receipt


def verify_staged_originals(original_entries, observed):
    changes = [name for name, row in original_entries.items() if observed.get(name) != row]
    additions = set(observed) - set(original_entries)
    require(not changes and all(name == "PlugIns/SDK06PendingTests.xctest"
            or name.startswith("PlugIns/SDK06PendingTests.xctest/") for name in additions),
            "The unit-test build changed an original staged App entry")


@dataclass(frozen=True)
class ProjectedComponentPlan:
    origin: object
    _seal: object = field(repr=False)
    _state: dict = field(default_factory=dict, repr=False, compare=False)

    def verify(self, *, full=False):
        from sdk06_original_native import SDK06OriginalNativeContext
        require(self._seal is _SEAL and type(self.origin) is SDK06OriginalNativeContext,
                "A sealed original App origin is required for the new component bundle")
        self.origin.verify_current(full=full)
        fixed = projection.contract(self.origin.control)
        require(fixed["selection"] == self.origin.tag_contract["selection"],
                "New registration scope differs from the original pending component contract")
        if "generated_root" in self._state:
            root = Path(self._state["generated_root"])
            actual = {p.relative_to(root).as_posix(): sha(p)
                      for p in sorted(root.rglob("*")) if p.is_file()}
            require(actual == self._state["generated_files"]
                    and inventory(root) == self._state["generated_inventory"],
                    "Projected source/project input changed")
        if "current_products" in self._state:
            require(inventory(Path(self._state["current_products_root"])) == self._state["current_products"],
                    "The current component test bundle changed")
        if "staged_app" in self._state:
            observed = inventory(Path(self._state["staged_app"]))
            verify_staged_originals(self._state["stage_before_build"], observed)
            if "stage_inventory" in self._state:
                require(observed == self._state["stage_inventory"],
                        "The staged App changed after the new test-bundle build")
        if "descriptor" in self._state:
            row = self._state["descriptor"]
            for path_key, hash_key in (("path", "sha256"), ("original_path", "original_sha256")):
                path = Path(row[path_key])
                require(path.is_file() and not path.is_symlink() and sha(path) == row[hash_key],
                        "A bound original or projected descriptor changed")
        if "enumeration" in self._state:
            row = self._state["enumeration"]
            require(sha(Path(row["path"])) == row["sha256"], "Bound projected enumeration changed")
        if "archive" in self._state:
            row = self._state["archive"]
            require(sha(Path(row["archive_path"])) == row["archive_sha256"],
                    "The retained generated source/product archive changed")
        return fixed

    def verify_component_receipt(self, receipt):
        self.verify()
        from shared_editor_existing_build import PASS_STATUS
        require(self._state.get("passed") is True
                and receipt.get("status") == PASS_STATUS
                and receipt.get("build_mode") == projection.MODE
                and receipt.get("original_native_origin") == self.origin.origin_reference()
                and receipt.get("controller_binding") == self.origin.execution_binding
                and receipt.get("actual", {}).get("actual_method_count") == 23
                and receipt.get("actual", {}).get("declared_case_count") == 32
                and receipt.get("component_bundle_builds") == 1
                and projection.digest(json.dumps(receipt, sort_keys=True).encode()) ==
                    self._state.get("component_receipt_sha256"),
                "The exact current projected component execution has not passed")
        return receipt

    def execute(self, app, original_configuration, udid, original_app, evidence, shared):
        import shared_editor_existing_build as component
        import sdk06_enumeration_probe as probe
        fixed = self.verify()
        require(not self._state and Path(app).resolve() == self.origin.app
                and original_configuration == self.origin.native_configuration
                and udid == self.origin.device["udid"]
                and original_app == self.origin.derived / "Build/Products/Debug-Anytype-iphonesimulator/Anytype.app"
                and evidence == self.origin.evidence / "shared-editor-components",
                "Only one exact current component projection is permitted")
        require(not evidence.exists(), "Refuse stale projected component evidence")
        evidence.mkdir()
        self._state["attempted"] = True
        source = component.source_contract(app)
        require(set(fixed["selection"]["selected"]) ==
                {source["compiled_declarations"][name] for name in source["methods"]},
                "Existing source/result validator and projection methods differ")
        receipt = {"protocol": PROTOCOL, "status": "FAIL", "phase": "TEST_BUNDLE_BUILD",
                   "profile": component.PROFILE, "build_mode": projection.MODE,
                   "controller_binding": self.origin.execution_binding,
                   "original_native_origin": self.origin.origin_reference(),
                   "additional_app_builds": 0, "native_library_builds": 0,
                   "component_bundle_builds": 0, "product_tests_executed": 0,
                   "source": source, "old_passed_methods_replayed": 0,
                   "real_native_persistence_accepted": False}
        save(evidence / "execution.json", receipt, fresh=True)
        primary_error = None
        primary_traceback = None
        pending_component_receipts = {}
        generated = current_root = None
        projected = build_binding = None
        build_return_code = None
        try:
            work = self.origin.work / "current-component-projection"
            require(not work.exists() and not work.is_symlink(), "Fresh projected component work root required")
            original_entries = inventory(original_app)
            app_bytes = sum(row.get("bytes", 0) for row in original_entries.values())
            require(shutil.disk_usage(self.origin.work).free >= app_bytes + 4_000_000_000,
                    "Insufficient room for the isolated App copy, test bundle and reserve")
            work.mkdir()
            staged = work / "host/Anytype.app"
            staged.parent.mkdir()
            shutil.copytree(original_app, staged, symlinks=False, copy_function=shutil.copy2)
            require(inventory(staged) == original_entries,
                    "The test-host copy must initially equal every original App entry")
            save(evidence / "staged-app-before-build.json", original_entries, fresh=True)
            self._state.update(staged_app=str(staged), stage_before_build=original_entries)
            generated = work / "project"
            products = self.origin.derived / "Build/Products/Debug-Anytype-iphonesimulator"
            project, projected = projection.write_project(self.origin.control, app, generated, staged, products,
                                                          with_compile_support=True, with_retained_frameworks=True)
            self._state.update(generated_root=str(generated), generated_files=projected["generated_files"],
                               generated_inventory=inventory(generated))
            save(evidence / "source-projection.json", projected, fresh=True)
            # Original precompiled modules are consumed by a single unit-test
            # target. There is no App, native or package target in its graph.
            derived = work / "derived"
            current_root = derived / "Build/Products"
            command = ["xcodebuild", "build-for-testing", "-project", str(project),
                       "-scheme", projection.SCHEME, "-configuration", "Debug-Anytype",
                       "-destination", "platform=iOS Simulator,id=" + udid,
                       "-parallel-testing-enabled", "NO", "-derivedDataPath", str(derived),
                       "-disableAutomaticPackageResolution"]
            receipt.update(component_bundle_builds=1, build_command=command)
            save(evidence / "execution.json", receipt)
            runner = probe.Commands(app, evidence, receipt)
            _, outcome = runner.run(command, "projected-component-build", timeout=900)
            build_return_code = outcome["return_code"]
            require(outcome["return_code"] == 0, "The isolated component test-bundle build failed")
            self.origin.verify_current(full=True)
            # No signature rewrite of the original App executable is allowed.
            after = inventory(staged)
            verify_staged_originals(original_entries, after)
            save(evidence / "staged-app-after-build.json", after, fresh=True)
            self._state.update(staged_app=str(staged), stage_inventory=after)
            current_root = derived / "Build/Products"
            candidates = list(current_root.rglob(projection.PRODUCT))
            require(len(candidates) == 1 and candidates[0].is_dir(),
                    "Exactly one newly built pending component bundle is required")
            test_bundle = candidates[0]
            info = plistlib.loads((test_bundle / "Info.plist").read_bytes())
            require(info.get("CFBundleIdentifier") == "com.AnytypeTests"
                    and info.get("CFBundleExecutable") == "SDK06PendingTests",
                    "Unexpected newly compiled component bundle identity")
            actual_products = inventory(current_root)
            self._state.update(current_products_root=str(current_root), current_products=actual_products)
            build_binding = {"controller": self.origin.execution_binding,
                             "original_native_origin": self.origin.origin_reference(),
                             "generated_source": projected,
                             "app_executable_sha256": sha(staged / "Anytype"),
                             "test_executable_sha256": sha(test_bundle / "SDK06PendingTests")}
            receipt["current_component_products"] = archive_product(
                current_root, evidence, build_binding, generated,
                build_return_code=build_return_code, bundle_identity_validated=True)
            self._state["archive"] = receipt["current_component_products"]
            self.verify()
            original_raw = original_configuration.read_bytes()
            configuration = work / "SDK06Pending.xctestrun"
            value = projection.descriptor_value(plistlib.loads(original_raw),
                self.origin.derived / "Build/Products", staged, test_bundle)
            configuration.write_bytes(plistlib.dumps(value, sort_keys=False))
            descriptor = {"path": str(configuration), "sha256": sha(configuration),
                          "original_path": str(original_configuration),
                          "original_sha256": projection.digest(original_raw),
                          "bytes_base64": base64.b64encode(configuration.read_bytes()).decode(),
                          "original_bytes_base64": base64.b64encode(original_raw).decode()}
            save(evidence / "projected-descriptor-chain.json", descriptor, fresh=True)
            self._state["descriptor"] = descriptor
            base = ["xcodebuild", "test-without-building", "-xctestrun", str(configuration),
                    "-destination", "platform=iOS Simulator,id=" + udid,
                    "-parallel-testing-enabled", "NO"]
            # All compiled registrations in this new bundle must be precisely
            # the23 pending identities. No per-method or tag filter is trusted.
            enumeration_path = evidence / "projected.enumeration.json"
            enum_command = [*base, "-enumerate-tests", "-test-enumeration-style", "flat",
                            "-test-enumeration-format", "json", "-test-enumeration-output-path",
                            str(enumeration_path), "-resultBundlePath", str(evidence / "Enumeration.xcresult")]
            receipt.update(phase="ENUMERATION_PRECHECK", enumeration_command=enum_command)
            save(evidence / "execution.json", receipt)
            _, outcome = runner.run(enum_command, "projected-component-enumeration", timeout=600)
            require(outcome["return_code"] == 0, "Current projected enumeration failed")
            self._state["enumeration"] = {"path": str(enumeration_path), "sha256": sha(enumeration_path)}
            test_plan, enabled, disabled = component.enumerated_identifiers(
                json.loads(enumeration_path.read_bytes()))
            observation = {"test_plan": test_plan, "enabled": sorted(enabled), "disabled": sorted(disabled),
                           "enumeration_sha256": sha(enumeration_path), "descriptor": descriptor,
                           "registered_original_passed_methods": sorted(enabled.intersection(fixed["selection"]["excluded"])),
                           "product_tests_executed": 0}
            save(evidence / "projected-enumeration-observation.json", observation, fresh=True)
            projection.require_pending_registration(test_plan, enabled, disabled, fixed)
            require(original_configuration.read_bytes() == original_raw
                    and sha(configuration) == descriptor["sha256"], "A bound descriptor changed")
            self.verify()
            result_bundle = evidence / "SharedEditorTableAuthority.xcresult"
            command = [*base, "-resultBundlePath", str(result_bundle)]
            receipt.update(phase="EXECUTION", command=command,
                           enumeration=observation, product_tests_may_have_started=True)
            save(evidence / "execution.json", receipt)
            shared.run_xctest(command, app, evidence, result_bundle, component.RESULT_PREFIX,
                              command_runner=component.host.command)
            summary_path = evidence / (component.RESULT_PREFIX + "-summary.json")
            tests_path = evidence / (component.RESULT_PREFIX + "-tests.json")
            actual = component.validate_results(json.loads(summary_path.read_bytes()),
                json.loads(tests_path.read_bytes()), set(source["methods"]), udid)
            self.verify()
            require(component.source_contract(app) == source
                    and original_configuration.read_bytes() == original_raw
                    and sha(configuration) == descriptor["sha256"]
                    and sha(enumeration_path) == observation["enumeration_sha256"],
                    "Bound source, descriptor or enumeration changed during current tests")
            hashes = {"app_executable": sha(staged / "Anytype"),
                      "test_executable": sha(test_bundle / "SDK06PendingTests"),
                      "xctestrun": sha(configuration)}
            for label, actual_component in actual["components"].items():
                pending_component_receipts[label] = {
                            "status": "SOURCE_BOUND_COMPONENT_PASS", "component": label,
                            "build_mode": projection.MODE, "additional_app_builds": 0,
                            "component_bundle_builds": 1, "actual": actual_component,
                            "methods": sorted(actual_component["core_cases"]),
                            "source_hashes": source["source_hashes"], "built_products": hashes,
                            "original_native_origin": self.origin.origin_reference(),
                            "raw_summary_sha256": sha(summary_path), "raw_tests_sha256": sha(tests_path),
                            "real_native_persistence_accepted": False}
            receipt.update(status="RESULTS_VALIDATED_PENDING_FINAL_INTEGRITY",
                           phase="FINAL_INTEGRITY", actual=actual, product_tests_executed=23,
                           declared_argument_cases_executed=32, built_products=hashes,
                           raw_summary_sha256=sha(summary_path), raw_tests_sha256=sha(tests_path))
        except BaseException as error:
            primary_error, primary_traceback = error, error.__traceback__
            receipt.update(status="FAIL", error_type=type(error).__name__, error=str(error))
        finally:
            integrity_errors = []
            # Even a failed build preserves its exact generated inputs and any
            # partial Products. Its return code and unvalidated identity stay explicit.
            if receipt["component_bundle_builds"] == 1 and "current_component_products" not in receipt:
                try:
                    require(generated is not None and generated.is_dir() and current_root is not None,
                            "Attempted build lacks its bound generated source/root")
                    partial_binding = build_binding or {
                        "controller": self.origin.execution_binding,
                        "original_native_origin": self.origin.origin_reference(),
                        "generated_source": projected,
                        "partial_build_outputs": True}
                    receipt["current_component_products"] = archive_product(
                        current_root, evidence, partial_binding, generated,
                        build_return_code=build_return_code, bundle_identity_validated=False)
                    self._state["archive"] = receipt["current_component_products"]
                except BaseException as audit_error:
                    integrity_errors.append({"scope": "retain_build_outputs",
                                             "error_type": type(audit_error).__name__,
                                             "error": str(audit_error)})
            try:
                self.verify(full=True)
                require(component.source_contract(app) == source,
                        "Bound component source changed before final qualification")
            except BaseException as audit_error:
                integrity_errors.append({"scope": "final_source_products_descriptors",
                                         "error_type": type(audit_error).__name__,
                                         "error": str(audit_error)})
            receipt["final_integrity"] = {
                "status": "PASS" if not integrity_errors else "FAIL",
                "errors": integrity_errors,
                "original_failure_preserved": primary_error is not None,
                "generated_source_bound": "generated_root" in self._state,
                "staged_original_app_bound": "staged_app" in self._state,
                "completed_new_products_bound": "current_products" in self._state,
                "descriptor_bound": "descriptor" in self._state,
                "enumeration_bound": "enumeration" in self._state,
                "source_products_archive_bound": "archive" in self._state}
            if integrity_errors:
                receipt["status"] = "FAIL"
                if primary_error is None:
                    primary_error = ValueError("Final projected component integrity failed")
                    receipt.update(error_type=type(primary_error).__name__, error=str(primary_error))
            if primary_error is None:
                try:
                    component_receipts = {}
                    for label, payload in pending_component_receipts.items():
                        path = evidence / ("component-" + label + ".json")
                        payload["final_integrity"] = "PASS"
                        save(path, payload, fresh=True)
                        component_receipts[label] = {"path": str(path), "sha256": sha(path)}
                    receipt.update(status=component.PASS_STATUS, phase="COMPLETE",
                                   component_receipts=component_receipts)
                    self._state["passed"] = True
                    self._state["component_receipt_sha256"] = projection.digest(
                        json.dumps(receipt, sort_keys=True).encode())
                except BaseException as sealing_error:
                    primary_error, primary_traceback = sealing_error, sealing_error.__traceback__
                    self._state["passed"] = False
                    receipt.update(status="FAIL", error_type=type(sealing_error).__name__,
                                   error=str(sealing_error))
            else:
                self._state["passed"] = False
            try:
                save(evidence / "execution.json", receipt)
            except BaseException as receipt_error:
                self._state["passed"] = False
                if primary_error is None:
                    primary_error, primary_traceback = receipt_error, receipt_error.__traceback__
        if primary_error is not None:
            raise primary_error.with_traceback(primary_traceback)
        return receipt


def load_plan(origin):
    from sdk06_original_native import SDK06OriginalNativeContext
    require(type(origin) is SDK06OriginalNativeContext, "Exact original-native origin required")
    origin.verify_current()
    return ProjectedComponentPlan(origin, _SEAL)
