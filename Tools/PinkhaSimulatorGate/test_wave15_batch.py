"""Controller controls only. Synthetic XCTest data never constitutes Apple evidence."""
import argparse
import copy
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

import wave15_batch as batch
import test_type_preservation as preservation_controls


SPECS = [
    ("AnytypeComprehensiveAcceptanceUITests", ["testObjectAddPropertyButtonAndPickerSearch",
        "testDocumentSourceSearchPresentation", "testSourceChipOpensAndClosesInspector",
        "testDocumentSourceSearchEmptyAndClear", "testInspectorShowsIndexedRelatedDocument"]),
    ("AnytypeComprehensiveAcceptanceUITests", ["testInspectorEmbeddedSearchOpenReturnAndDocumentLink"]),
    ("PinkhaNativeDerivedAcceptanceUITests", ["testNativePropertiesPickerChipsSetMembershipAndRelaunch",
        "testSourceHeaderSelectionAndOverflow", "testUniversalPageNoteCustomPropertiesAndMixedSet"]),
    ("PinkhaNativeDerivedAcceptanceUITests", ["testRemainingNativeSourceFilterEditing",
        "testRemainingUniversalTypePickersAndMixedSet"]),
    ("PinkhaTorahPropertiesAcceptanceUITests", ["testOriginalPropertiesCanonicalLinkUnlinkAndRelaunchForAllWritingTypes"]),
    ("PinkhaStage1AcceptanceUITests", ["testAppWideDirectionPersistenceAndInteractiveBack",
        "testMultiBlockEnterCreationAndTypingLifecycle", "testDocumentSourcesEntryOpensExistingSearch"]),
]
UDID = "11111111-1111-1111-1111-111111111111"
DEVICE = {"udid": UDID, "name": "owned", "lane": "inspector",
          "device": {"identifier": "com.apple.CoreSimulator.SimDeviceType.iPad-Pro"},
          "runtime": {"identifier": "com.apple.CoreSimulator.SimRuntime.iOS-27-0"}}


def selection(name, device="ipad", language="en"):
    index = batch.LANES.index(name)
    suite, names = SPECS[index]
    return {"lane": name, "device_family": device, "app_language": language,
            "build_configuration": batch.CONFIGURATION, "expected_ui_executions": len(names),
            "expected_preparation_executions": 1, "preparation": batch.PREPARATIONS[index],
            "expected_postflight_executions": 1 if name == "properties-set" else 0,
            "postflight": batch.preservation.METHOD if name == "properties-set" else None,
            "methods": [suite + "/" + method for method in names]}


def inventory(devices):
    value = {"devices": {}}
    for device in devices:
        value["devices"].setdefault(device["runtime"]["identifier"], []).append({
            "udid": device["udid"], "name": device["name"], "state": "Shutdown", "isAvailable": True,
            "deviceTypeIdentifier": device["device"]["identifier"]})
    return value


def summary(methods, udid=UDID):
    return {"totalTestCount": len(methods), "passedTests": sum(value == "Passed" for value in methods.values()),
            "failedTests": sum(value == "Failed" for value in methods.values()), "skippedTests": 0,
            "devicesAndConfigurations": [{"device": {"deviceId": udid, "osVersion": "27.0",
                                                        "architecture": "arm64"}}]}


def frozen(root, device=None):
    runtime = root / "runtime.json"
    runtime.write_text("{}")
    return batch.FrozenBuild(root, root / "derived", root / "derived-ui", root / "Anytype.app",
        root / "native.xctestrun", root / "ui.xctestrun", Mock(), {"source_sha": "a" * 40}, {}, {}, (),
        runtime, batch.digest(runtime), {}, device)


def fresh_receipt(directory, udid):
    directory.mkdir(parents=True, exist_ok=True)
    stderr = b"Synthetic controller-only unclassified diagnostic\r\n"
    (directory / "container-lookup.stderr").write_bytes(stderr)
    return {"status": "FRESH_CREATED_DEVICE_BEFORE_NATIVE_PREPARATION", "simulator_udid": udid,
            "freshness_basis": "NEW_OWNED_DEVICE_BEFORE_FIRST_APP_INSTALL",
            "container_lookup_classification": "NEGATIVE_UNCLASSIFIED", "container_lookup_exit_code": 77,
            "container_lookup_stdout_sha256": batch.hashlib.sha256(b"").hexdigest(),
            "container_lookup_stderr_path": "container-lookup.stderr",
            "container_lookup_stderr_sha256": batch.hashlib.sha256(stderr).hexdigest(),
            "container_lookup_stderr_bytes": len(stderr)}


class BatchControls(unittest.TestCase):
    def tracked_fixture(self, root):
        def git(directory, *args):
            return subprocess.check_output(["git", "-C", str(directory), *args], text=True).strip()
        git(root, "init", "-q")
        git(root, "config", "user.name", "Controller fixture")
        git(root, "config", "user.email", "controller@example.invalid")
        lock = root / "Project/Package.resolved"
        lock.parent.mkdir()
        lock.write_text('{"pins": [], "version": 3}\n')
        snapshot = root / "Dependencies/Hanlin/.pinkha-source.json"
        snapshot.parent.mkdir(parents=True)
        snapshot.write_text("{}\n")
        (root / "source with spaces.swift").write_text("// Controller-only source fixture\n")
        git(root, "add", ".")
        git(root, "commit", "-qm", "Controller fixture")
        return types.SimpleNamespace(git=git), lock

    def test_real_git_lock_mutation_is_rejected_and_retained_before_any_lane(self):
        # Reproduce the observed incomplete lock's three missing dependencies
        # and originHash using the reviewed production lock, without Xcode.
        path = Path(__file__).resolve().parents[2] / "Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved"
        selected = json.loads(path.read_text())
        added = {"swift-ai-sdk", "swift-argument-parser", "swiftyjson"}
        self.assertTrue(added.issubset({item["identity"] for item in selected["pins"]}))
        old = {key: value for key, value in selected.items() if key != "originHash"}
        old["pins"] = [item for item in old["pins"] if item["identity"] not in added]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared, lock = self.tracked_fixture(root)
            lock.write_text(json.dumps(old))
            shared.git(root, "add", "Project/Package.resolved")
            shared.git(root, "commit", "-qm", "Incomplete controller fixture lock")
            original = batch.digest(lock)
            frozen_source = batch.source_snapshot(root, shared)
            lock.write_text(json.dumps(selected))
            with self.assertRaises(batch.TrackedSourceChanged) as raised:
                batch.source_snapshot(root, shared, stage="AFTER_APP_AND_NATIVE_TEST_BUILD")
            observed = raised.exception.observation
            self.assertEqual(observed["stage"], "AFTER_APP_AND_NATIVE_TEST_BUILD")
            self.assertEqual(observed["source_sha"], frozen_source["source_sha"])
            self.assertEqual(observed["changed_path_count"], 1)
            self.assertNotIn("diagnostic_error_type", observed)
            item, = observed["changes"]
            self.assertEqual(item["path"], "Project/Package.resolved")
            self.assertEqual(item["head_sha256"], original)
            self.assertEqual(item["worktree_sha256"], batch.digest(lock))
            self.assertNotEqual(item["head_sha256"], item["worktree_sha256"])
            self.assertEqual(frozen_source["package_locks"]["Project/Package.resolved"], original)
            args = argparse.Namespace(app=root, evidence=root / "evidence", derived=root / "build/derived",
                                      deadline=time.monotonic() + batch.WORKER_SECONDS - 1)
            lane = types.SimpleNamespace(plan=selection, execute=Mock())
            with patch.object(batch, "build_once", side_effect=raised.exception):
                code = batch.worker(args, lane, {"parent_pid": os.getppid()})
            receipt = json.loads((args.evidence / "batch-worker.json").read_text())
            self.assertEqual(code, 1)
            self.assertEqual(receipt["status"], "BATCH_ABORTED_SETUP_OR_IDENTITY")
            self.assertEqual(receipt["tracked_source_change"], observed)
            self.assertEqual(set(receipt["lane_statuses"].values()), {"NOT_RUN_SETUP"})
            lane.execute.assert_not_called()

    def test_unexpected_tracked_changes_still_fail_with_names_and_hashes_only(self):
        for mutation in ("edit", "delete", "staged"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                shared, _ = self.tracked_fixture(root)
                path = root / "source with spaces.swift"
                original = batch.digest(path)
                if mutation == "delete":
                    path.unlink()
                else:
                    path.write_text("// Changed controller-only source fixture\n")
                    if mutation == "staged":
                        shared.git(root, "add", path.name)
                with self.assertRaises(batch.TrackedSourceChanged) as raised:
                    batch.source_snapshot(root, shared)
                observed = raised.exception.observation
                self.assertEqual(observed["changed_path_count"], 1)
                self.assertNotIn("diagnostic_error_type", observed)
                item, = observed["changes"]
                self.assertEqual(item["path"], path.name)
                self.assertEqual(item["head_sha256"], original)
                self.assertEqual(item["worktree_kind"], "missing" if mutation == "delete" else "file")
                self.assertNotIn("Controller-only source", json.dumps(observed))
                self.assertNotIn("Changed controller-only source", json.dumps(observed))

    def test_diagnostic_error_cannot_make_dirty_source_pass(self):
        shared = types.SimpleNamespace(git=Mock(side_effect=[" M source.swift", OSError("diagnostic unavailable")]))
        with self.assertRaises(batch.TrackedSourceChanged) as raised:
            batch.source_snapshot(Path("."), shared)
        self.assertEqual(raised.exception.observation["diagnostic_error_type"], "OSError")
        self.assertEqual(raised.exception.observation["porcelain_observation"], " M source.swift")

    def test_canonical_lane_module_declares_the_untrimmed_six_lanes(self):
        if importlib.util.find_spec("run_wave15_acceptance") is None:
            self.skipTest("Canonical lane source is not copied into Scratch; run this control in the repository")
        import run_wave15_acceptance as lane
        plans = batch.plan(lane)
        self.assertEqual([item["methods"] for item in plans], [selection(name)["methods"] for name in batch.LANES])
        self.assertEqual(sum(item["expected_ui_executions"] for item in plans), 15)
        self.assertEqual(len(plans), 6)

    def test_profile_rejects_changed_configuration_count_or_preparation(self):
        lane = types.SimpleNamespace(plan=selection)
        self.assertEqual(len(batch.plan(lane)), 6)
        for key, replacement in [("build_configuration", "Debug-Anytype"),
                                 ("expected_ui_executions", 1), ("preparation", "OtherSuite/test")]:
            with self.subTest(key=key):
                def changed(name, device, language):
                    value = selection(name, device, language)
                    if name == "inspector":
                        value[key] = replacement
                    return value
                with self.assertRaises(RuntimeError):
                    batch.plan(types.SimpleNamespace(plan=changed))

    def test_original_products_and_resources_are_frozen_and_external_links_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "App.app"
            root.mkdir()
            (root / "code").write_bytes(b"compiled-code")
            (root / "resource").write_bytes(b"title")
            first = batch.bundle_manifest(root)
            (root / "resource").write_bytes(b"changed-title")
            self.assertNotEqual(first, batch.bundle_manifest(root))
            if os.name == "posix":
                outside = root.parent / "outside"
                outside.write_text("not a selected bundle input")
                (root / "escape").symlink_to(outside)
                with self.assertRaisesRegex(RuntimeError, "external dependency"):
                    batch.bundle_manifest(root)

    def test_explicit_selection_replaces_old_union_and_preserves_testroot_and_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = Path(temporary) / "Products/native.xctestrun"
            original.parent.mkdir()
            target = {"BlueprintName": "AnytypeTests", "TestHostPath": "__TESTROOT__/Anytype.app/Anytype",
                      "OnlyTestIdentifiers": ["OtherPreparation", "TorahT5RuntimePairTests"],
                      "SkipTestIdentifiers": ["TorahNativeDerivedProductIntegrationTests"]}
            original.write_bytes(plistlib.dumps({"TestConfigurations": [{"TestTargets": [target]}]}))
            before = original.read_bytes()
            selected = batch.explicit_selection(original, "AnytypeTests", [batch.PREPARATIONS[2]], {},
                                                 types.SimpleNamespace(inject=lambda *args: None))
            actual = plistlib.loads(selected.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
            self.assertEqual(actual["OnlyTestIdentifiers"], ["TorahNativeDerivedProductIntegrationTests"])
            self.assertEqual(actual["SkipTestIdentifiers"], [])
            self.assertEqual(actual["TestHostPath"], target["TestHostPath"])
            self.assertEqual(selected.parent, original.parent)
            self.assertEqual(original.read_bytes(), before)

    def test_ambiguous_xctestrun_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            original = Path(temporary) / "original.xctestrun"
            original.write_bytes(plistlib.dumps({"targets": [{"BlueprintName": "AnytypeTests"}] * 2}))
            with self.assertRaises(RuntimeError):
                batch.explicit_selection(original, "AnytypeTests", [batch.PREPARATIONS[0]], {}, Mock())

    def test_original_results_must_match_every_named_case_and_actual_destination(self):
        expected = selection("properties-set")["methods"]
        methods = {name + "()": "Passed" for name in expected}
        valid = summary(methods)
        batch.validate_observed_result(valid, methods, expected, UDID, passing=True)
        for mutate in [lambda value: value.update(totalTestCount=999),
                       lambda value: value.update(passedTests=True),
                       lambda value: value.update(skippedTests=1),
                       lambda value: value["devicesAndConfigurations"][0]["device"].update(deviceId="another"),
                       lambda value: value["devicesAndConfigurations"][0]["device"].update(architecture="x86_64"),
                       lambda value: value["devicesAndConfigurations"][0]["device"].update(osVersion="26.0")]:
            value = copy.deepcopy(valid)
            mutate(value)
            with self.subTest(summary=value), self.assertRaises(RuntimeError):
                batch.validate_observed_result(value, methods, expected, UDID, passing=True)
        for wrong in [{expected[0]: "Passed"}, {expected[0]: "Passed", "Other/test()": "Passed"},
                      {expected[0]: "Passed", expected[0] + "()": "Passed"},
                      {expected[0]: "Passed", expected[1]: "Skipped"}]:
            with self.subTest(methods=wrong), self.assertRaises(RuntimeError):
                batch.validate_observed_result(summary(wrong), wrong, expected, UDID, passing=True)

    def test_only_an_original_failed_case_qualifies_for_continuation(self):
        expected = selection("inspector")["methods"]
        methods = {expected[0] + "()": "Failed"}
        result = batch.validate_observed_result(summary(methods), methods, expected, UDID, passing=False)
        self.assertEqual(result["original_counts"]["failedTests"], 1)
        for wrong in [{}, {expected[0]: "Passed"}, {"Other/test": "Failed"}, {expected[0]: "Skipped"}]:
            with self.subTest(methods=wrong), self.assertRaises(RuntimeError):
                batch.validate_observed_result(summary(wrong), wrong, expected, UDID, passing=False)

    def test_fixture_reuse_is_rejected_before_ui_even_with_a_fresh_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = frozen(root, DEVICE)
            directory = root / UDID / "data/container"
            directory.mkdir(parents=True)
            context.observe_fixture({"spaceId": "real-observed-space-A"}, directory, root / "first")
            other_id = "22222222-2222-2222-2222-222222222222"
            other = replace(context, device={**DEVICE, "udid": other_id, "lane": "properties-set"})
            second = root / other_id / "data/container"
            second.mkdir(parents=True)
            with self.assertRaisesRegex(RuntimeError, "reused"):
                other.observe_fixture({"spaceId": "real-observed-space-A"}, second, root / "second")
            other.observe_fixture({"spaceId": "real-observed-space-B"}, second, root / "second")
            with self.assertRaises(RuntimeError):
                other.observe_fixture({"spaceId": "third"}, root / "foreign", root / "third")

    def test_fresh_creation_basis_does_not_misclassify_lookup_failure_as_absence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = frozen(root, DEVICE)
            observed = inventory([DEVICE])
            observed["devices"][DEVICE["runtime"]["identifier"]][0]["state"] = "Booted"
            stderr = b"Unclassified failure, not a missing-container contract\r\n"
            cases = [(77, b"", True), (0, b"", False), (0, b"/some/container\n", False),
                     (77, b"unexpected stdout", False), (77, b" \n", False)]
            for index, (code, stdout, accepted_construction) in enumerate(cases):
                with self.subTest(code=code, stdout=stdout):
                    directory = root / str(index)
                    directory.mkdir()
                    with patch.object(batch.subprocess, "check_output", return_value=json.dumps(observed).encode()) as query, \
                         patch.object(batch.subprocess, "run", return_value=types.SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)) as lookup:
                        if accepted_construction:
                            context.confirm_empty_container(UDID, directory)
                        else:
                            with self.assertRaises(RuntimeError):
                                context.confirm_empty_container(UDID, directory)
                    query.assert_called_once_with(["xcrun", "simctl", "list", "devices", UDID, "--json"], timeout=120)
                    lookup.assert_called_once_with(["xcrun", "simctl", "get_app_container", UDID, batch.BUNDLE, "data"],
                                                   capture_output=True, timeout=30)
                    receipt = json.loads((directory / "fresh-container.json").read_text())
                    self.assertEqual((directory / "container-lookup.stderr").read_bytes(), stderr)
                    self.assertEqual(receipt["container_lookup_stderr_sha256"], batch.hashlib.sha256(stderr).hexdigest())
                    self.assertEqual(receipt["freshness_basis"], "NEW_OWNED_DEVICE_BEFORE_FIRST_APP_INSTALL")
                    self.assertEqual(receipt["status"], "FRESH_CREATED_DEVICE_BEFORE_NATIVE_PREPARATION" if accepted_construction else "FAIL")
                    if accepted_construction:
                        self.assertEqual(receipt["container_lookup_classification"], "NEGATIVE_UNCLASSIFIED")
                        batch.validate_fresh_device_receipt(receipt, directory, UDID)
            for exception in [subprocess.TimeoutExpired("simctl", 30), OSError("probe could not start")]:
                directory = root / type(exception).__name__
                directory.mkdir()
                with patch.object(batch.subprocess, "check_output", return_value=json.dumps(observed).encode()), \
                     patch.object(batch.subprocess, "run", side_effect=exception), self.assertRaises(type(exception)):
                    context.confirm_empty_container(UDID, directory)
                self.assertFalse((directory / "fresh-container.json").exists())

    def test_fresh_receipt_consumer_requires_exact_basis_and_original_stderr(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            original = fresh_receipt(directory, UDID)
            batch.validate_fresh_device_receipt(original, directory, UDID)
            for key, value in [("status", "OBSERVED_ABSENT_BEFORE_NATIVE_PREPARATION"),
                               ("freshness_basis", "LOOKUP_FAILED"),
                               ("container_lookup_classification", "CONTAINER_NOT_FOUND"),
                               ("container_lookup_exit_code", 0), ("container_lookup_exit_code", True),
                               ("container_lookup_stdout_sha256", "other"),
                               ("container_lookup_stderr_path", "../other"),
                               ("container_lookup_stderr_sha256", "other"),
                               ("container_lookup_stderr_bytes", -1)]:
                with self.subTest(key=key), self.assertRaises(RuntimeError):
                    batch.validate_fresh_device_receipt({**original, key: value}, directory, UDID)
            (directory / "container-lookup.stderr").write_bytes(b"changed diagnostic")
            with self.assertRaisesRegex(RuntimeError, "stderr differs"):
                batch.validate_fresh_device_receipt(original, directory, UDID)

    def test_source_flags_runtime_and_products_cannot_drift_between_lanes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = frozen(root)
            source = {"source_sha": "a" * 40, "package_locks": {"Package.resolved": "pin"}}
            context = replace(context, source=source, artifacts={"bundle": "same"})
            with patch.object(batch, "source_snapshot", return_value=source), \
                 patch.object(batch.FrozenBuild, "observed_artifacts", return_value={"bundle": "same"}):
                context.verify(root, "a" * 40, {"hashes": {}}, batch.FLAGS, batch.CONFIGURATION)
                with self.assertRaises(RuntimeError):
                    context.verify(root, "a" * 40, {"hashes": {}}, [*batch.FLAGS, "-D PINKHA_NATIVE_T5_LOOKUP_V1"], batch.CONFIGURATION)
                with patch.object(batch, "source_snapshot", return_value={**source, "package_locks": {"Package.resolved": "changed"}}), \
                     self.assertRaises(RuntimeError):
                    context.verify(root, "a" * 40, {"hashes": {}}, batch.FLAGS, batch.CONFIGURATION)
                with patch.object(batch.FrozenBuild, "observed_artifacts", return_value={"bundle": "re-signed"}), \
                     self.assertRaises(RuntimeError):
                    context.verify(root, "a" * 40, {"hashes": {}}, batch.FLAGS, batch.CONFIGURATION)
                context.runtime_receipt_path.write_text('{"different":"runtime"}')
                with self.assertRaises(RuntimeError):
                    context.verify(root, "a" * 40, {"hashes": {}}, batch.FLAGS, batch.CONFIGURATION)

    def test_creation_before_receipt_can_only_recover_the_unique_new_planned_device(self):
        owner = {key: value for key, value in DEVICE.items() if key != "udid"}
        observed = inventory([DEVICE])
        self.assertEqual(batch.resolve_cleanup_device(observed, owner, [], None), DEVICE)
        self.assertIsNone(batch.resolve_cleanup_device(inventory([{**DEVICE, "name": "unrelated"}]), owner, []))
        with self.assertRaises(RuntimeError):
            batch.resolve_cleanup_device(observed, owner, [UDID])
        with self.assertRaises(RuntimeError):
            batch.resolve_cleanup_device(observed, owner, [], {**DEVICE, "udid": "changed"})
        with self.assertRaises(RuntimeError):
            batch.resolve_cleanup_device(inventory([DEVICE, {**DEVICE, "udid": "duplicate"}]), owner, [])
        for key, value in [("runtime", {"identifier": "wrong-runtime"}), ("device", {"identifier": "wrong-type"})]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                batch.resolve_cleanup_device(observed, {**owner, key: value}, [])

    def test_cleanup_preflight_uses_exact_uid_even_if_an_old_same_name_device_exists(self):
        observed = inventory([DEVICE, {**DEVICE, "udid": "unrelated-old-uid"}])
        self.assertEqual(batch.resolve_cleanup_device(observed, DEVICE, [UDID]), DEVICE)
        with self.assertRaises(RuntimeError):
            batch.resolve_cleanup_device(observed, {**DEVICE, "name": "another-name"}, [UDID])

    def test_scoped_inventory_rejects_aliases_substrings_foreign_rows_and_invalid_shapes(self):
        owner = {key: value for key, value in DEVICE.items() if key != "udid"}
        good = inventory([DEVICE])
        for identity, selector in ((DEVICE, UDID), (owner, DEVICE["name"])):
            with self.subTest(selector=selector), \
                 patch.object(batch.subprocess, "check_output", return_value=json.dumps(good).encode()) as query:
                self.assertEqual(batch.scoped_device_inventory(identity, timeout=20), good)
                query.assert_called_once_with(["xcrun", "simctl", "list", "devices", selector, "--json"], timeout=20)
        for identity, timeout in (({**DEVICE, "udid": "booted"}, 20), ({**DEVICE, "udid": "all"}, 20),
                                  ({**DEVICE, "udid": None}, 20), ({**owner, "name": ""}, 20),
                                  (DEVICE, 121), (DEVICE, float("inf")), (DEVICE, 0)):
            with self.subTest(identity=identity, timeout=timeout), patch.object(batch.subprocess, "check_output") as query:
                with self.assertRaises(RuntimeError):
                    batch.scoped_device_inventory(identity, timeout=timeout)
                query.assert_not_called()
        wrong = inventory([{**DEVICE, "udid": "22222222-2222-2222-2222-222222222222"}])
        malformed = [[], {}, {"devices": []}, {"devices": {"runtime": {}}},
                     {"devices": {"runtime": [None]}}, inventory([{**DEVICE, "udid": "booted"}]), wrong]
        for value in malformed:
            with self.subTest(value=value), \
                 patch.object(batch.subprocess, "check_output", return_value=json.dumps(value).encode()):
                with self.assertRaises(RuntimeError):
                    batch.scoped_device_inventory(DEVICE, timeout=20)
        with patch.object(batch.subprocess, "check_output", return_value=json.dumps(
                inventory([{**DEVICE, "name": DEVICE["name"] + "-other"}])).encode()), self.assertRaises(RuntimeError):
            batch.scoped_device_inventory(owner, timeout=20)

    def test_scoped_admission_keeps_every_identity_guard_before_container_query(self):
        variants = []
        for field, value in (("name", "another"), ("state", "Shutdown"), ("isAvailable", False),
                             ("deviceTypeIdentifier", "another-type")):
            observed = inventory([DEVICE])
            item = observed["devices"][DEVICE["runtime"]["identifier"]][0]
            item["state"] = "Booted"
            item[field] = value
            variants.append(observed)
        wrong_runtime = inventory([DEVICE])
        wrong_runtime["devices"]["another-runtime"] = wrong_runtime["devices"].pop(DEVICE["runtime"]["identifier"])
        variants += [wrong_runtime, inventory([]), inventory([DEVICE, DEVICE])]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = frozen(root, DEVICE)
            for index, observed in enumerate(variants):
                directory = root / str(index)
                directory.mkdir()
                with self.subTest(index=index), \
                     patch.object(batch.subprocess, "check_output", return_value=json.dumps(observed).encode()), \
                     patch.object(batch.subprocess, "run") as lookup, self.assertRaises(RuntimeError):
                    context.confirm_empty_container(UDID, directory)
                lookup.assert_not_called()
                self.assertFalse((directory / "fresh-container.json").exists())

    def test_cleanup_uses_recorded_udids_and_skips_a_lane_that_never_started(self):
        preflight = {**DEVICE, "udid": "22222222-2222-2222-2222-222222222222", "name": "preflight"}
        owner = {key: value for key, value in DEVICE.items() if key != "udid"}
        unstarted = {**owner, "lane": "editor", "name": "never-created"}
        intent = {"preflight_devices": [preflight], "lane_devices": [owner, unstarted],
                  "baseline_udids": [preflight["udid"]]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            batch.write(root / "lanes/inspector/owned-simulator.json", DEVICE)
            queries, actions = [], []
            def query(command, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 120)
                self.assertEqual(command[:4], ["xcrun", "simctl", "list", "devices"])
                self.assertEqual(command[-1], "--json")
                queries.append(command[4])
                device = next(row for row in (preflight, DEVICE) if row["udid"] == command[4])
                value = inventory([device])
                value["devices"][device["runtime"]["identifier"]][0]["state"] = "Booted"
                return json.dumps(value).encode()
            def action(command, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 20)
                actions.append(command[2:])
                return types.SimpleNamespace(returncode=0)
            with patch.object(batch.subprocess, "check_output", side_effect=query), \
                 patch.object(batch.subprocess, "run", side_effect=action):
                result = batch.cleanup_owned(intent, root)
            self.assertEqual(queries, [preflight["udid"], UDID])
            self.assertEqual(actions, [[operation, identity] for identity in queries for operation in ("shutdown", "delete")])
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["devices"][-1], {"name": unstarted["name"], "status": "NOT_STARTED"})

    def test_slow_scoped_inventory_succeeds_once_without_extending_container_lookup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observed = inventory([DEVICE])
            observed["devices"][DEVICE["runtime"]["identifier"]][0]["state"] = "Booted"
            with patch.object(batch.time, "monotonic", side_effect=[1000.0, 1073.25]), \
                 patch.object(batch.subprocess, "check_output", return_value=json.dumps(observed).encode()) as query, \
                 patch.object(batch.subprocess, "run", return_value=types.SimpleNamespace(
                     returncode=77, stdout=b"", stderr=b"unclassified lookup")) as lookup:
                frozen(root, DEVICE).confirm_empty_container(UDID, root)
            query.assert_called_once_with(["xcrun", "simctl", "list", "devices", UDID, "--json"], timeout=120)
            lookup.assert_called_once_with(["xcrun", "simctl", "get_app_container", UDID, batch.BUNDLE, "data"],
                                           capture_output=True, timeout=30)
            observation = json.loads((root / "fresh-device-query.json").read_text())
            self.assertEqual(observation, {"status": "RETURNED_VALID_SCOPED_INVENTORY", "selector": UDID,
                "selector_kind": "OWNED_UDID", "timeout_seconds": 120, "elapsed_seconds": 73.25})
            batch.validate_fresh_device_receipt(json.loads((root / "fresh-container.json").read_text()), root, UDID)

    def test_cleanup_query_observes_elapsed_and_remaining_budget_without_extending_actions(self):
        # Simulated monotonic time verifies slow success without sleeping.
        for times, query_timeout, elapsed, action_timeouts in [
                ([1000, 1000, 1000, 1073.25, 1073.25, 1073.25], 120, 73.25, [20, 20]),
                ([1000, 1135, 1135, 1148, 1148, 1163], 45, 13, [20, 17])]:
            with self.subTest(query_timeout=query_timeout), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                observed = inventory([DEVICE])
                observed["devices"][DEVICE["runtime"]["identifier"]][0]["state"] = "Booted"
                with patch.object(batch.time, "monotonic", side_effect=times), \
                     patch.object(batch.subprocess, "check_output", return_value=json.dumps(observed).encode()) as query, \
                     patch.object(batch.subprocess, "run", return_value=types.SimpleNamespace(returncode=0)) as action:
                    result = batch.cleanup_owned({"preflight_devices": [DEVICE], "lane_devices": [],
                                                  "baseline_udids": [UDID]}, root)
                query.assert_called_once_with(["xcrun", "simctl", "list", "devices", UDID, "--json"], timeout=query_timeout)
                self.assertEqual([call.args[0] for call in action.call_args_list],
                    [["xcrun", "simctl", name, UDID] for name in ["shutdown", "delete"]])
                self.assertEqual([call.kwargs["timeout"] for call in action.call_args_list], action_timeouts)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["inventory_queries"], [{"status": "RETURNED_VALID_SCOPED_INVENTORY",
                    "selector": UDID, "selector_kind": "OWNED_UDID", "timeout_seconds": query_timeout,
                    "elapsed_seconds": elapsed}])

    def test_cleanup_recovers_by_exact_nonce_name_and_rejects_unbound_receipts(self):
        owner = {key: value for key, value in DEVICE.items() if key != "udid"}
        intent = {"preflight_devices": [], "lane_devices": [owner], "baseline_udids": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / "lanes/inspector"
            directory.mkdir(parents=True)
            with patch.object(batch.subprocess, "check_output", return_value=json.dumps(inventory([DEVICE])).encode()) as query, \
                 patch.object(batch.subprocess, "run", return_value=types.SimpleNamespace(returncode=0)) as action:
                result = batch.cleanup_owned(intent, root)
            self.assertEqual(result["status"], "PASS")
            query.assert_called_once()
            self.assertEqual(query.call_args.args[0], ["xcrun", "simctl", "list", "devices", owner["name"], "--json"])
            self.assertEqual(action.call_args.args[0], ["xcrun", "simctl", "delete", UDID])
            bad_inventory = [inventory([{**DEVICE, "name": owner["name"] + "-foreign"}]),
                             inventory([DEVICE, {**DEVICE, "udid": "22222222-2222-2222-2222-222222222222"}]),
                             inventory([{**DEVICE, "runtime": {"identifier": "foreign-runtime"}}])]
            for value in bad_inventory:
                with self.subTest(inventory=value), \
                     patch.object(batch.subprocess, "check_output", return_value=json.dumps(value).encode()), \
                     patch.object(batch.subprocess, "run") as action, self.assertRaises(RuntimeError):
                    batch.cleanup_owned(intent, root)
                action.assert_not_called()
                self.assertEqual(json.loads((root / "batch-cleanup.json").read_text())["status"], "FAIL")
            with patch.object(batch.subprocess, "check_output", return_value=json.dumps(inventory([DEVICE])).encode()), \
                 patch.object(batch.subprocess, "run") as action, self.assertRaises(RuntimeError):
                batch.cleanup_owned({**intent, "baseline_udids": [UDID]}, root)
            action.assert_not_called()
            for changed in ({**DEVICE, "udid": "booted"}, {**DEVICE, "name": "foreign"},
                            {**DEVICE, "runtime": {"identifier": "foreign-runtime"}}):
                batch.write(directory / "owned-simulator.json", changed)
                with self.subTest(receipt=changed), patch.object(batch.subprocess, "check_output") as query, \
                     patch.object(batch.subprocess, "run") as action, self.assertRaises(RuntimeError):
                    batch.cleanup_owned(intent, root)
                query.assert_not_called()
                action.assert_not_called()
            batch.write(directory / "owned-simulator.json", DEVICE)
            with patch.object(batch.subprocess, "check_output") as query, \
                 patch.object(batch.subprocess, "run") as action, self.assertRaises(RuntimeError):
                batch.cleanup_owned({**intent, "baseline_udids": [UDID]}, root)
            query.assert_not_called()
            action.assert_not_called()

    def test_scoped_timeout_or_cancellation_never_retries_global_inventory_or_claims_freshness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = frozen(root, DEVICE)
            for error in (subprocess.TimeoutExpired(["xcrun", "simctl", "list", "devices", UDID, "--json"], 120,
                                                    output=b"private-partial-stdout", stderr=b"private-partial-stderr"),
                          KeyboardInterrupt()):
                with self.subTest(error=type(error).__name__), patch.object(batch.subprocess, "check_output", side_effect=error) as query, \
                     patch.object(batch.subprocess, "run") as action, patch.object(batch.time, "monotonic", return_value=1000):
                    with self.assertRaises(type(error)) as caught:
                        context.confirm_empty_container(UDID, root)
                    self.assertIs(caught.exception, error)
                    query.assert_called_once_with(["xcrun", "simctl", "list", "devices", UDID, "--json"], timeout=120)
                    action.assert_not_called()
                    self.assertFalse((root / "fresh-container.json").exists())
                    observation = json.loads((root / "fresh-device-query.json").read_text())
                    self.assertEqual(observation, {"status": "CANCELLED" if isinstance(error, KeyboardInterrupt) else "TIMED_OUT",
                        "selector": UDID, "selector_kind": "OWNED_UDID", "timeout_seconds": 120,
                        "elapsed_seconds": 0, "error_type": type(error).__name__})
                    self.assertNotIn("private-partial", (root / "fresh-device-query.json").read_text())
                    query.reset_mock()
                    with self.assertRaises(type(error)) as caught:
                        batch.cleanup_owned({"preflight_devices": [DEVICE], "lane_devices": [], "baseline_udids": [UDID]}, root)
                    self.assertIs(caught.exception, error)
                    query.assert_called_once_with(["xcrun", "simctl", "list", "devices", UDID, "--json"], timeout=120)
                    action.assert_not_called()
                    result = json.loads((root / "batch-cleanup.json").read_text())
                    self.assertEqual(result["status"], "CANCELLED" if isinstance(error, KeyboardInterrupt) else "FAIL")
                    self.assertEqual(result["devices"], [])
                    self.assertEqual(result["inventory_queries"], [observation])
                    self.assertNotIn("private-partial", (root / "batch-cleanup.json").read_text())

    def test_existing_fixed_caps_and_per_lane_test_limits_are_explicit(self):
        self.assertEqual(batch.WORKER_SECONDS, 105 * 60)
        self.assertEqual(batch.CLEANUP_SECONDS, 180)
        self.assertEqual(batch.SCOPED_DEVICE_QUERY_SECONDS, 120)
        self.assertLess(batch.WORKER_SECONDS + batch.CLEANUP_SECONDS, 120 * 60)
        self.assertEqual(batch.STEP_SECONDS, 120 * 60)
        self.assertEqual(batch.minimum_lane_budget(selection("inspector")), 6 * 300 + 180)
        self.assertEqual(batch.preservation.INSTALLATION_SECONDS, 660)
        self.assertEqual(batch.minimum_lane_budget(selection("properties-set")), 4 * 300 + 180 + 660)
        self.assertEqual(batch.minimum_lane_budget(selection("properties")), 2100 + 300 + 180)
        self.assertEqual(batch.minimum_lane_budget(selection("editor")), 4 * 300 + 180)
        changed = selection("properties")
        changed["expected_ui_executions"] += 1
        with self.assertRaisesRegex(RuntimeError, "exact declared UI method"):
            batch.minimum_lane_budget(changed)

    def test_properties_set_cannot_omit_postflight_from_budget_or_profile(self):
        for key, value in [("expected_postflight_executions", 0), ("postflight", None),
                           ("postflight", "TorahNativeDerivedProductIntegrationTests/originalProductPipeline")]:
            selected = selection("properties-set"); selected[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(RuntimeError):
                batch.minimum_lane_budget(selected)

    def test_batch_pass_requires_six_original_preparations_and_fifteen_original_ui_cases(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            source = {"source_sha": "a" * 40}
            intent = {"source_sha": source["source_sha"], "run_id": "123", "run_attempt": "1",
                      "baseline_udids": [], "lane_devices": []}
            build_path = evidence / "batch-build/same-job-build.json"
            batch.write(build_path, {"status": "SAME_JOB_SUCCESSFUL_BUILD_WITH_FROZEN_PRODUCTS", "source": source,
                                     "build_flags": batch.FLAGS, "configuration": batch.CONFIGURATION,
                                     "previous_artifact_reuse": False})
            build_sha = batch.digest(build_path)
            receipt = {"protocol": batch.PROTOCOL, "profile": batch.PROFILE, "source": source,
                       "status": "BATCH_PASS_ACCEPTANCE_REVIEW_PENDING", "planned_ui_methods": 15,
                       "planned_native_preparations": 6, "planned_native_postflights": 1, "build_receipt_sha256": build_sha,
                       "lane_statuses": {name: "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" for name in batch.LANES},
                       "lane_receipts": {}}
            for index, name in enumerate(batch.LANES):
                directory = evidence / "lanes" / name
                device = {**DEVICE, "lane": name, "name": "unique-" + name, "udid": str(index) + UDID[1:]}
                intent["lane_devices"].append({key: value for key, value in device.items() if key != "udid"})
                batch.write(directory / "owned-simulator.json", device)
                batch.write(directory / "fresh-container.json", fresh_receipt(directory, device["udid"]))
                batch.write(directory / "fixture-isolation.json", {"simulator_udid": device["udid"],
                    "space_id": "synthetic-controller-space-" + name, "container": "synthetic-controller-container-" + name})
                original = {"status": "LANE_PASS_ACCEPTANCE_REVIEW_PENDING", "source_sha": source["source_sha"],
                            "run_id": "123", "run_attempt": "1", "same_job_build_receipt_sha256": build_sha}
                if name == "properties-set":
                    gate = batch.preservation
                    bound = gate.binding(source["source_sha"], "123", "1", "b" * 32)
                    container_path = "/controller-only/" + device["udid"] + "/data"
                    identity = {"path": container_path, "device": "1", "inode": "2", "createdAt": 1700000000.0}
                    directories = {"container": identity, "middleware": {
                        **identity, "path": str(Path(container_path) / gate.STORE), "inode": "3"}}
                    baseline = preservation_controls.baseline(directories)
                    baseline["binding"] = bound
                    raw = json.dumps(baseline).encode()
                    (directory / "type-preservation-baseline.json").write_bytes(raw)
                    baseline_sha = gate.sha256(raw)
                    raw_fixture = json.dumps(preservation_controls.fixture()).encode()
                    (directory / "type-preservation-fixture.json").write_bytes(raw_fixture)
                    fixture_sha = gate.sha256(raw_fixture)
                    installation = preservation_controls.installation_proof(
                        baseline, baseline_sha, fixture_sha, device["udid"], directories)
                    raw_installation = preservation_controls.installation_bytes(installation)
                    (directory / gate.INSTALLATION).write_bytes(raw_installation)
                    installation_sha = gate.sha256(raw_installation)
                    batch.write(directory / "built-code-carriers.json", {"sha256": preservation_controls.CODE_SHA})
                    native = preservation_controls.native_receipt(baseline, baseline_sha, installation)
                    raw_native = json.dumps(native).encode()
                    (directory / "postflight").mkdir()
                    (directory / "postflight/native-result.json").write_bytes(raw_native)
                    post = preservation_controls.result()
                    post["actual_devices"][0]["deviceId"] = device["udid"]
                    original.update(postflight_binding=bound, preservation_baseline_sha256=baseline_sha,
                                    preservation_fixture_sha256=fixture_sha, preservation_installation_sha256=installation_sha,
                                    preservation_native_receipt_sha256=gate.sha256(raw_native), postflight=post)
                    original["type_preservation"] = gate.validate_native_receipt(
                        baseline, baseline_sha, device["udid"], native, post, installation, installation_sha)
                    batch.write(directory / "fixture-ids.json", preservation_controls.fixture())
                    batch.write(directory / "type-preservation-inputs.json", {"binding": bound,
                        "baseline_sha256": baseline_sha, "fixture_sha256": fixture_sha, "directories": directories,
                        "simulator_udid": device["udid"], "source": "FROZEN_BEFORE_UI"})
                    methods = {gate.METHOD + "()": "Passed"}
                    batch.write(directory / "postflight" / (gate.PREFIX + "-summary.json"), summary(methods, device["udid"]))
                    batch.write(directory / "postflight" / (gate.PREFIX + "-tests.json"), methods)
                batch.write(directory / "execution.json", original)
                receipt["lane_receipts"][name] = {"path": "lanes/" + name + "/execution.json",
                                                   "sha256": batch.digest(directory / "execution.json")}
                selected = selection(name)
                for phase, prefix, names in [("preparation", "prepare", [selected["preparation"]]),
                                             ("ui", "wave15-" + name, selected["methods"])]:
                    methods = {method + "()": "Passed" for method in names}
                    batch.write(directory / phase / (prefix + "-summary.json"), summary(methods, device["udid"]))
                    batch.write(directory / phase / (prefix + "-tests.json"), methods)
            lane = types.SimpleNamespace(plan=selection, shared=types.SimpleNamespace(method_results=lambda value: value))
            batch.validate_worker_conclusion(receipt, intent, evidence, lane)
            post_summary = evidence / "lanes/properties-set/postflight" / (batch.preservation.PREFIX + "-summary.json")
            saved_post = post_summary.read_bytes()
            post_summary.unlink()
            with self.assertRaises(FileNotFoundError):
                batch.validate_worker_conclusion(receipt, intent, evidence, lane)
            post_summary.write_bytes(saved_post)
            missing = copy.deepcopy(receipt)
            missing["lane_receipts"].pop("properties")
            with self.assertRaisesRegex(RuntimeError, "six passing"):
                batch.validate_worker_conclusion(missing, intent, evidence, lane)
            changed = evidence / "lanes/properties/ui/wave15-properties-summary.json"
            before = changed.read_bytes()
            value = json.loads(before)
            value["totalTestCount"] = 999
            batch.write(changed, value)
            with self.assertRaisesRegex(RuntimeError, "counts"):
                batch.validate_worker_conclusion(receipt, intent, evidence, lane)
            changed.write_bytes(before)
            fixture = evidence / "lanes/properties-set/fixture-isolation.json"
            value = json.loads(fixture.read_text())
            value["space_id"] = "synthetic-controller-space-properties"
            batch.write(fixture, value)
            with self.assertRaisesRegex(RuntimeError, "independent fresh"):
                batch.validate_worker_conclusion(receipt, intent, evidence, lane)

    def test_first_cancellation_in_cleanup_or_publication_is_not_swallowed(self):
        for phase in ["cleanup", "publication", "signals_worker", "signals_cleanup", "signals_publication", "diagnostics"]:
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                args = argparse.Namespace(app=root, evidence=root / "build/evidence", derived=root / "build/derived",
                                          device="ipad", language="en")
                preflight_device = {**DEVICE, "name": "Pinkha-UI27-123-ipad"}
                preflight = {"source_sha": "a" * 40, "run_id": "123", "run_attempt": "1",
                             "status": "PREFLIGHT_PASS_UI_NOT_RUN", "selected": {"ipad": preflight_device}}
                batch.write(args.evidence / "preflight/preflight.json", preflight)
                original_write = batch.write
                original_diagnostics = batch.publish_batch_observations
                cancellation_sent = False
                cleanup_finished = False

                def mock_worker(*values):
                    original_write(args.evidence / "batch-worker.json", {"protocol": batch.PROTOCOL,
                        "profile": batch.PROFILE, "status": "BATCH_ABORTED_SETUP_OR_IDENTITY",
                        "planned_ui_methods": 15, "planned_native_preparations": 6, "planned_native_postflights": 1,
                        "lane_statuses": {name: "NOT_RUN_SETUP" for name in batch.LANES}})
                    if phase == "signals_worker":
                        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                    return {"return_code": 1}

                def publish(path, value):
                    nonlocal cancellation_sent
                    if phase == "publication" and path.name == "execution.json" and value["status"] != "FAIL" and not cancellation_sent:
                        cancellation_sent = True
                        raise KeyboardInterrupt()
                    if phase == "signals_publication" and path.name == "execution.json" and value["status"] != "FAIL" and not cancellation_sent:
                        cancellation_sent = True
                        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                        signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
                    original_write(path, value)

                def cleanup(*values):
                    nonlocal cleanup_finished
                    if phase == "cleanup":
                        raise KeyboardInterrupt()
                    if phase in {"signals_worker", "signals_cleanup"}:
                        signal.getsignal(signal.SIGINT)(signal.SIGINT, None)
                        signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                    cleanup_finished = True
                    return {"status": "PASS"}

                def publish_diagnostics(*values):
                    if phase == "diagnostics":
                        raise KeyboardInterrupt()
                    return original_diagnostics(*values)

                previous = {number: signal.getsignal(number) for number in (signal.SIGTERM, signal.SIGINT)}
                with patch.object(batch.sys, "platform", "darwin"), \
                     patch.dict(os.environ, {"GITHUB_SHA": "a" * 40, "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}), \
                     patch.object(batch.subprocess, "check_output", return_value=json.dumps(inventory([preflight_device])).encode()), \
                     patch.object(batch, "run_worker_command", side_effect=mock_worker), \
                     patch.object(batch, "cleanup_owned", side_effect=cleanup), patch.object(batch, "write", side_effect=publish), \
                     patch.object(batch, "publish_batch_observations", side_effect=publish_diagnostics):
                    with self.assertRaises(KeyboardInterrupt):
                        batch.run(args, types.SimpleNamespace(plan=selection))
                for number, handler in previous.items():
                    self.assertEqual(signal.getsignal(number), handler)
                if phase.startswith("signals_"):
                    self.assertTrue(cleanup_finished, "A later cancellation signal interrupted owned cleanup")
                self.assertEqual(json.loads((args.evidence / "execution.json").read_text())["status"], "CANCELLED")

    def test_parent_diagnostics_ignore_external_symlink_and_cannot_rewrite_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            result = {"status": "BATCH_ABORTED_SETUP_OR_IDENTITY", "error": "original failure",
                      "source_sha": "a" * 40, "run_id": "123", "run_attempt": "1"}
            worker = {"protocol": batch.PROTOCOL, "profile": batch.PROFILE,
                      "status": "BATCH_ABORTED_SETUP_OR_IDENTITY", "phase": "BUILD",
                      "lane_receipts": {"editor": {"path": "lanes/editor/execution.json", "sha256": "a" * 64}}}
            batch.write(evidence / "batch-worker.json", worker)
            result["retained_worker_receipt"] = {"sha256": batch.digest(evidence / "batch-worker.json")}
            original = copy.deepcopy(result)
            external = root / "external.json"
            external.write_text('{"status":"EXTERNAL_PRIVATE_VALUE"}')
            lane = evidence / "lanes" / "editor"
            lane.mkdir(parents=True)
            (lane / "execution.json").symlink_to(external)
            with patch.object(batch.diagnostics, "emit_execution") as emit:
                batch.publish_batch_observations(evidence, result)
            self.assertEqual(result, original)
            self.assertEqual(json.loads((evidence / "batch-worker.json").read_text()), worker)
            records = [call.args for call in emit.call_args_list]
            self.assertEqual(records, [(original, batch.PROFILE), (worker, batch.PROFILE),
                ({"status": "DIAGNOSTIC_READ_FAILED"}, "editor")])
            self.assertNotIn("EXTERNAL_PRIVATE_VALUE", str(records))

    def test_parent_diagnostics_require_current_worker_reference_hash_and_lane_identity(self):
        for mode in ["unreferenced-old-lane", "foreign-run", "changed-bytes", "current"]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                evidence = Path(temporary)
                result = {"status": "BATCH_ABORTED_SETUP_OR_IDENTITY", "source_sha": "a" * 40,
                          "run_id": "123", "run_attempt": "1"}
                value = {**result, "status": "LANE_PASS_ACCEPTANCE_REVIEW_PENDING", "passed_ui_methods": 3}
                if mode in {"unreferenced-old-lane", "foreign-run"}:
                    value.update(source_sha="b" * 40, run_id="999")
                lane_path = evidence / "lanes/editor/execution.json"
                batch.write(lane_path, value)
                references = {} if mode == "unreferenced-old-lane" else {
                    "editor": {"path": "lanes/editor/execution.json", "sha256": batch.digest(lane_path)}}
                worker = {"protocol": batch.PROTOCOL, "profile": batch.PROFILE,
                          "status": "BATCH_ABORTED_SETUP_OR_IDENTITY", "phase": "BUILD",
                          "lane_receipts": references}
                batch.write(evidence / "batch-worker.json", worker)
                result["retained_worker_receipt"] = {"sha256": batch.digest(evidence / "batch-worker.json")}
                if mode == "changed-bytes":
                    batch.write(lane_path, {**value, "passed_ui_methods": 99})
                with patch.object(batch.diagnostics, "emit_execution") as emit:
                    batch.publish_batch_observations(evidence, result)
                records = [call.args for call in emit.call_args_list]
                self.assertEqual(records[:2], [(result, batch.PROFILE), (worker, batch.PROFILE)])
                if mode == "unreferenced-old-lane":
                    self.assertEqual(len(records), 2)
                elif mode == "current":
                    self.assertEqual(records[2], (value, "editor"))
                else:
                    self.assertEqual(records[2], ({"status": "DIAGNOSTIC_READ_FAILED"}, "editor"))

    def test_old_worker_or_lane_data_is_rejected_before_any_command(self):
        for name in ["execution.json", "batch-intent.json", "batch-worker.json", "lanes", "broken-worker"]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                evidence = Path(temporary)
                if name == "lanes":
                    (evidence / name).mkdir()
                elif name == "broken-worker":
                    (evidence / "batch-worker.json").symlink_to(evidence / "missing")
                else:
                    (evidence / name).write_text("original data")
                args = argparse.Namespace(app=evidence, evidence=evidence, derived=evidence / "derived",
                                          device="ipad", language="en")
                with patch.object(batch.sys, "platform", "darwin"), \
                     patch.object(batch.subprocess, "check_output") as command, \
                     self.assertRaisesRegex(RuntimeError, "stale batch evidence"):
                    batch.run(args, types.SimpleNamespace(plan=selection))
                command.assert_not_called()
                if name not in {"lanes", "broken-worker"}:
                    self.assertEqual((evidence / name).read_text(), "original data")

    def worker_case(self, mode):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        args = argparse.Namespace(app=root, evidence=root / "evidence", derived=root / "build/derived",
                                  deadline=time.monotonic() + batch.WORKER_SECONDS - 1)
        devices = [{**DEVICE, "udid": str(index + 1) * 8 + "-1111-1111-1111-111111111111",
                    "name": "owned-" + name, "lane": name} for index, name in enumerate(batch.LANES)]
        ownership = [{key: value for key, value in device.items() if key != "udid"} for device in devices]
        intent = {"parent_pid": os.getppid(), "lane_devices": ownership, "baseline_udids": []}
        calls = []
        active = []
        context = frozen(root)
        preflight = {"selected": {"ipad": DEVICE}, "status": "PREFLIGHT_PASS_UI_NOT_RUN"}

        class SelectionFailure(ValueError):
            pass

        def execute(local, receipt, *, build_context):
            calls.append(local.lane)
            if mode == "setup" and local.lane == "inspector":
                raise RuntimeError("injected setup failure")
            if mode == "functional" and local.lane == "inspector":
                receipt["phase"] = "UI"
                raise SelectionFailure("injected actual failed-case path")
            if mode == "preservation_budget" and local.lane == "properties":
                # Enough for the old 1380s lane, insufficient for its additional
                # mandatory stopped-store/install phase.
                args.deadline = time.monotonic() + 1500
            receipt.update(status="LANE_PASS_ACCEPTANCE_REVIEW_PENDING", phase="COMPLETE")

        lane = types.SimpleNamespace(plan=selection, shared=Mock(), execute=execute, SelectionFailure=SelectionFailure)

        def check_output(command, **kwargs):
            if command[2:4] == ["list", "devices"]:
                self.assertEqual(kwargs["timeout"], 120)
                self.assertNotEqual(command[4], "--json", "A lane must never fall back to a global inventory")
                selected = active if command[4] == "--json" else [device for device in active
                    if command[4] in (device["udid"], device["name"])]
                return json.dumps(inventory(selected)).encode()
            if command[2] == "create":
                self.assertEqual(kwargs["timeout"], 30)
                device = next(device for device in devices if device["name"] == command[3])
                active.append(device)
                return device["udid"] + "\n"
            raise AssertionError(command)

        def build_once(*values):
            values[-1]["build_receipt_sha256"] = "synthetic-controller-build"
            return context, preflight

        if mode == "budget":
            args.deadline = time.monotonic() + 20
        elif mode == "properties_budget":
            args.deadline = time.monotonic() + 2200
        verification = Mock(side_effect=[None, None, RuntimeError("shared source changed")]) if mode == "drift" else Mock()
        with patch.object(batch, "build_once", side_effect=build_once), \
             patch.object(batch.FrozenBuild, "verify_current", verification), \
             patch.object(batch.subprocess, "check_output", side_effect=check_output), \
             patch.object(batch.subprocess, "run", return_value=types.SimpleNamespace(returncode=0)), \
             patch.object(batch, "validate_lane_pass", return_value={"synthetic_control": True}), \
             patch.object(batch, "qualify_functional_failure", return_value={"original_counts": {"failedTests": 1}}):
            code = batch.worker(args, lane, intent)
        return root, calls, code, json.loads((args.evidence / "batch-worker.json").read_text())

    def test_functional_failure_remains_failed_while_five_fresh_lanes_continue(self):
        root, calls, code, receipt = self.worker_case("functional")
        self.assertEqual(calls, list(batch.LANES))
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "BATCH_FAILED_OBSERVED_TESTS")
        self.assertEqual(receipt["lane_statuses"]["inspector"], "LANE_FAILED_OBSERVED_TEST")
        self.assertEqual(sum(value == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING" for value in receipt["lane_statuses"].values()), 5)
        self.assertEqual(len(receipt["lane_receipts"]), 6)
        owned = [json.loads((root / "evidence/lanes" / name / "owned-simulator.json").read_text())["udid"] for name in batch.LANES]
        self.assertEqual(len(set(owned)), 6)

    def test_setup_failure_aborts_remaining_lanes_without_relabelling_them(self):
        _, calls, code, receipt = self.worker_case("setup")
        self.assertEqual(calls, ["inspector"])
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "BATCH_ABORTED_SETUP_OR_IDENTITY")
        self.assertTrue(all(receipt["lane_statuses"][name] == "NOT_RUN_SETUP" for name in batch.LANES[1:]))

    def test_shared_input_drift_aborts_before_the_next_fresh_lane(self):
        _, calls, code, receipt = self.worker_case("drift")
        self.assertEqual(calls, ["inspector"])
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "BATCH_ABORTED_SETUP_OR_IDENTITY")
        self.assertEqual(receipt["lane_statuses"]["inspector"], "LANE_PASS_ACCEPTANCE_REVIEW_PENDING")
        self.assertTrue(all(receipt["lane_statuses"][name] == "NOT_RUN_SETUP" for name in batch.LANES[1:]))

    def test_insufficient_budget_executes_no_lane_and_records_all_as_not_run(self):
        _, calls, code, receipt = self.worker_case("budget")
        self.assertEqual(calls, [])
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "BATCH_BUDGET_EXHAUSTED")
        self.assertEqual(set(receipt["lane_statuses"].values()), {"NOT_RUN_BUDGET"})

    def test_long_properties_ceiling_preserves_prior_lanes_without_overrunning_worker(self):
        _, calls, code, receipt = self.worker_case("properties_budget")
        self.assertEqual(calls, ["inspector", "inspector-search"])
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "BATCH_BUDGET_EXHAUSTED")
        self.assertTrue(all(receipt["lane_statuses"][name] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING"
                            for name in calls))
        self.assertTrue(all(receipt["lane_statuses"][name] == "NOT_RUN_BUDGET"
                            for name in batch.LANES[2:]))

    def test_properties_install_budget_is_reserved_before_any_lane_mutation(self):
        root, calls, code, receipt = self.worker_case("preservation_budget")
        self.assertEqual(calls, ["inspector", "inspector-search", "properties"])
        self.assertEqual(code, 1)
        self.assertEqual(receipt["status"], "BATCH_BUDGET_EXHAUSTED")
        self.assertTrue(all(receipt["lane_statuses"][name] == "LANE_PASS_ACCEPTANCE_REVIEW_PENDING"
                            for name in calls))
        self.assertTrue(all(receipt["lane_statuses"][name] == "NOT_RUN_BUDGET"
                            for name in batch.LANES[3:]))
        self.assertFalse((root / "evidence/lanes/properties-set/owned-simulator.json").exists())


def process_running(pid):
    value = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return value.returncode == 0 and value.stdout.strip() and not value.stdout.strip().startswith("Z")


@unittest.skipUnless(os.name == "posix", "Owned POSIX process-group controls require POSIX")
class OwnedProcessControls(unittest.TestCase):
    def worker_script(self, root):
        script = root / "controlled-worker.py"
        script.write_text("import os, signal, subprocess, sys, time\n"
            "child=subprocess.Popen([sys.executable,'-c',"
            "'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(60)'])\n"
            "open(sys.argv[1],'w').write(str(child.pid))\n"
            "time.sleep(60)\n")
        return [sys.executable, str(script), str(root / "child.pid")]

    def check_controlled_cleanup(self, interrupt):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unrelated = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"])
            previous = None
            try:
                if interrupt:
                    previous = signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
                    signal.setitimer(signal.ITIMER_REAL, 0.8)
                exception = KeyboardInterrupt if interrupt else subprocess.TimeoutExpired
                with self.assertRaises(exception):
                    batch.run_worker_command(self.worker_script(root), root, root / "worker.log", 0.8 if not interrupt else 15)
                child = int((root / "child.pid").read_text())
                for _ in range(20):
                    if not process_running(child):
                        break
                    time.sleep(0.02)
                self.assertFalse(process_running(child), "TERM-exited parent left its owned TERM-ignoring child alive")
                self.assertIsNone(unrelated.poll(), "Cleanup signalled an unrelated process")
                receipt = json.loads((root / "worker.command.json").read_text())
                self.assertEqual(receipt["status"], "CANCELLED" if interrupt else "TIMED_OUT")
                self.assertTrue((root / "worker.log").exists())
            finally:
                if previous is not None:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, previous)
                unrelated.terminate()
                unrelated.wait(timeout=5)

    def test_timeout_terminates_owned_descendant_after_parent_exits(self):
        self.check_controlled_cleanup(False)

    def test_keyboard_interrupt_preserves_cancel_receipt_and_owned_cleanup(self):
        self.check_controlled_cleanup(True)


if __name__ == "__main__":
    unittest.main()
