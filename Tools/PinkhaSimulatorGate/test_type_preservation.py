"""Controller controls. Synthetic records are never native/Apple acceptance."""
import copy
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import type_preservation as gate

UDID = "11111111-1111-1111-1111-111111111111"
BINDING = gate.binding("a" * 40, "12345", "1", "b" * 32)
CODE_SHA = "c" * 64
TEST_IMAGE = b"synthetic native test executable"
XCODE_MANUAL = b"test-without-building uses -xctestrun for an existing test configuration.\n"
XCTESTRUN_MANUAL = b""".It Sy UseDestinationArtifacts <bool>
When this flag is set, xcodebuild will not install test artifacts to the destination during testing.
TestBundlePath, TestHostPath, and UITargetAppPath should be excluded.
TestHostBundleIdentifier TestBundleDestinationRelativePath UITargetAppBundleIdentifier __TESTHOST__
"""


def native_target():
    return {"BlueprintName": "AnytypeTests", "IsAppHostedTestBundle": True,
            "TestBundlePath": gate.destination_mode.RELATIVE, "TestHostBundleIdentifier": gate.destination_mode.HOST,
            "TestHostPath": "__TESTROOT__/Release-Anytype-iphonesimulator/Anytype.app",
            "TestingEnvironmentVariables": {"XCInjectBundleInto": "__TESTHOST__/Anytype", "XCODE_REQUIRED": "kept"},
            "CommandLineArguments": []}


def synthetic_destination_proof(directory, bound, code_sha=CODE_SHA):
    """Only for synthetic artifact controls; never actual runner evidence."""
    records = {}
    for key, raw in (("xcodebuild", XCODE_MANUAL), ("xctestrun", XCTESTRUN_MANUAL)):
        filename = "type-preservation-" + gate.destination_mode.MANUALS[key][1]
        (directory / filename).write_bytes(raw)
        records[key] = {"sourcePath": "/synthetic/Xcode.app/Contents/Developer/usr/share/man/" + filename, "file": filename,
                        "sha256": gate.sha256(raw), "bytes": len(raw), "compressed": False}
    value = {"schemaVersion": 1, "status": "SUPPORTED_SELECTED_XCODE", "binding": bound,
             "codeCarriersSHA256": code_sha, "xcodebuildPath": "/synthetic/Xcode.app/Contents/Developer/usr/bin/xcodebuild",
             "xcodebuildVersion": "Xcode 27.0\nBuild version 18A1", "manuals": records,
             "testBundle": {"hostBundleIdentifier": gate.destination_mode.HOST, "testBundleIdentifier": "io.anytype.tests",
                 "relativeBundlePath": gate.destination_mode.RELATIVE, "executableRelativePath": gate.destination_mode.EXECUTABLE,
                 "sha256": gate.sha256(TEST_IMAGE), "bytes": len(TEST_IMAGE)}}
    (directory / gate.destination_mode.PROOF).write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))
    return value


def linux_control_identity(path):
    """Use real directory dev/inode; a fixed birthtime substitutes macOS only."""
    info = path.stat()
    return {"path": str(path.resolve()), "device": str(info.st_dev), "inode": str(info.st_ino), "createdAt": 1_700_000_000.0}


def fixture():
    return {"spaceId": "space", "typeSwitch": {"objectId": "subject", "spaceId": "space", "initialTypeId": "chiddush"},
            "documents": {"chiddush": "writing1", "article": "writing2", "research": "writing3"},
            "universalDocuments": {"page": "blank1", "note": "blank2", "custom": "blank3"},
            "universalTypes": {"page": "page"}, "sourceHeaderCases": [{"objectId": "header" + str(x)} for x in range(4)],
            "setId": "set1", "universalSetId": "set2"}


def baseline(directories):
    records = [{"spaceId": "space", "objectId": "subject", "item": {
        "id": "association-" + kind, "kind": kind, "role": "context", "providerID": "sefaria", "canonicalKey": key,
        "externalID": key, "labelHe": key, "createdAt": "2026-11-18T21:00:00.000Z"}}
        for kind, key in (("ref", "Genesis 3:1"), ("topic", "creation"), ("word", "בראשית"))]
    raw = json.dumps({"version": 2, "records": records}, ensure_ascii=False)
    def row(oid, typ, tags, links, backlinks, seeded):
        return {"objectID": oid, "spaceID": "space", "typeID": typ, "tags": tags,
                "links": sorted(links), "backlinks": sorted(backlinks), "seededLinks": seeded}
    objects = [row("subject", "chiddush", ["native-tag"], ["outgoing", "other-retained-link"], ["incoming"],
                   [{"blockID": "out-block", "targetID": "outgoing"}]),
               row("outgoing", "page", [], [], ["subject", "other-retained-backlink"], []),
               row("incoming", "page", [], ["subject"], [], [{"blockID": "in-block", "targetID": "subject"}])]
    return {"schemaVersion": 1, "binding": BINDING, "preparationPID": 101, "state": {
        "accountID": "original-account", "spaceID": "space", "subjectID": "subject", "chiddushTypeID": "chiddush",
        "canonicalPropertyKey": "canonical-key", "canonicalRaw": raw, "canonicalSHA256": gate.sha256(raw.encode()),
        **directories, "objects": objects, "tagOption": {"objectID": "native-tag", "spaceID": "space",
            "name": "Original native Type-preservation Tag", "relationKey": "tag", "color": "red"}}}


def result():
    return {"status": "PASS", "command_exit_code": 0, "passed": 1, "failed": 0, "skipped": 0,
            "selected": [gate.METHOD], "actual_methods": {gate.METHOD + "()": "Passed"},
            "actual_devices": [{"deviceId": UDID, "architecture": "arm64", "osVersion": "27.0"}]}


def installation_proof(original, original_sha, fixture_sha, udid, directories):
    checks = {stage: {"status": "PASS_APP_NOT_RUNNING", "commandExitCode": 0, "ownedAppMatches": 0,
              "unresolvedAppMatches": 0, "controllerPID": 303, "enumeratedProcesses": 4,
              "inventorySHA256": "d" * 64, "executablePathSHA256": "e" * 64} for stage in gate.STOP_STAGES}
    summary = {"sha256": "f" * 64, "files": 2, "bytes": 64, "directories": 1}
    original_dirs = {k: copy.deepcopy(original["state"][k]) for k in ("container", "middleware")}
    return {"schemaVersion": 1, "status": "PASS_STOPPED_NATIVE_STORE_UNCHANGED", "binding": original["binding"],
            "baselineSHA256": original_sha, "fixtureSHA256": fixture_sha, "simulatorUDID": udid,
            **{k: original["state"][k] for k in ("accountID", "spaceID", "subjectID")},
            "preparationPID": original["preparationPID"], "codeCarriersSHA256": CODE_SHA,
            "installedBeforeCodeSHA256": CODE_SHA, "installedAfterCodeSHA256": CODE_SHA,
            "originalDirectories": original_dirs, "currentDirectories": copy.deepcopy(directories),
            "beforeInventory": copy.deepcopy(summary), "afterInventory": copy.deepcopy(summary),
            "stoppedProcessChecks": checks,
            "containerRelocated": original_dirs["container"]["path"] != directories["container"]["path"]}


def installation_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def native_receipt(original, original_sha, installation):
    state = copy.deepcopy(original["state"])
    state.update(copy.deepcopy(installation["currentDirectories"]))
    return {"schemaVersion": 2, "status": "PASS", "scope": "FINAL_UI_TYPE_ROUNDTRIP", "binding": original["binding"],
            "baselineSHA256": original_sha, "preparationPID": original["preparationPID"], "postflightPID": 202,
            "installationSHA256": gate.sha256(installation_bytes(installation)),
            "directoriesBefore": copy.deepcopy(installation["currentDirectories"]),
            "verifierCallsMutationAPI": False, "state": state}


class PreservationControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.container = self.root / UDID / "data"
        self.support = self.container / "Library/Application Support"
        (self.support / "Anytype/middleware-go").mkdir(parents=True)
        self.evidence = self.root / "evidence"; self.evidence.mkdir()
        self.patch = patch.object(gate, "directory_identity", side_effect=linux_control_identity)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.directories = {"container": linux_control_identity(self.container),
                            "middleware": linux_control_identity(self.support / "Anytype/middleware-go")}
        self.original = baseline(self.directories)
        self.raw = json.dumps(self.original, ensure_ascii=False).encode()
        (self.support / gate.BASELINE).write_bytes(self.raw)
        self.fixture_raw = json.dumps(fixture()).encode()
        (self.support / gate.FIXTURE).write_bytes(self.fixture_raw)
        (self.support / "Anytype/middleware-go/native.db").write_bytes(b"original native account bytes")
        self.built = self.root / "built/Anytype.app"; self.built.mkdir(parents=True)
        self.installed = self.root / UDID / "bundle/Anytype.app"; self.installed.mkdir(parents=True)
        (self.built / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "io.anytype.app"}))
        (self.installed / "Info.plist").write_bytes((self.built / "Info.plist").read_bytes())
        for app in (self.built, self.installed):
            bundle = app / gate.destination_mode.BUNDLE; bundle.mkdir(parents=True)
            (bundle / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "io.anytype.tests",
                                                               "CFBundleExecutable": "AnytypeTests"}))
            (app / gate.destination_mode.EXECUTABLE).write_bytes(TEST_IMAGE)
        self.developer = self.root / "Xcode.app/Contents/Developer"
        self.xcodebuild = self.developer / "usr/bin/xcodebuild"
        self.xcodebuild.parent.mkdir(parents=True); self.xcodebuild.write_bytes(b"synthetic Xcode executable")
        for key, raw in (("xcodebuild", XCODE_MANUAL), ("xctestrun", XCTESTRUN_MANUAL)):
            section, name = gate.destination_mode.MANUALS[key]
            path = self.developer / "usr/share/man" / section / name
            path.parent.mkdir(parents=True); path.write_bytes(raw)
        self.capability_calls = []
        self.install_calls = []

    def carriers(self, app):
        raw = (app / gate.destination_mode.EXECUTABLE).read_bytes()
        return {"sha256": CODE_SHA, "manifest": {"carriers": {
            gate.destination_mode.EXECUTABLE: {"sha256": gate.sha256(raw), "bytes": len(raw)}}}}

    def freeze(self):
        return gate.freeze(self.container, self.evidence, BINDING, fixture(), UDID)

    def install(self, frozen, change=None, *, install_error=None, process=None, code=None, capability_error=None):
        if not (self.evidence / gate.INSTALLATION).exists():
            # Each repeated negative is a new synthetic attempt, not a production retry.
            for path in self.evidence.iterdir():
                if path.name == gate.destination_mode.PROOF or path.name.startswith("type-preservation-xcodebuild."):
                    path.unlink()
        current = [self.container]
        def query(udid, kind, *, timeout):
            self.assertEqual(udid, UDID)
            self.assertGreater(timeout, 0); self.assertLessEqual(timeout, gate.QUERY_SECONDS)
            return current[0] if kind == "data" else self.installed
        def command(argv, **kwargs):
            if argv == ["xcrun", "--find", "xcodebuild"]:
                self.capability_calls.append(argv)
                if capability_error and capability_error[0] == 1:
                    raise capability_error[1]
                return SimpleNamespace(returncode=0, stdout=(str(self.xcodebuild) + "\n").encode(), stderr=b"")
            if argv == [str(self.xcodebuild), "-version"]:
                self.capability_calls.append(argv)
                if capability_error and capability_error[0] == 2:
                    raise capability_error[1]
                return SimpleNamespace(returncode=0, stdout=b"Xcode 27.0\nBuild version 18A1\n", stderr=b"")
            if argv[0] == "/bin/ps":
                self.assertEqual(argv, ["/bin/ps", "-ww", "-axo", "pid=,ucomm=,comm="])
                if isinstance(process, BaseException):
                    raise process
                raw = process if process is not None else f"{os.getpid()} Python /usr/bin/python3\n".encode()
                return SimpleNamespace(returncode=0, stdout=raw, stderr=b"")
            self.assertEqual(argv, ["xcrun", "simctl", "install", UDID, str(self.built)])
            self.assertEqual(kwargs["timeout"], 120)
            self.install_calls.append(argv)
            if install_error is not None:
                raise install_error
            if change:
                replacement = change(current[0])
                if replacement is not None:
                    current[0] = replacement
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        with patch.object(gate, "app_container", side_effect=query), patch.object(gate.subprocess, "run", side_effect=command):
            return gate.install_for_postflight(frozen, self.built, CODE_SHA, self.evidence,
                                               code or self.carriers)

    def test_real_original_bytes_are_frozen_outside_mutable_container(self):
        frozen = self.freeze()
        installation = self.install(frozen)
        self.assertEqual(frozen.path.read_bytes(), self.raw)
        self.assertFalse(frozen.path.is_relative_to(self.container))
        # Changing the mutable handoff must never redefine postflight expectations.
        env = gate.environment(frozen, installation)
        self.assertEqual(gate.base64.b64decode(env["PINKHA_TYPE_PRESERVATION_BASELINE_BASE64"]), self.raw)
        self.assertEqual(env["PINKHA_TYPE_PRESERVATION_BASELINE_SHA256"], gate.sha256(self.raw))
        self.assertEqual(gate.base64.b64decode(env["PINKHA_TYPE_PRESERVATION_INSTALLATION_BASE64"]),
                         installation.path.read_bytes())
        (self.support / gate.BASELINE).write_bytes(b'{"foreign":true}')
        with self.assertRaisesRegex(ValueError, "baseline/fixture changed"):
            gate.environment(frozen, installation)
        self.assertEqual(frozen.path.read_bytes(), self.raw)

    def test_mutated_external_baseline_or_recreated_store_fails(self):
        frozen = self.freeze()
        installation = self.install(frozen)
        frozen.path.write_bytes(self.raw + b" ")
        with self.assertRaisesRegex(ValueError, "baseline bytes changed"):
            gate.environment(frozen, installation)
        frozen.path.write_bytes(self.raw)
        middleware = self.support / "Anytype/middleware-go"
        middleware.rename(middleware.with_name("old-owned-control-store"))
        middleware.mkdir()
        with self.assertRaisesRegex(ValueError, "recreated or replaced"):
            gate.verify_frozen(frozen)

    def test_full_native_sets_and_original_canonical_bytes_are_required(self):
        frozen = self.freeze()
        installation = self.install(frozen)
        receipt = native_receipt(frozen.value, frozen.sha256, installation.value)
        self.assertEqual(gate.validate_result(frozen, installation, receipt, result())["native_postflight_methods"], 1)
        changes = [
            lambda x: x["state"].update(accountID="other-account"),
            lambda x: x["state"].update(canonicalRaw=x["state"]["canonicalRaw"] + " "),
            lambda x: x["state"].update(canonicalSHA256="c" * 64),
            lambda x: x["state"]["objects"][0].update(tags=[]),
            lambda x: x["state"]["objects"][0].update(links=["outgoing"]),
            lambda x: x["state"]["objects"][1].update(backlinks=["subject"]),
            lambda x: x["state"]["objects"][0]["seededLinks"][0].update(blockID="recreated-block"),
            lambda x: x["state"]["objects"][2]["seededLinks"][0].update(targetID="foreign"),
            lambda x: x["state"]["middleware"].update(inode="99999"),
            lambda x: x["state"]["container"].update(createdAt=1_700_000_001.0),
            lambda x: x.update(postflightPID=101),
            lambda x: x.update(baselineSHA256="d" * 64),
            lambda x: x["binding"].update(nonce="e" * 32),
            lambda x: x.update(verifierCallsMutationAPI=True),
        ]
        for change in changes:
            bad = copy.deepcopy(receipt); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_result(frozen, installation, bad, result())

    def test_stale_foreign_or_unproved_baseline_is_rejected_before_ui(self):
        changes = [
            lambda x: x["binding"].update(runID="99999"),
            lambda x: x["state"].update(subjectID="another-object"),
            lambda x: x["state"].update(accountID=""),
            lambda x: x["state"]["objects"][1].update(objectID="blank1"),
            lambda x: x["state"]["objects"][0].update(links=[]),
            lambda x: x["state"]["objects"][1].update(backlinks=[]),
            lambda x: x["state"]["objects"][0].update(tags=[]),
            lambda x: x["state"]["tagOption"].update(relationKey="other-property"),
            lambda x: x["state"]["objects"][2]["seededLinks"][0].update(targetID="other"),
            lambda x: x["state"]["middleware"].update(path="/other-store"),
        ]
        for change in changes:
            bad = copy.deepcopy(self.original); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_baseline(bad, BINDING, fixture(), self.directories)

    def test_canonical_raw_v1_missing_identity_or_timestamps_cannot_be_lifted(self):
        changes = [lambda x: x.update(version=1),
                   lambda x: x["records"][0]["item"].pop("createdAt"),
                   lambda x: x["records"][0]["item"].update(createdAt="invalidZ"),
                   lambda x: x["records"][0]["item"].update(id=""),
                   lambda x: x["records"][0].update(blockId="unapproved-block-scope"),
                   lambda x: x["records"][0].update(spaceId="foreign-space")]
        for change in changes:
            bad = copy.deepcopy(self.original); canonical = json.loads(bad["state"]["canonicalRaw"]); change(canonical)
            raw = json.dumps(canonical); bad["state"].update(canonicalRaw=raw, canonicalSHA256=gate.sha256(raw.encode()))
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_baseline(bad, BINDING, fixture(), self.directories)

    def test_native_missing_skipped_extra_or_foreign_results_fail(self):
        frozen = self.freeze(); installation = self.install(frozen)
        receipt = native_receipt(frozen.value, frozen.sha256, installation.value)
        changes = [lambda x: x.update(status="NOT_RUN"), lambda x: x.update(command_exit_code=1),
                   lambda x: x.update(passed=True), lambda x: x.update(skipped=1),
                   lambda x: x.update(actual_methods={gate.METHOD: "Skipped"}),
                   lambda x: x["actual_methods"].update({"Preparation/createWallet": "Passed"}),
                   lambda x: x["actual_methods"].update({gate.METHOD: "Passed"}),
                   lambda x: x["actual_devices"][0].update(deviceId="foreign"),
                   lambda x: x["actual_devices"][0].update(osVersion="26.0")]
        for change in changes:
            bad = copy.deepcopy(result()); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_result(frozen, installation, receipt, bad)

    def test_postflight_copy_clears_preparation_and_stays_beside_products(self):
        frozen = self.freeze(); installation = self.install(frozen); env = gate.environment(frozen, installation)
        products = self.root / "Products"; products.mkdir()
        original = products / "native.xctestrun"
        target = {**native_target(),
                  "OnlyTestIdentifiers": ["TorahNativeDerivedProductIntegrationTests"],
                  "SkipTestIdentifiers": [gate.METHOD], "EnvironmentVariables": {
                      "PINKHA_NATIVE_DERIVED_ACCEPTANCE": "1", "PINKHA_UNEXPECTED_PREP": "1", "XCODE_REQUIRED": "kept"}}
        raw = plistlib.dumps({"TestConfigurations": [{"TestTargets": [target]}]}); original.write_bytes(raw)
        with patch.dict(os.environ, {"PINKHA_T5_APPLE_PAIR": "1", "SIMCTL_CHILD_PINKHA_OTHER": "1"}):
            selected = gate.selected_configuration(original, env)
        self.assertEqual(selected.parent, products); self.assertEqual(original.read_bytes(), raw)
        observed = plistlib.loads(selected.read_bytes())["TestConfigurations"][0]["TestTargets"][0]
        self.assertEqual(observed["OnlyTestIdentifiers"], [gate.METHOD]); self.assertEqual(observed["SkipTestIdentifiers"], [])
        self.assertTrue(observed["UseDestinationArtifacts"])
        self.assertEqual(observed["TestHostBundleIdentifier"], gate.destination_mode.HOST)
        self.assertEqual(observed["UITargetAppBundleIdentifier"], gate.destination_mode.HOST)
        self.assertEqual(observed["TestBundleDestinationRelativePath"], gate.destination_mode.RELATIVE)
        self.assertFalse(any(k in observed for k in ("TestHostPath", "TestBundlePath", "UITargetAppPath")))
        self.assertEqual(observed["TestingEnvironmentVariables"], target["TestingEnvironmentVariables"])
        self.assertEqual(observed["EnvironmentVariables"]["PINKHA_UNEXPECTED_PREP"], "0")
        self.assertEqual(observed["EnvironmentVariables"]["SIMCTL_CHILD_PINKHA_OTHER"], "0")
        self.assertEqual(observed["EnvironmentVariables"]["XCODE_REQUIRED"], "kept")
        self.assertTrue(all(observed["EnvironmentVariables"][k] == "0" for k in gate.DISABLED_FLAGS))

    def test_inherited_launch_injection_or_enabled_preparation_is_rejected(self):
        frozen = self.freeze(); installation = self.install(frozen); env = gate.environment(frozen, installation)
        with self.assertRaisesRegex(ValueError, "injection argument"):
            gate.configure_target({**native_target(), "CommandLineArguments": ["PINKHA_NATIVE_DERIVED_ACCEPTANCE=1"]}, env)
        env["PINKHA_NATIVE_DERIVED_ACCEPTANCE"] = "1"
        with self.assertRaisesRegex(ValueError, "not disabled"):
            gate.configure_target({}, env)

    def test_failed_missing_or_extra_ui_prevents_postflight_admission(self):
        methods = ["PinkhaNativeDerivedAcceptanceUITests/testRemainingNativeSourceFilterEditing",
                   "PinkhaNativeDerivedAcceptanceUITests/testRemainingUniversalTypePickersAndMixedSet"]
        passing = {"status": "PASS", "command_exit_code": 0, "passed": 2, "failed": 0, "skipped": 0,
                   "actual_methods": {x: "Passed" for x in methods}}
        gate.require_ui_passed(passing, methods)
        for change in (lambda x: x.update(status="FAIL"), lambda x: x.update(passed=1),
                       lambda x: x.update(skipped=1), lambda x: x.update(command_exit_code=65),
                       lambda x: x["actual_methods"].update({methods[0]: "Failed"}),
                       lambda x: x["actual_methods"].update({"Unexpected/test": "Passed"})):
            bad = copy.deepcopy(passing); change(bad)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "before native postflight"):
                gate.require_ui_passed(bad, methods)

    def test_saved_qualification_requires_original_receipt_and_binding(self):
        frozen = self.freeze(); installation = self.install(frozen)
        receipt = native_receipt(frozen.value, frozen.sha256, installation.value)
        (self.evidence / "postflight").mkdir()
        (self.evidence / "postflight/selection-inputs.json").write_text(json.dumps({"environment": gate.environment(frozen, installation)}))
        raw = json.dumps(receipt).encode(); (self.evidence / "postflight/native-result.json").write_bytes(raw)
        (self.evidence / "fixture-ids.json").write_text(json.dumps(fixture()))
        (self.evidence / "built-code-carriers.json").write_text(json.dumps({"sha256": CODE_SHA}))
        (self.evidence / "type-preservation-inputs.json").write_text(json.dumps({
            "binding": BINDING, "baseline_sha256": frozen.sha256, "fixture_sha256": frozen.fixture_sha256,
            "directories": self.directories,
            "container": str(self.container), "simulator_udid": UDID, "source": "FROZEN_BEFORE_UI"}))
        execution = {"source_sha": BINDING["sourceSHA"], "run_id": BINDING["runID"], "run_attempt": BINDING["runAttempt"],
                     "postflight_binding": BINDING, "preservation_baseline_sha256": frozen.sha256,
                     "preservation_fixture_sha256": frozen.fixture_sha256,
                     "preservation_installation_sha256": installation.sha256,
                     "preservation_native_receipt_sha256": gate.sha256(raw), "postflight": result(),
                     "type_preservation": gate.validate_result(frozen, installation, receipt, result())}
        self.assertEqual(gate.validate_saved(self.evidence, execution, UDID)["status"], "PASS")
        execution["run_id"] = "99999"
        with self.assertRaisesRegex(ValueError, "execution binding"):
            gate.validate_saved(self.evidence, execution, UDID)
        execution["run_id"] = BINDING["runID"]
        (self.evidence / "postflight/native-result.json").write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "bytes changed"):
            gate.validate_saved(self.evidence, execution, UDID)

    def test_same_build_install_can_move_original_store_without_redefining_baseline(self):
        frozen = self.freeze()
        target = self.root / UDID / "relocated-data"
        def move(current):
            current.rename(target)
            return target
        installation = self.install(frozen, move)
        self.assertEqual(len(self.install_calls), 1)
        self.assertFalse(self.container.exists())
        self.assertEqual(installation.container, target)
        self.assertTrue(installation.value["containerRelocated"])
        self.assertEqual(installation.value["beforeInventory"], installation.value["afterInventory"])
        self.assertEqual(frozen.path.read_bytes(), self.raw)
        self.assertEqual(frozen.value["state"]["container"]["path"], str(self.container))
        observed = native_receipt(frozen.value, frozen.sha256, installation.value)
        qualified = gate.validate_result(frozen, installation, observed, result())
        self.assertTrue(qualified["canonical_byte_preservation"])
        self.assertTrue(qualified["stopped_native_install_continuity"])
        self.assertEqual(observed["state"]["canonicalRaw"], frozen.value["state"]["canonicalRaw"])
        self.assertEqual(observed["state"]["container"]["path"], str(target))
        self.assertEqual(gate.base64.b64decode(gate.environment(frozen, installation)[
            "PINKHA_TYPE_PRESERVATION_BASELINE_BASE64"]), self.raw)

    def test_same_build_install_accepts_only_identical_copy_of_native_files(self):
        frozen = self.freeze()
        target = self.root / UDID / "copied-data"
        def copy_store(current):
            shutil.copytree(current, target)
            return target
        installation = self.install(frozen, copy_store)
        self.assertNotEqual(installation.value["originalDirectories"]["middleware"]["inode"],
                            installation.value["currentDirectories"]["middleware"]["inode"])
        self.assertEqual(installation.value["beforeInventory"], installation.value["afterInventory"])

    def test_changed_deleted_or_extra_native_files_fail_the_install_transition(self):
        for mode in ("changed", "deleted", "extra", "directory"):
            with self.subTest(mode=mode):
                frozen = self.freeze() if mode == "changed" else self.frozen_for_additional_control()
                native = self.support / "Anytype/middleware-go/native.db"
                def change(_):
                    if mode == "changed": native.write_bytes(b"foreign account bytes")
                    elif mode == "deleted": native.unlink()
                    elif mode == "extra": (native.parent / "extra.db").write_bytes(b"unexpected")
                    else: (native.parent / "extra-dir").mkdir()
                with self.assertRaisesRegex(ValueError, "changed or removed|store is empty"):
                    self.install(frozen, change)
                self.assertFalse((self.evidence / gate.INSTALLATION).exists())
                self.assertEqual(frozen.path.read_bytes(), self.raw)
                # Restore only this disposable synthetic control's files.
                for path in native.parent.iterdir():
                    if path.is_dir(): path.rmdir()
                    else: path.unlink()
                native.write_bytes(b"original native account bytes")

    def frozen_for_additional_control(self):
        return gate.FrozenBaseline(self.evidence / "type-preservation-baseline.json", gate.sha256(self.raw),
            copy.deepcopy(self.original), self.directories, self.container, UDID,
            self.evidence / "type-preservation-fixture.json", gate.sha256(self.fixture_raw))

    def test_original_fixture_or_baseline_mutation_during_install_is_rejected(self):
        frozen = self.freeze()
        for name in (gate.BASELINE, gate.FIXTURE):
            original = (self.support / name).read_bytes()
            with self.subTest(name=name):
                def change(_): (self.support / name).write_bytes(original + b" ")
                with self.assertRaisesRegex(ValueError, "baseline/fixture changed"):
                    self.install(frozen, change)
                self.assertFalse((self.evidence / gate.INSTALLATION).exists())
                (self.support / name).write_bytes(original)

    def test_native_store_file_or_directory_symlink_is_rejected(self):
        frozen = self.freeze()
        native = self.support / "Anytype/middleware-go"
        outside = self.root / "outside"; outside.write_bytes(b"private bytes")
        link = native / "external.db"
        link.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Unexpected native store file"):
            self.install(frozen)
        self.assertEqual(self.install_calls, [])
        link.unlink()
        directory = native / "external-dir"; directory.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Unexpected native store directory"):
            self.install(frozen)
        self.assertEqual(self.install_calls, [])

    def test_owned_running_or_unresolved_app_prevents_any_install(self):
        frozen = self.freeze()
        for name, command in (("Anytype", str(self.installed / "Anytype")), ("Anytype", "Anytype"),
                              ("Anytype", "(Anytype)"), ("renamed", str(self.installed / "Anytype"))):
            raw = f"{os.getpid()} Python /usr/bin/python3\n777 {name} {command}\n".encode()
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, "still running|unresolved"):
                self.install(frozen, process=raw)
            self.assertEqual(self.install_calls, [])
            self.assertFalse((self.evidence / gate.INSTALLATION).exists())

    def test_unowned_full_path_app_does_not_get_terminated_or_reused(self):
        frozen = self.freeze()
        raw = (f"{os.getpid()} Python /usr/bin/python3\n"
               "777 Anytype /devices/22222222-2222-2222-2222-222222222222/bundle/Anytype.app/Anytype\n").encode()
        installation = self.install(frozen, process=raw)
        self.assertEqual(len(self.install_calls), 1)
        self.assertEqual(installation.value["simulatorUDID"], UDID)

    def test_empty_or_incomplete_process_observation_cannot_prove_exit(self):
        frozen = self.freeze()
        for raw in (b"", b"777 Anytype\n", b"999 Python /usr/bin/python3\n"):
            with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "observation"):
                self.install(frozen, process=raw)
            self.assertEqual(self.install_calls, [])

    def test_install_timeout_and_cancellation_are_single_call_failures_with_private_output_withheld(self):
        frozen = self.freeze()
        for error in (subprocess.TimeoutExpired(["private-command"], 120, output=b"private-output"),
                      KeyboardInterrupt("private-cancel-message")):
            self.install_calls.clear()
            with self.subTest(error=type(error).__name__), self.assertRaises(type(error)):
                self.install(frozen, install_error=error)
            self.assertEqual(len(self.install_calls), 1)
            self.assertFalse((self.evidence / gate.INSTALLATION).exists())
            observed = (self.evidence / "type-preservation-install-observation.json").read_text()
            self.assertNotIn("private-", observed)
            value = json.loads(observed)
            self.assertEqual(value["status"], "FAIL")
            self.assertEqual(value["phase"], "INSTALL")
            self.assertEqual(value["timeoutSeconds"], 120)
            self.assertGreaterEqual(value["elapsedSeconds"], 0)

    def test_process_timeout_cannot_fall_back_to_app_exit_assumption(self):
        frozen = self.freeze()
        with self.assertRaises(subprocess.TimeoutExpired):
            self.install(frozen, process=subprocess.TimeoutExpired(["ps"], 30, output=b"private-process"))
        self.assertEqual(self.install_calls, [])
        self.assertNotIn("private-process", (self.evidence / "type-preservation-install-observation.json").read_text())

    def test_changed_installed_executable_bytes_fail_even_if_native_files_match(self):
        frozen = self.freeze()
        calls = []
        def carriers(path):
            calls.append(path)
            return {**self.carriers(path), "sha256": "d" * 64 if len(calls) == 3 else CODE_SHA}
        with self.assertRaisesRegex(ValueError, "changed executable bytes"):
            self.install(frozen, code=carriers)
        self.assertEqual(len(self.install_calls), 1)
        self.assertFalse((self.evidence / gate.INSTALLATION).exists())

    def test_any_additional_unproved_relocation_or_recreation_is_rejected(self):
        frozen = self.freeze(); installation = self.install(frozen)
        target = self.root / UDID / "unproved-copy"
        shutil.copytree(self.container, target)
        with self.assertRaisesRegex(ValueError, "Additional unproved"):
            gate.verify_installed(frozen, installation, target)
        middleware = self.support / "Anytype/middleware-go"
        middleware.rename(middleware.with_name("old-owned-control-store")); middleware.mkdir()
        with self.assertRaisesRegex(ValueError, "recreated or replaced"):
            gate.verify_installed(frozen, installation, self.container)

    def test_stale_or_missing_installation_is_not_admitted(self):
        frozen = self.freeze()
        with self.assertRaisesRegex(ValueError, "proved controlled install"):
            gate.environment(frozen, None)
        installation = self.install(frozen)
        with self.assertRaisesRegex(ValueError, "stale controlled-install"):
            self.install(frozen)
        self.assertEqual(len(self.install_calls), 1)
        installation.path.write_bytes(installation.path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "receipt changed"):
            gate.environment(frozen, installation)

    def test_wrong_account_fixture_source_process_inventory_or_code_proof_is_rejected(self):
        frozen = self.freeze(); installation = self.install(frozen)
        changes = [
            lambda x: x.update(accountID="foreign"), lambda x: x.update(spaceID="foreign"),
            lambda x: x.update(subjectID="foreign"), lambda x: x.update(baselineSHA256="a" * 64),
            lambda x: x.update(fixtureSHA256="a" * 64), lambda x: x.update(simulatorUDID="foreign"),
            lambda x: x["binding"].update(nonce="a" * 32), lambda x: x.update(codeCarriersSHA256="a" * 64),
            lambda x: x.update(installedAfterCodeSHA256="a" * 64), lambda x: x.update(containerRelocated=True),
            lambda x: x["afterInventory"].update(files=99),
            lambda x: x["afterInventory"].update(sha256="a" * 64),
            lambda x: x["originalDirectories"]["container"].update(inode="999"),
            lambda x: x["currentDirectories"]["middleware"].update(path="/unowned"),
            lambda x: x["stoppedProcessChecks"].pop("BEFORE_INSTALL"),
            lambda x: x["stoppedProcessChecks"]["AFTER_INSTALL"].update(ownedAppMatches=1),
            lambda x: x["stoppedProcessChecks"]["AFTER_INSTALL"].update(commandExitCode=True),
        ]
        for change in changes:
            bad = copy.deepcopy(installation.value); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_installation(bad, frozen.value, frozen.sha256, frozen.fixture_sha256,
                                           UDID, frozen.directories, CODE_SHA)

    def test_native_receipt_cannot_use_legacy_or_another_installation(self):
        frozen = self.freeze(); installation = self.install(frozen)
        receipt = native_receipt(frozen.value, frozen.sha256, installation.value)
        for change in (lambda x: x.update(schemaVersion=1), lambda x: x.update(installationSHA256="a" * 64),
                       lambda x: x.pop("directoriesBefore"),
                       lambda x: x["directoriesBefore"]["container"].update(inode="123"),
                       lambda x: x["state"].update(canonicalRaw=x["state"]["canonicalRaw"] + " ")):
            bad = copy.deepcopy(receipt); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.validate_result(frozen, installation, bad, result())

    def test_directory_birthtime_is_exact_within_each_observer(self):
        frozen = self.freeze(); installation = self.install(frozen)
        receipt = native_receipt(frozen.value, frozen.sha256, installation.value)
        # A cross-library fractional representation difference is not a tolerance.
        for key in ("container", "middleware"):
            receipt["directoriesBefore"][key]["createdAt"] += 0.000001
            receipt["state"][key]["createdAt"] = receipt["directoriesBefore"][key]["createdAt"]
        self.assertEqual(gate.validate_result(frozen, installation, receipt, result())["status"], "PASS")
        receipt["state"]["middleware"]["createdAt"] += 0.000001
        with self.assertRaisesRegex(ValueError, "state differs"):
            gate.validate_result(frozen, installation, receipt, result())
        changed = copy.deepcopy(installation.value["currentDirectories"]["container"]); changed["createdAt"] += 1
        with patch.object(gate, "directory_identity", return_value=changed), self.assertRaisesRegex(ValueError, "recreated"):
            gate.verify_installed(frozen, installation)

    def test_unreadable_real_child_cannot_be_omitted_from_either_inventory(self):
        frozen = self.freeze()
        hidden = self.support / "Anytype/middleware-go/unreadable"; hidden.mkdir()
        original = hidden / "native.db"; original.write_bytes(b"original hidden account bytes")
        scan = gate.os.scandir
        def unreadable(path):
            if Path(path) == hidden:
                raise PermissionError("private-unreadable-path")
            return scan(path)
        with patch.object(gate.os, "scandir", side_effect=unreadable):
            for content in (b"original hidden account bytes", b"changed hidden account bytes"):
                original.write_bytes(content)
                with self.subTest(content=content), self.assertRaisesRegex(ValueError, "enumerate every"):
                    self.install(frozen)
                self.assertEqual(self.install_calls, [])
                self.assertFalse((self.evidence / gate.INSTALLATION).exists())
                self.assertNotIn("private-unreadable-path",
                                 (self.evidence / "type-preservation-install-observation.json").read_text())

    def test_install_phase_deadline_does_not_reset_after_install(self):
        frozen = self.freeze(); clock = [100.0]
        def elapsed(_):
            clock[0] += gate.INSTALLATION_SECONDS + 1
        with patch.object(gate.time, "monotonic", side_effect=lambda: clock[0]):
            with self.assertRaisesRegex(ValueError, "phase budget exhausted"):
                self.install(frozen, elapsed)
        self.assertEqual(len(self.install_calls), 1)
        self.assertFalse((self.evidence / gate.INSTALLATION).exists())
        observed = json.loads((self.evidence / "type-preservation-install-observation.json").read_text())
        self.assertEqual(observed["phaseBudgetSeconds"], 660)
        self.assertEqual(observed["elapsedSeconds"], 661)
        self.assertEqual(observed["status"], "FAIL")
        with patch.object(gate.time, "monotonic", return_value=100):
            self.assertEqual(gate.remaining(110, 120), 10)
            with self.assertRaisesRegex(ValueError, "phase budget exhausted"):
                gate.remaining(100, 120)


if __name__ == "__main__":
    unittest.main()
