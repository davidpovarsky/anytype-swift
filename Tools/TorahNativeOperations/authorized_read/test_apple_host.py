#!/usr/bin/env python3
"""Admission controls for only the new fixed25 actual Heart iOS host."""
import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import shutil
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_apple_host as host


class HeartIOSHostControls(unittest.TestCase):
    UDID = "11111111-2222-3333-4444-555555555555"

    def testReviewedSourceDeclaresExactly25NewMethods(self):
        actual = host.source_selection(host.ROOT)
        self.assertEqual(len(host.expected_methods()), 25)
        self.assertEqual(len(actual), 6)

    def testMissingOrAdditionalSourceMethodCannotChangeSelection(self):
        with tempfile.TemporaryDirectory() as directory:
            control = Path(directory)
            for name in [*host.SOURCES.values(), host.GENERATED_FIXTURE]:
                target = control/name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(host.ROOT/name, target)
            suite = "HeartAuthorizedOperationLibTests"
            path = control/host.SOURCES[suite]; original = path.read_text(encoding="utf8")
            for changed in [original.replace("func testActualLibRead", "func disabledActualLibRead"),
                            original+"\n    func testUnreviewedExtra() {}\n"]:
                path.write_text(changed, encoding="utf8")
                with self.assertRaisesRegex(ValueError, "declaration"):
                    host.source_selection(control)

    def testExactActual25PassesOnOwnedSimulatorAreAccepted(self):
        summary, tree = self.execution()
        result = host.validate_execution(summary, tree, self.UDID)
        self.assertEqual(set(result["methods"]), host.expected_methods())

    def testMissingSkippedFailedOrExtraActualCaseIsRejected(self):
        summary, tree = self.execution()
        alterations = []
        missing = copy.deepcopy(tree); missing["testNodes"].pop(); alterations.append(missing)
        extra = copy.deepcopy(tree)
        extra["testNodes"].append({"nodeType": "Test Case", "nodeIdentifier": "Other/testUnreviewed()", "result": "Passed"})
        alterations.append(extra)
        for result in ["Skipped", "Failed", None]:
            changed = copy.deepcopy(tree); changed["testNodes"][0]["result"] = result; alterations.append(changed)
        for changed in alterations:
            with self.assertRaisesRegex(ValueError, "test node"):
                host.validate_execution(summary, changed, self.UDID)

    def testSummaryCannotHideWrongMethodOrDuplicateActualNode(self):
        summary, tree = self.execution()
        changed = copy.deepcopy(tree); changed["testNodes"][0]["nodeIdentifier"] = "Other/testUnreviewed()"
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            host.validate_execution(summary, changed, self.UDID)
        changed = copy.deepcopy(tree); changed["testNodes"][0] = copy.deepcopy(changed["testNodes"][1])
        with self.assertRaisesRegex(RuntimeError, "duplicate"):
            host.validate_execution(summary, changed, self.UDID)

    def testWrongDestinationOrNonintegerCountsCannotQualify(self):
        summary, tree = self.execution()
        for key, value in [("deviceId", "unowned"), ("osVersion", "26.2"),
                           ("architecture", "x86_64"), ("osBuildNumber", "")]:
            changed = copy.deepcopy(summary); changed["devicesAndConfigurations"][0]["device"][key] = value
            with self.assertRaisesRegex(ValueError, "destination"):
                host.validate_execution(changed, tree, self.UDID)
        for key, value in [("totalTestCount", "25"), ("skippedTests", False), ("passedTests", 24), ("failedTests", 1)]:
            changed = copy.deepcopy(summary); changed[key] = value
            with self.assertRaisesRegex(ValueError, "actual passing"):
                host.validate_execution(changed, tree, self.UDID)

    def testNativeJourneyRequiresOwnedRuntimeSourceNonceAndTypedFacts(self):
        config, value = self.journey()
        host.validate_native_result(value, config)
        for key, item in [("native_version", "r15-attachment-v1"), ("nonce", "stale"),
                          ("app_sha", "0"*40), ("run_id", "wrong-run"), ("actual_append_calls", True),
                          ("publication_denied_at_retirement", False), ("fresh_ios_process_reopen", "PASS")]:
            changed = dict(value, **{key: item})
            with self.assertRaisesRegex(ValueError, "native iOS journey"):
                host.validate_native_result(changed, config)

    def testNativeJourneyRejectsMissingPIDMalformedHashesOrExtraPayload(self):
        config, value = self.journey()
        for key, item in [("pid", 0), ("pid", True), ("account_id_sha256", None), ("canonical_sha256", "raw-content")]:
            with self.assertRaises(ValueError): host.validate_native_result(dict(value, **{key: item}), config)
        changed = dict(value); del changed["space_id_sha256"]
        with self.assertRaises(ValueError): host.validate_native_result(changed, config)
        with self.assertRaises(ValueError): host.validate_native_result(dict(value, account_key="forbidden-extra"), config)

    def testRuntimeAdmissionRequiresSuccessfulControlledProducer(self):
        receipt, run, qualified = self.runtime()
        host.validate_runtime(receipt, run, qualified)
        for key, value in [("conclusion", "failure"), ("head_branch", "main"), ("run_attempt", 2),
                           ("head_sha", "b"*40), ("event", "pull_request"), ("display_title", "Pinkha heart-runtime")]:
            with self.assertRaisesRegex(ValueError, "successful controlled"):
                host.validate_runtime(receipt, dict(run, **{key: value}), qualified)

    def testRuntimeSourceOrGeneratedModuleDriftCannotReuseNativeProof(self):
        receipt, run, qualified = self.runtime()
        for key in ["generated_sha256", "native_source_sha256", "module_sha256"]:
            changed = copy.deepcopy(receipt); changed[key][next(iter(changed[key]))] = "0"*64
            with self.assertRaisesRegex(ValueError, "native input changed"):
                host.validate_runtime(changed, run, qualified)
        with self.assertRaisesRegex(ValueError, "candidate build receipt"):
            host.validate_runtime(dict(receipt, candidate_sha256="0"*64), run, qualified)

    def testUnpackedFrameworkMustMatchFullInventoryAndSliceHash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, files = self.framework()
            archive = self.archive(root, files, receipt)
            observed, framework = host.unpack_runtime(archive, root/"valid")
            self.assertEqual(observed["framework_files_sha256"], receipt["framework_files_sha256"])
            self.assertTrue((framework/"Info.plist").is_file())
            changed = copy.deepcopy(receipt); changed["framework_files_sha256"]["Info.plist"] = "0"*64
            with self.assertRaisesRegex(ValueError, "archive changed"):
                host.unpack_runtime(self.archive(root, files, changed), root/"bad-inventory")
            changed = copy.deepcopy(receipt); changed["binary_slices"][0]["sha256"] = "0"*64
            with self.assertRaisesRegex(ValueError, "slice receipt"):
                host.unpack_runtime(self.archive(root, files, changed), root/"bad-slice")

    def testArchiveCannotExtractTraversalLinkOrUnexpectedFile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (name, kind) in enumerate([("../escape", tarfile.REGTYPE),
                ("/absolute", tarfile.REGTYPE), ("Lib.xcframework/link", tarfile.SYMTYPE),
                ("Lib.xcframework/hardlink", tarfile.LNKTYPE), ("Unexpected.txt", tarfile.REGTYPE)]):
                archive = root/(str(index)+".tar.gz")
                with tarfile.open(archive, "w:gz") as output:
                    member = tarfile.TarInfo(name); member.type = kind; member.linkname = "../escape"
                    output.addfile(member, io.BytesIO())
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    host.unpack_runtime(archive, root/("unpack-"+str(index)))
            self.assertFalse((root/"escape").exists())

    def testResolutionRequiresExactReviewedDependencyRevisions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root/"Package.resolved"
            pins = [{"identity": name, "state": {"revision": revision}} for name, revision in host.PINS.items()]
            path.write_text(json.dumps({"version": 3, "pins": pins}))
            self.assertEqual(len(host.validate_pins(root)), 1)
            pins[0]["state"]["revision"] = "0"*40
            path.write_text(json.dumps({"version": 3, "pins": pins}))
            with self.assertRaisesRegex(ValueError, "dependency revisions"):
                host.validate_pins(root)

    def testCommandJSONRetainsDiagnosticsButRejectsAmbiguousDocuments(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"command.log"
            path.write_text('Xcode diagnostic\n{\n  "a": {"b": 2}\n}\nAnother diagnostic\n')
            self.assertEqual(host.command_json(path), {"a": {"b": 2}})
            path.write_text('{}\n{}\n')
            with self.assertRaisesRegex(ValueError, "Ambiguous"):
                host.command_json(path)

    def execution(self):
        summary = {"totalTestCount": 25, "passedTests": 25, "failedTests": 0, "skippedTests": 0,
                   "devicesAndConfigurations": [{"device": {"deviceId": self.UDID, "osVersion": "27.0",
                      "osBuildNumber": "fixture-build", "architecture": "arm64"}}]}
        tree = {"testNodes": [{"nodeType": "Test Case", "nodeIdentifier": host.TARGET+"/"+method+"()", "result": "Passed"}
                              for method in sorted(host.expected_methods())]}
        return summary, tree

    @staticmethod
    def journey():
        config = {"runID": "fixture-run", "appSHA": "a"*40, "nonce": "fixture-nonce"}
        value = {"status": "PASS_ACTUAL_HEART_LIB_SHARED_READ", "run_id": config["runID"],
                 "app_sha": config["appSHA"], "nonce": config["nonce"], "candidate_sha256": host.native.CANDIDATE,
                 "native_version": host.native.VERSION, "actual_append_calls": 1, "signed_native_provenance": True,
                 "verified_local_absence": True, "block_delete_preserved_history": True,
                 "native_account_reopen_preserved_unreachable_history": True, "retirement_while_stop_pending": True,
                 "publication_denied_at_retirement": True, "space_delete_retired_reader": True,
                 "app_capability": "OFF", "fresh_ios_process_reopen": "NOT_RUN", "two_app_clients": "NOT_RUN",
                 "pid": 17, "account_id_sha256": "a"*64, "space_id_sha256": "b"*64, "canonical_sha256": "c"*64}
        return config, value

    @staticmethod
    def runtime():
        qualified = host.native.qualified_generation(host.ROOT)
        receipt = {"run_id": "123", "run_attempt": "1", "app_sha": "a"*40,
                   "status": "APPLE_SIMULATOR_FRAMEWORK_BUILT_NOT_EXECUTED", "candidate_sha256": host.native.CANDIDATE,
                   "expected_app_get_version": host.native.VERSION, "heart_sha": host.native.rpc.HEART,
                   "native_tests_executed_this_run": 0, "qualified_native_run": host.native.QUALIFIED_RUN,
                   "generated_sha256": qualified["generated_sha256"], "native_source_sha256": qualified["source_sha256"],
                   "module_sha256": qualified["module_sha256"]}
        run = {"status": "completed", "conclusion": "success", "id": 123, "run_attempt": 1, "head_sha": "a"*40,
               "head_branch": "codex/chatgpt-wave15-shared-20261121", "event": "workflow_dispatch",
               "display_title": "Pinkha t2-authorized-read-apple-runtime \u00b7 " + "a"*40,
               "path": ".github/workflows/torah-inspector-ipados27.yml"}
        return receipt, run, qualified

    @staticmethod
    def framework():
        binary = b"synthetic admission-control bytes, not executable native proof"
        info = {"AvailableLibraries": [{"LibraryIdentifier": "ios-arm64-simulator", "LibraryPath": "Lib.framework",
                "SupportedPlatform": "ios", "SupportedPlatformVariant": "simulator", "SupportedArchitectures": ["arm64"]}]}
        files = {"Info.plist": plistlib.dumps(info), "ios-arm64-simulator/Lib.framework/Lib": binary}
        receipt = {"framework_files_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
                   "binary_slices": [{"path": "ios-arm64-simulator/Lib.framework/Lib", "architecture": "arm64",
                       "marker": host.native.VERSION, "sha256": hashlib.sha256(binary).hexdigest()}]}
        return receipt, files

    @staticmethod
    def archive(root, files, receipt):
        path = root/"candidate.tar.gz"
        with tarfile.open(path, "w:gz") as output:
            members = {"Lib.xcframework/"+name: data for name, data in files.items()}
            members["HeartAuthorizedReadBuild.json"] = json.dumps(receipt).encode()
            for name, data in members.items():
                member = tarfile.TarInfo(name); member.size = len(data)
                output.addfile(member, io.BytesIO(data))
        return path


if __name__ == "__main__": unittest.main()
